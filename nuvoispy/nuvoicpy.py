from io import BufferedReader
import time
import getopt
import sys
from config import *

from libicp import *

def icp_read_config():
		return ConfigFlags(icp_read_flash(CFG_FLASH_ADDR, CFG_FLASH_LEN))

def init():
		return icp_init()

def deinit():
		icp_exit()

def reinit():
		deinit()
		time.sleep(0.2)
		init()

def print_usage():
		print("nuvoicp, a RPi ICP flasher for the Nuvoton N76E003")
		print("written by Steve Markgraf <steve@steve-m.de>\n")
		print("Usage:")
		print("\t[-h print this help]")
		print("\t[-c print chip configuration and exit]")
		print("\t[-r <filename> read entire flash to file]")
		print("\t[-w <filename> write file to APROM/entire flash (if LDROM is disabled)]")
		print("\t[-l <filename> write file to LDROM, enable LDROM, enable boot from LDROM]")
		print("\t[-s lock the chip after writing]")
		print("Pinout:\n")
		print("                           40-pin header J8")
		print(" connect 3.3V of MCU ->    3V3  (1) (2)  5V")
		print("                                 [...]")
		print("        connect CLK ->  GPIO26 (37) (38) GPIO20 <- connect DAT")
		print("        connect GND ->     GND (39) (40) GPIO21 <- connect RST\n")
		print("                      ________")
		print("                     |   USB  |")
		print("                     |  PORTS |")
		print("                     |________|\n")
		print("Please refer to the 'pinout' command on your RPi\n")

class DeviceInfo:
		def __init__(self, device_id = 0xFFFF, uid = 0xFFFFFF, cid = 0xFF, ucid = 0xFFFFFFFF):
			self.device_id = device_id
			self.uid = uid
			self.cid = cid
			self.ucid = ucid

		def __str__(self):
				return "Device ID: 0x%04X\nUID: 0x%08X\nCID: 0x%02X\nUCID: 0x%08X" % (self.device_id, self.uid, self.cid, self.ucid)

		def is_supported(self):
			return self.device_id == N76E003_DEVID


def get_device_info():
	devinfo = DeviceInfo()
	devinfo.device_id = icp_read_device_id()
	devinfo.uid = icp_read_uid()
	devinfo.cid = icp_read_cid()
	devinfo.ucid = icp_read_ucid()
	return devinfo

def erase_flash():
	print("Erasing flash...")
	cid = icp_read_cid()
	icp_mass_erase()
	if cid == 0xFF:
		reinit()


def read_flash(read_file):
		try:
				f = open(read_file, "wb")
		except:
				print("Could not open file for writing.")
				return False
		print("Reading flash...")
		f.write(icp_read_flash(0, FLASH_SIZE))
		f.close()
		print("Done.")
		return True
		

def write_ldrom(ldrom_data: bytes) -> ConfigFlags:
	# ldrom_data = lf.read()
	if len(ldrom_data) > LDROM_MAX_SIZE:
		print("LDROM too large.")
		return None
	if len(ldrom_data) % 1024 != 0:
		print("LDROM size must be a multiple of 1024 bytes.")
		return None
	chosen_ldrom_sz_kb = len(ldrom_data) / 1024
	erase_flash()
	print("Programming LDROM (%d KB)..." % chosen_ldrom_sz_kb)
	write_config = ConfigFlags([0x7F, 0xFF, 0xFF, 0xFF, 0xFF])
	write_config.CBS = 0
	write_config.LDS = ((7 - chosen_ldrom_sz_kb) & 0x7)
	icp_write_flash(CFG_FLASH_ADDR, write_config.to_bytes())
	icp_write_flash(FLASH_SIZE - len(ldrom_data), ldrom_data)
	print("LDROM programmed.")
	return write_config

def verify_flash(data: bytes):
		read_data = icp_read_flash(APROM_ADDR, FLASH_SIZE)
		if read_data == None:
				return False
		if len(read_data) != len(data):
				return False
		for i in range(len(data)):
				if read_data[i] != data[i]:
						return False
		return True

def write_flash(write_file, ldrom_file = "", lock_chip = False):
		lf = None
		try:
			wf = open(write_file, "rb")
			if ldrom_file != "":
				lf = open(ldrom_file, "rb")
		except:
			print("Could not open file for reading.")
			return False
		
		config = ConfigFlags()
		ldrom_data = bytes()

		if ldrom_file != "":
			ldrom_data = lf.read()
			config = write_ldrom(ldrom_data)
			if not config:
				print("Could not write LDROM.")
				return False
		else:
			erase_flash()
		
		ldrom_size = (7 - config.LDS) * 1024
		aprom_size = FLASH_SIZE - ldrom_size
		aprom_data = wf.read(aprom_size)
		print("Programming APROM (%d KB)..." % (aprom_size / 1024))
		icp_write_flash(APROM_ADDR, aprom_data)
		print("APROM programmed.")
		combined_data = aprom_data + ldrom_data
		if not verify_flash(combined_data):
			print("Verification failed.")
			return False
		print("Verification succeeded.")
		if lock_chip:
			config.LOCK = 0
			icp_write_flash(CFG_FLASH_ADDR, config.to_bytes())
			print("Locked chip.")
		
		config.print_config()
		print("Finished programming.")
		return True
		

def main():
		argv = sys.argv[1:]
		try:
				opts, _ = getopt.getopt(argv, "hcr:w:l:s")
		except getopt.GetoptError:
				print(
						"Invalid command line arguments. Please refer to the usage documentation."
				)
				print_usage()
				sys.exit(2)

		config = False
		read = False
		read_file = ""
		write = False
		write_file = ""
		ldrom_file = ""
		lock_chip = False
		for opt, arg in opts:
				if opt == "-h":
						print_usage()
						sys.exit()
				elif opt == "-c":
						config = True
				elif opt == "-r":
						read = True
						read_file = arg
				elif opt == "-w":
						write_file = arg
						write = True
				elif opt == "-l":
						ldrom_file = arg
						ldrom = True
				elif opt == "-s":
						lock_chip = True

		if (read and write):
			print("ERROR: Please specify either -r or -w, not both.\n\n")
			print_usage()
			sys.exit(2)

		if not init():
			print("ERROR: Failed to initialize ICP!\n\n")
			sys.exit(2)
		
		devinfo = get_device_info()
		# chip's locked, re-enter ICP mode to reload the flash
		# if (devinfo.cid == 0xFF):
		# 	icp_reentry()
		# 	devinfo = get_device_info()
		
		print(devinfo)
		if (devinfo.device_id != N76E003_DEVID):
			print("ERROR: Unsupported device ID: 0x%04X\n\n" % devinfo.device_id)
			deinit()
			sys.exit(2)


		Error = False
		if config:
				icp_read_config().print_config()
				sys.exit()

		if read:
				if not read_flash(read_file):
						Error = True
						print("Reading failed!!")
						

		if write:
				if not write_flash(write_file, ldrom_file, lock_chip):
					Error = True
					print("Programming failed!!")
		deinit()
		sys.exit(2 if Error else 0)



if __name__ == "__main__":
		main()
