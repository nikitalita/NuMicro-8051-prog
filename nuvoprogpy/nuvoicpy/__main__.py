import platform
if platform.system() != 'Linux':
    raise NotImplementedError("%s is not supported yet" % platform.system())

import atexit
from enum import Enum
from io import BufferedReader
import time
import getopt
import sys
import os
from ..config import *

from .nuvoicpy import NuvoICP

def print_usage():
		print("nuvoicpy, a RPi ICP flasher for the Nuvoton N76E003")
		print("written by Nikitalita\n")
		print("Usage:")
		print("\t[-h print this help]")
		print("\t[-u print chip configuration and exit]")
		print("\t[-r <filename> read entire flash to file]")
		print("\t[-w <filename> write file to APROM/entire flash (if LDROM is disabled)]")
		print("\t[-l <filename> write file to LDROM, enable LDROM, enable boot from LDROM]")
		print("\t[-b <value>    enable brownout detection (2.2v, 2.7v, 3.7v, 4.4v, or OFF to disable)]")
		print("\t[-s lock the chip after writing]")
		print("\t[-c <filename> use config file for writing (overrides -b and -s)]")
		print("Pinout:\n")
		print("                           40-pin header J8")
		print(" connect 3.3V of MCU ->    3V3  (1) (2)  5V")
		print("                                 [...]")
		print("				                        (35) (36) GPIO16 <- connect TRIGGER (optional)")
		print("        connect CLK ->  GPIO26 (37) (38) GPIO20 <- connect DAT")
		print("        connect GND ->     GND (39) (40) GPIO21 <- connect RST\n")
		print("                      ________")
		print("                     |   USB  |")
		print("                     |  PORTS |")
		print("                     |________|\n")
		print("Please refer to the 'pinout' command on your RPi\n")

def main() -> int:
		argv = sys.argv[1:]
		try:
				opts, _ = getopt.getopt(argv, "hur:w:l:sb:c:")
		except getopt.GetoptError:
				print(
						"Invalid command line arguments. Please refer to the usage documentation."
				)
				print_usage()
				return 2

		config_dump_cmd = False
		read = False
		read_file = ""
		write = False
		write_file = ""
		ldrom_file = ""
		config_file = ""
		lock_chip = False
		brown_out_voltage : float = 2.2
		if len(opts) == 0:
				print_usage()
				return 1
		for opt, arg in opts:
				if opt == "-h":
						print_usage()
						return 0
				elif opt == "-u":
						config_dump_cmd = True
				elif opt == "-r":
						read = True
						read_file = arg
				elif opt == "-w":
						write_file = arg
						write = True
				elif opt == "-l":
						ldrom_file = arg
				elif opt == "-c":
						config_file = arg
				elif opt == "-s":
						lock_chip = True
				elif opt == "-b":
						#strip off the v if it exists
						value = arg.strip("vV")
						if value.lower() == "off":
							brown_out_voltage = 0
						#check if the value is a float
						elif value.isnumeric():
							brown_out_voltage = float(value)
							if brown_out_voltage != 2.2 and brown_out_voltage != 4.4 and brown_out_voltage != 2.7 and brown_out_voltage != 3.7:
								print("ERROR: Brown out voltage must be 2.2v, 2.7v, 3.7v, 4.4v, or OFF to disable.")
								print_usage()
								return 2
		

		if (read and write):
			print("ERROR: Please specify either -r or -w, not both.\n\n")
			print_usage()
			return 2

		if not (read or write or config_dump_cmd):
			print("ERROR: Please specify either -r, -w, or -u.\n\n")
			print_usage()
			return 2


		# check to see if the files exist before we start the ICP
		for filename in [write_file, ldrom_file, config_file]:
			if ((filename and filename != "") and not os.path.isfile(filename)):
				print("ERROR: %s does not exist.\n\n" % filename)
				print_usage()
				return 2

		try:
		# check to see if the files are the correct size
			if (write and os.path.getsize(write_file) > FLASH_SIZE):
				print("ERROR: %s is too large for APROM.\n\n" % write_file)
				print_usage()
				return 2
		except:
			print("ERROR: Could not read %s.\n\n" % write_file)
			return 2
	
		# check the length of the ldrom file
		ldrom_size = 0
		if (ldrom_file != ""):
			try:
				# check the length of the ldrom file
				ldrom_size = os.path.getsize(ldrom_file)
				if not NuvoICP.check_ldrom_size(ldrom_size):
					print("Error: LDROM file invalid.")
					return 1
			except:
				print("Error: Could not read LDROM file")
				return 2

		# setup write config
		write_config = None
		if write:
			if (config_file != ""):
				write_config = ConfigFlags.from_json_file(config_file)
				if (write_config == None):
					print("Error: Could not read config file")
					return 1
			else: #default config
				write_config = ConfigFlags()
				if brown_out_voltage == 0:
					write_config.set_brownout_detect = False
					write_config.set_brownout_inhibits_IAP = False
					write_config.set_brownout_reset = False
				else:
					write_config.set_brownout_voltage(brown_out_voltage)
				write_config.set_lock(lock_chip)
				write_config.set_ldrom_boot(ldrom_file != "")
				if (ldrom_file != ""):
					write_config.set_ldrom_size(ldrom_size)
			
		with NuvoICP() as nuvo:
			devinfo = nuvo.get_device_info()
			if (devinfo.device_id != N76E003_DEVID):
				if (write and devinfo.cid == 0xFF):
					print("Device not found, chip may be locked, Do you want to attempt a mass erase? (y/N)")
					if (input() == "y" or input() == "Y"):
						if not nuvo.mass_erase():
							print("Mass erase failed, exiting...")
							return 2
						devinfo = nuvo.get_device_info()
						print(devinfo)
					else:
						print("Exiting...")
						return 2
					if (devinfo.device_id != N76E003_DEVID):
						print("ERROR: Unsupported device ID: 0x%04X (mass erase failed!)\n\n" % devinfo.device_id)
						return 2
				else:
					if devinfo.device_id == 0:
						print("ERROR: Device not found, please check your connections.\n\n")
						return 2				
					print("ERROR: Unsupported device ID: 0x%04X (chip may be locked)\n\n" % devinfo.device_id)
					return 2

			# process commands
			if config_dump_cmd:
				print(devinfo)
				cfg = nuvo.read_config()
				if not cfg:
					print("Config read failed!!")
					return 1
				cfg.print_config()
				return 0
			elif read:
				print(devinfo)
				cfg = nuvo.read_config()
				cfg.print_config()
				print()
				if (devinfo.cid == 0xFF or cfg.is_locked()):
					print("Error: Chip is locked, cannot read flash")
					return 1
				if not nuvo.dump_flash_to_file(read_file):
						print("Reading failed!!")
						return 1
				#remove extension from read_file
				config_file = read_file.rsplit('.', 1)[0] + "-config.json"
				cfg.to_json_file(config_file)
			elif write:
					if not nuvo.program(write_file, ldrom_file, write_config):
						print("Programming failed!!")
						return 1
			return 0



if __name__ == "__main__":
	sys.exit(main())
