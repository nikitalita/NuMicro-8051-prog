import platform

if platform.system() != 'Linux':
    raise NotImplementedError("%s is not supported yet" % platform.system())

import atexit
from enum import Enum
from io import BufferedReader
import time
import getopt
import sys
from ..config import *
from .lib.libnuvoicp import *


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


class PGMInitException(Exception):
	pass
class NoDeviceException(Exception):
	pass
class UnsupportedDeviceException(Exception):
	pass

# class HostPGM:
#   def __init__(self, host_type: str = "Raspberry Pi"):
#     self.host_type = ICPHostType.from_str(host_type)
# 		self.initialized = False

"""_summary_
NuvoICP class
Raises:
		PGMInitException: _description_
		NoDeviceException: _description_
		UnsupportedDeviceException: _description_
		Exception: _description_

Returns:
		_type_: _description_
"""

class NuvoICP:
	def __init__(self, library: str = "pigpio", enter_no_init = False, enter_init_send_reset_sequence = None):
		self.library = library
		self.icp = LibICP(library)
		self.pgm = LibPGM(library)
		self.enter_no_init = enter_no_init
		self.enter_init_send_reset_sequence = enter_init_send_reset_sequence
		self.initialized = False
		
	def __enter__(self):
		if self.enter_no_init:
			return self
		send_res = True
		if self.enter_init_send_reset_sequence is not None:
			send_res = self.enter_init_send_reset_sequence
		if not self.init(send_res, True, True):
			return None
		return self

	def __exit__(self, exc_type, exc_value, traceback):
		self.deinit()

	def init_pgm(self):
		if not self.pgm.init():
			raise PGMInitException("Unable to initialize PGM module")


	# CMD_BIT_DELAY property
	# The delay between each bit sent to the device during `icp_write_byte()` in microseconds
	# @return: The current CMD_BIT_DELAY value
	@property
	def CMD_BIT_DELAY(self):
		return self.pgm.get_cmd_bit_delay()

	@CMD_BIT_DELAY.setter
	def CMD_BIT_DELAY(self, delay_us):
		self.pgm.set_cmd_bit_delay(delay_us)
	
	# READ_BIT_DELAY property
	# The delay between each bit read from the device during `icp_read_byte()` in microseconds
	# @return: The current READ_BIT_DELAY value
	@property
	def READ_BIT_DELAY(self):
		return self.pgm.get_read_bit_delay()

	@READ_BIT_DELAY.setter
	def READ_BIT_DELAY(self, delay_us):
		self.pgm.set_read_bit_delay(delay_us)
	
	# WRITE_BIT_DELAY property
	# The delay between each bit written to the device during `icp_write_byte()` in microseconds
	# @return: The current WRITE_BIT_DELAY value
	@property
	def WRITE_BIT_DELAY(self):
		return self.pgm.get_write_bit_delay()								

	@WRITE_BIT_DELAY.setter
	def WRITE_BIT_DELAY(self, delay_us):
		self.pgm.set_write_bit_delay(delay_us)


	# This is mostly needed when the chip is configured to not have P2.0 as the reset pin
	# It is often a crapshoot to get it into ICP Programming mode as it will not stay in a reset state when nRST is low and will reboot itself
	# So, we have to keep trying at random intervals to try and catch it in a reset state
	def retry(self):
		max_reentry = 5
		max_reinit = 2
		max_fullexit = 3
		reentry_tries = 0
		fullexit_tries = 0
		reinit_tries = 0
		print("No device found, attempting reentry...")
		try:
			while reinit_tries < max_reinit:
				while fullexit_tries < max_fullexit:
					while reentry_tries < max_reentry:
						print("Reentry attempt " + str(reentry_tries * (fullexit_tries + 1) * (reinit_tries+1)) + " of "+ str(max_reentry * max_reinit * max_fullexit) +"...")
						self.icp.reentry(8000 + (reentry_tries * 1000), 1000, 100 + (reentry_tries * 100))
						reentry_tries+=1
						if self.icp.read_device_id() != 0:
							print("Connected!")
							return True
					print("Attempting full exit and entry...")
					self.icp.exit()
					time.sleep(0.5)
					self.icp.entry()
					if self.icp.read_device_id() != 0:
						print("Connected!")
						return True
					fullexit_tries+=1
				print("Attempting reinitialization...")
				self.icp.deinit()
				time.sleep(0.5)
				self.icp.init()
				if self.icp.read_device_id() != 0:
					print("Connected!")
					return True
				reinit_tries+=1
		except KeyboardInterrupt:
			print("Retry aborted!")
		except Exception:
			pass
		print("Retry failed!")
		return False
		
		

	# Initialize ICP
	# Returns True if successful, False otherwise
	# @param do_reset_seq: Whether to perform the reset sequence
	def init(self, do_reset_seq = True, check_device = True, retry = True):
		if not self.icp.init(do_reset_seq):
			raise PGMInitException("ERROR: Could not initialize ICP.")
		if check_device:
			devid = self.icp.read_device_id()
			cid = self.icp.read_cid()
			if devid == 0:
				if (not retry or not self.retry()):
					self.pgm.deinit()
					raise NoDeviceException("ERROR: No device detected, please check your connections!")
				devid = self.icp.read_device_id()
				cid = self.icp.read_cid()
			if devid == 0xFFFF and cid == 0xFF:
				print("WARNING: Read Device ID of 0xFFFF and cid of 0xFF, device may be locked!")
				print("Proceeding anyway...")
			elif devid != N76E003_DEVID:
				self.pgm.deinit()
				raise UnsupportedDeviceException("ERROR: Non-N76E003 device detected (devid: %d)\nThis programmer only supports N76E003 (devid: %d)!" % (devid, N76E003_DEVID))
		self.initialized = True
		return True

	def deinit(self):
		self.initialized = False
		self.icp.deinit()

	def reinit(self, do_reset_seq = True, check_device = True):
		self.deinit()
		time.sleep(0.2)
		return self.init(do_reset_seq, check_device)

	def reentry(self, delay1 = 5000, delay2 = 1000, delay3 = 10):
		if not self.initialized:
			print("ICP not initialized.")
			return None
		self.icp.reentry(delay1, delay2, delay3)

	def get_device_id(self):
		if not self.initialized:
			print("ICP not initialized.")
			return None
		return self.icp.read_device_id()

	def get_cid(self):
		if not self.initialized:
			print("ICP not initialized.")
			return None
		return self.icp.read_cid()

	def read_config(self):
		if not self.initialized:
			print("ICP not initialized.")
			return None
		return ConfigFlags(self.icp.read_flash(CFG_FLASH_ADDR, CFG_FLASH_LEN))

	def mass_erase(self):
		if not self.initialized:
			print("ICP not initialized.")
			return False
		print("Erasing flash...")
		cid = self.icp.read_cid()
		self.icp.mass_erase()
		if cid == 0xFF or cid == 0x00:
			self.reentry()
		return True

	def get_device_info(self):
		if not self.initialized:
			print("ICP not initialized.")
			return None
		devinfo = DeviceInfo()
		devinfo.device_id = self.icp.read_device_id()
		devinfo.uid = self.icp.read_uid()
		devinfo.cid = self.icp.read_cid()
		devinfo.ucid = self.icp.read_ucid()
		return devinfo

	def page_erase(self, addr):
		if not self.initialized:
			print("ICP not initialized.")
			return False
		self.icp.page_erase(addr)
		return True

	def read_flash(self, addr, len) -> bytes:
		if not self.initialized:
			print("ICP not initialized.")
			return None
		return self.icp.read_flash(addr, len)

	def write_flash(self, addr, data) -> bool:
		if not self.initialized:
			print("ICP not initialized.")
			return False
		self.icp.write_flash(addr, data)
		return True

	def dump_flash(self) -> bytes:
		if not self.initialized:
			print("ICP not initialized.")
			return None
		return self.icp.read_flash(APROM_ADDR, FLASH_SIZE)

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
			f.write(self.icp.read_flash(APROM_ADDR, FLASH_SIZE))
			f.close()
			print("Done.")
			return True
	
	def write_config(self, config: ConfigFlags) -> bool:
		if not self.initialized:
			print("ICP not initialized.")
			return False
		self.icp.page_erase(CFG_FLASH_ADDR)
		self.icp.write_flash(CFG_FLASH_ADDR, config.to_bytes())
		return True

	"""
	Programs the LDROM with the given data, and programs the config block with the given configuration flags.

	@param ldrom_data: The data to program into the LDROM
	@param write_config: The configuration flags to write to the config block. If None, the default config for the ldrom size will be written.
	@return: The configuration flags that were written to the config block, or None if an error occurred.
	"""	
	def program_ldrom(self, ldrom_data: bytes, write_config: ConfigFlags = None) -> ConfigFlags or None:
		if not self.initialized:
			print("ICP not initialized.")
			return None
		print("Programming LDROM (%d KB)..." % int(len(ldrom_data) / 1024))
		if (not write_config):
			write_config = ConfigFlags()
			write_config.set_ldrom_boot(True)
			write_config.set_ldrom_size(len(ldrom_data))
		self.write_config(write_config)
		self.icp.write_flash(FLASH_SIZE - len(ldrom_data), ldrom_data)
		print("LDROM programmed.")
		return write_config

	def verify_flash(self, data: bytes, report_errors = True) -> bool:
			if not self.initialized:
				print("ICP not initialized.")
				return False
			read_data = self.icp.read_flash(APROM_ADDR, FLASH_SIZE)
			if read_data == None:
					return False
			if len(read_data) != len(data):
					return False
			result = True
			byte_errors = 0
			for i in range(len(data)):
					if read_data[i] != data[i]:
							if not report_errors:
									return False
							result = False
							byte_errors += 1
			if not result:
				print("Verification failed. %d byte errors." % byte_errors)
			return result

	def program_aprom(self, data: bytes) -> bool:
			if not self.initialized:
				print("ICP not initialized.")
				return False
			print("Programming APROM...")
			self.icp.write_flash(APROM_ADDR, data)
			print("APROM programmed.")
			return True

	# static method
	@staticmethod
	def check_ldrom_size(size) -> bool:
			if size > LDROM_MAX_SIZE:
				print("LDROM too large.")
				return False
			if size % 1024 != 0:
				print("LDROM size must be a multiple of 1024 bytes.")
				return False
			return True
 
	def program_data(self, aprom_data, ldrom_data = bytes(), config: ConfigFlags = None, ldrom_config_override = True) -> bool:
			if not self.initialized:
				print("ICP not initialized.")
				return False
			if len(ldrom_data) > 0:
				ldrom_size = len(ldrom_data)
				if not self.check_ldrom_size(ldrom_size):
					print("ERROR: Invalid LDROM. Not programming...")
					return False
				else:
					if config:
						if config.get_ldrom_size() != ldrom_size:
							print("WARNING: LDROM size does not match config: %d KB vs %d KB" % (ldrom_size / 1024, config.get_ldrom_size_kb()))
							if ldrom_config_override:
								print("Overriding LDROM size in config.")
								config.set_ldrom_size(ldrom_size)
							else:
								if len(ldrom_data) < config.get_ldrom_size():
									print("LDROM will be padded with 0xFF.")
									ldrom_data = ldrom_data + bytes([0xFF] * (config.get_ldrom_size() - len(ldrom_data)))
								else:
									print("LDROM will be truncated.")
									ldrom_data = ldrom_data[:config.get_ldrom_size()]
						if config.is_ldrom_boot() != True:
							print("WARNING: LDROM boot flag not set in config")
							if ldrom_config_override:
								print("Overriding LDROM boot in config.")
								config.set_ldrom_boot(True)
							else:
								print("LDROM will not be bootable.")
					else: # No config, set defaults
						config = ConfigFlags()
						config.set_ldrom_size(ldrom_size)
						config.set_ldrom_boot(True)
			elif config == None:
				config = ConfigFlags()

			aprom_size = config.get_aprom_size()
			if aprom_size != len(aprom_data):
				print("WARNING: APROM file size does not match config: %d KB vs %d KB" % (len(aprom_data) / 1024, aprom_size / 1024))
				if aprom_size < len(aprom_data):
					print("APROM will be truncated.")
					aprom_data = aprom_data[:aprom_size]
				else:
					print("APROM will be padded with 0xFF.")
					# Pad with 0xFF
					aprom_data += bytes([0xFF] * (aprom_size - len(aprom_data)))

			self.mass_erase()
			if len(ldrom_data) > 0:
				config = self.program_ldrom(ldrom_data, config)
				if not config:
					print("Could not write LDROM.")
					return False
			
			print("Programming APROM (%d KB)..." % (aprom_size / 1024))
			self.write_config(config)
			self.icp.write_flash(APROM_ADDR, aprom_data)
			print("APROM programmed.")
			combined_data = aprom_data + ldrom_data
			if not self.verify_flash(combined_data):
				print("Verification failed.")
				return False
			print("Verification succeeded.")
			
			print("\nResulting Device info:")
			devinfo = self.get_device_info()
			print(devinfo)
			print()
			config.print_config()
			print("Finished programming!\n")
			return True

	def program(self, write_file, ldrom_file = "", config: ConfigFlags = None, ldrom_override = True) ->bool:
			if not self.initialized:
				print("ICP not initialized.")
				return False
			lf = None
			try:
				wf = open(write_file, "rb")
			except:
				print("Could not open %s for reading." % write_file)
				return False
			if ldrom_file != "":
				try:
					lf = open(ldrom_file, "rb")
				except:
					print("Could not open %s for reading." % ldrom_file)
					return False
			aprom_data = wf.read()

			ldrom_data = bytes()
			if lf:
				ldrom_data = lf.read()
			return self.program_data(aprom_data, ldrom_data, config, ldrom_override)

