import atexit
from io import BufferedReader
import time
import getopt
import sys
try:
	from nuvoispy.config import *
	from nuvoispy.libicp import *
except:
	from config import *
	from config import ConfigFlags
	from libicp import *

class DeviceInfo:
		def __init__(self, device_id = 0xFFFF, uid = 0xFFFFFF, cid = 0xFF, ucid = 0xFFFFFFFF):
			self.device_id = device_id
			self.uid = uid
			self.cid = cid
			self.ucid = ucid

		def __str__(self):
				return "Device ID: 0x%04X\nCID: 0x%02X\nUID: 0x%08X\nUCID: 0x%08X" % (self.device_id, self.cid, self.uid, self.ucid)

		def is_supported(self):
			return self.device_id == N76E003_DEVID

class NuvoICP:
	def __init__(self):
		self.initialized = False
		
	def __enter__(self):
		if not self.init():
			return None
		return self

	def __exit__(self, exc_type, exc_value, traceback):
		self.deinit()

	# Initialize ICP
	# Returns True if successful, False otherwise
	# @param do_reset_seq: Whether to perform the reset sequence
	def init(self, do_reset_seq = True):
		if not icp_init(do_reset_seq):
			raise Exception("ERROR: Could not initialize ICP.")
		self.initialized = True
		return True

	def deinit(self):
		self.initialized = False
		icp_exit()

	def reinit(self, do_reset_seq = True):
		self.deinit()
		time.sleep(0.2)
		if not icp_init(do_reset_seq):
			raise Exception("ERROR: Could not initialize ICP.")
		return True

	def reentry(self, delay1 = 5000, delay2 = 1000, delay3 = 10):
		if not self.initialized:
			print("ICP not initialized.")
			return None
		icp_reentry(delay1, delay2, delay3)

	def get_device_id(self):
		if not self.initialized:
			print("ICP not initialized.")
			return None
		return icp_read_device_id()

	def get_cid(self):
		if not self.initialized:
			print("ICP not initialized.")
			return None
		return icp_read_cid()

	def read_config(self):
		if not self.initialized:
			print("ICP not initialized.")
			return False
		return ConfigFlags(icp_read_flash(CFG_FLASH_ADDR, CFG_FLASH_LEN))

	def mass_erase(self):
		if not self.initialized:
			print("ICP not initialized.")
			return False
		print("Erasing flash...")
		cid = icp_read_cid()
		icp_mass_erase()
		if cid == 0xFF or cid == 0x00:
			self.reentry()
		return True

	def get_device_info(self):
		if not self.initialized:
			print("ICP not initialized.")
			return None
		devinfo = DeviceInfo()
		devinfo.device_id = icp_read_device_id()
		devinfo.uid = icp_read_uid()
		devinfo.cid = icp_read_cid()
		devinfo.ucid = icp_read_ucid()
		return devinfo

	def page_erase(self, addr):
		if not self.initialized:
			print("ICP not initialized.")
			return False
		icp_page_erase(addr)
		return True

	def read_flash(self, addr, len) -> bytes:
		if not self.initialized:
			print("ICP not initialized.")
			return None
		return icp_read_flash(addr, len)

	def write_flash(self, addr, data) -> bool:
		if not self.initialized:
			print("ICP not initialized.")
			return False
		icp_write_flash(addr, data)
		return True

	def dump_flash(self) -> bytes:
		if not self.initialized:
			print("ICP not initialized.")
			return None
		return icp_read_flash(APROM_ADDR, FLASH_SIZE)

	def dump_flash_to_file(self, read_file) -> bool:
			if not self.initialized:
				print("ICP not initialized.")
				return False
			try:
					f = open(read_file, "wb")
			except:
					print("Could not open file for writing.")
					return False
			print("Reading flash...")
			f.write(icp_read_flash(APROM_ADDR, FLASH_SIZE))
			f.close()
			print("Done.")
			return True
 
	def write_config(self, config: ConfigFlags) -> bool:
		if not self.initialized:
			print("ICP not initialized.")
			return False
		icp_write_flash(CFG_FLASH_ADDR, config.to_bytes())
		return True

	def program_ldrom(self, ldrom_data: bytes, write_config: ConfigFlags = None) -> ConfigFlags:
		if not self.initialized:
			print("ICP not initialized.")
			return None
		chosen_ldrom_sz_kb = len(ldrom_data) / 1024
		print("Programming LDROM (%d KB)..." % chosen_ldrom_sz_kb)
		if (not write_config):
			write_config = ConfigFlags()
			write_config.set_ldrom_boot(True)
			write_config.set_ldrom_size(chosen_ldrom_sz_kb)
		self.write_config(write_config)
		icp_write_flash(FLASH_SIZE - len(ldrom_data), ldrom_data)
		print("LDROM programmed.")
		return write_config

	def verify_flash(self, data: bytes):
			if not self.initialized:
				print("ICP not initialized.")
				return False
			read_data = icp_read_flash(APROM_ADDR, FLASH_SIZE)
			if read_data == None:
					return False
			if len(read_data) != len(data):
					return False
			for i in range(len(data)):
					if read_data[i] != data[i]:
							return False
			return True

	def program_aprom(self, data: bytes) -> bool:
			if not self.initialized:
				print("ICP not initialized.")
				return False
			print("Programming APROM...")
			icp_write_flash(APROM_ADDR, data)
			print("APROM programmed.")
			return True

	def check_ldrom_size(self, size) -> bool:
			if size > LDROM_MAX_SIZE:
				print("LDROM too large.")
				return False
			if size % 1024 != 0:
				print("LDROM size must be a multiple of 1024 bytes.")
				return False
			return True

	def program(self, write_file, ldrom_file = "", config: ConfigFlags = None, ldrom_override = True) ->bool:
			if not self.initialized:
				print("ICP not initialized.")
				return False
			lf = None
			try:
				wf = open(write_file, "rb")
				if ldrom_file != "":
					lf = open(ldrom_file, "rb")
			except:
				print("Could not open %s for reading." % write_file)
				return False

			ldrom_data = bytes()
			if ldrom_file != "":
				ldrom_data = lf.read()
				ldrom_size = len(ldrom_data)
				if not self.check_ldrom_size(ldrom_size):
					print("ERROR: Invalid LDROM. Exiting...")
					return False
				else:
					if config:
						if config.get_ldrom_size() != ldrom_size:
							print("WARNING: LDROM size does not match config: %d KB vs %d KB" % (ldrom_size / 1024, config.get_ldrom_size_kb()))
							if ldrom_override:
								print("Overriding LDROM size in config.")
								config.set_ldrom_size(int(ldrom_size / 1024))
							else:
								print("Programming failed")
								return False
						if config.is_ldrom_boot() != True:
							print("WARNING: LDROM boot flag not set in config")
							if ldrom_override:
								print("Overriding LDROM boot in config.")
								config.set_ldrom_boot(True)
							else:
								print("LDROM will not be bootable.")
					else:
						config = ConfigFlags()
						config.set_ldrom_size(int(ldrom_size / 1024))
						config.set_ldrom_boot(True)
			elif config == None:
				config = ConfigFlags()
			
			self.mass_erase()
			if ldrom_file != "":
				config = self.program_ldrom(ldrom_data, config)
				if not config:
					print("Could not write LDROM.")
					return False
			
			aprom_size = config.get_aprom_size()
			aprom_data = wf.read(aprom_size)
			print("Programming APROM (%d KB)..." % (aprom_size / 1024))
			icp_write_flash(CFG_FLASH_ADDR, config.to_bytes())
			icp_write_flash(APROM_ADDR, aprom_data)
			print("APROM programmed.")
			combined_data = aprom_data + ldrom_data
			if not self.verify_flash(combined_data):
				print("Verification failed.")
				return False
			print("Verification succeeded.")
			
			devinfo = self.get_device_info()
			print(devinfo)
			print()
			config.print_config()
			print("Finished programming.")
			return True



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

		with NuvoICP() as icp:
		
			devinfo = icp.get_device_info()
			
			if (devinfo.device_id != N76E003_DEVID):
				if (write and devinfo.cid == 0xFF):
					print("Device not found, chip may be locked, Do you want to attempt a mass erase? (y/N)")
					if (input() == "y" or input() == "Y"):
						if not icp.mass_erase():
							print("Mass erase failed, exiting...")
							return 2
						devinfo = icp.get_device_info()
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

			if config_dump_cmd:
				print(devinfo)
				cfg = icp.read_config()
				if not cfg:
					print("Config read failed!!")
					return 1
				cfg.print_config()
				return 0
			elif read:
				print(devinfo)
				cfg = icp.read_config()
				cfg.print_config()
				print()
				if (devinfo.cid == 0xFF or cfg.is_locked()):
					print("Error: Chip is locked, cannot read flash")
					return 1
				if not icp.dump_flash_to_file(read_file):
						print("Reading failed!!")
						return 1
			elif write:
					write_config = None
					if (config_file != ""):
						write_config = ConfigFlags.from_json_file(config_file)
						if (write_config == None):
							print("Error: Could not read config file")
							return 1
					else:
						write_config = ConfigFlags()
						if brown_out_voltage == 0:
							write_config.set_brownout_detect = False
							write_config.set_brownout_inhibits_IAP = False
							write_config.set_brownout_reset = False
						else:
							write_config.set_brownout_voltage(brown_out_voltage)
						write_config.set_lock(lock_chip)
						write_config.set_ldrom_boot(ldrom_file != "")
						# check the length of the ldrom file
						if (ldrom_file != ""):
							try:
								# check the length of the ldrom file
								ldrom_size = os.path.getsize(ldrom_file)
								if not icp.check_ldrom_size(ldrom_size):
									print("Error: LDROM file invalid.")
									return 1
								write_config.set_ldrom_size(ldrom_size/1024)
							except:
								print("Error: Could not read LDROM file")
								return 1
					
					if not icp.program(write_file, ldrom_file, write_config):
						print("Programming failed!!")
						return 1
			return 0



if __name__ == "__main__":
	sys.exit(main())
