from io import BufferedReader
import time
import RPi.GPIO as GPIO
import getopt
import sys
from config import *

# GPIO line numbers for RPi, must be changed for other SBCs
GPIO_DAT = 20
GPIO_RST = 21
GPIO_CLK = 26


CMD_READ_UID = 0x04
CMD_READ_CID = 0x0B
CMD_READ_DEVICE_ID = 0x0C
CMD_READ_FLASH = 0x00
CMD_WRITE_FLASH = 0x21
CMD_MASS_ERASE = 0x26
CMD_PAGE_ERASE = 0x22

ENTRY_BITS = 0x5AA503
ICP_SEQ = 0x9E1CB6
ICP_BITSEND = 0xF78F0
MASS_ERASE_ADDR = 0x3A5A5

CONSUMER = "nuvoicp"

def pgm_init():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(GPIO_DAT, GPIO.IN)
    GPIO.setup(GPIO_RST, GPIO.OUT)
    GPIO.setup(GPIO_CLK, GPIO.OUT)

def pgm_set_dat(val):
    GPIO.output(GPIO_DAT, val)

def pgm_get_dat():
    return GPIO.input(GPIO_DAT)

def pgm_set_rst(val):
    GPIO.output(GPIO_RST, val)

def pgm_set_clk(val):
    GPIO.output(GPIO_CLK, val)


def pgm_dat_dir(state):
		dat_line.release()
		if state:
				dat_line.request(consumer=CONSUMER, type=gpiod.LINE_REQ_DIR_OUT, default_val=0)
		else:
				dat_line.request(consumer=CONSUMER, type=gpiod.LINE_REQ_DIR_IN)


def pgm_deinit():
		pgm_set_rst(1)
		chip.close()


def usleep(usecs):
		time.sleep(usecs / 1000000)


def icp_bitsend(data, length, udelay):
		pgm_dat_dir(True)
		for i in range(length):
				pgm_set_dat((data >> i) & 1)
				usleep(udelay)
				pgm_set_clk(1)
				usleep(udelay)
				pgm_set_clk(0)


def icp_write_byte(data: int, end: int, delay1: int, delay2: int, bitdelay: int):
		icp_bitsend(data, 8, bitdelay)
		pgm_set_dat(end)
		usleep(delay1)
		pgm_set_clk(1)
		usleep(delay2)
		pgm_set_dat(0)
		pgm_set_clk(0)


def icp_send_command(cmd, dat):
		icp_bitsend((dat << 6) | cmd, 24, 1)


def icp_read_byte(end: int):
		pgm_dat_dir(0)

		data = 0
		i = 8

		while i > 0:
				i -= 1
				state = pgm_get_dat()
				pgm_set_clk(1)
				pgm_set_clk(0)
				data |= state << i

		pgm_dat_dir(1)
		pgm_set_dat(end)
		pgm_set_clk(1)
		pgm_set_clk(0)
		pgm_set_dat(0)
		return data


def icp_init():
		for i in range(24):
				pgm_set_rst((ICP_SEQ >> i) & 1)
				usleep(10000)

		usleep(100)
		icp_bitsend(ENTRY_BITS, 24, 60)


def icp_reentry():
		usleep(10)
		pgm_set_rst(1)
		usleep(5000)
		pgm_set_rst(0)
		usleep(1000)
		icp_bitsend(ENTRY_BITS, 24, 60)
		usleep(10)


def icp_exit():
		pgm_set_rst(1)
		usleep(5000)
		pgm_set_rst(0)
		usleep(10000)
		icp_bitsend(ICP_BITSEND, 24, 60)
		usleep(500)
		pgm_set_rst(1)


def icp_read_device_id():
		icp_send_command(CMD_READ_DEVICE_ID, 0)
		devid = [0xFF, 0xFF]
		devid[0] = icp_read_byte(0)
		devid[1] = icp_read_byte(1)
		return (devid[1] << 8) | devid[0]


def icp_read_uid():
		uid = [0xFF, 0xFF, 0xFF, 0xFF]
		for i in range(4):
				icp_send_command(CMD_READ_UID, i)
				uid[i] = icp_read_byte(1)
		return (uid[3] << 24) | (uid[2] << 16) | (uid[1] << 8) | uid[0]


def icp_read_cid():
		icp_send_command(CMD_READ_CID, 0)
		return icp_read_byte(1)


def icp_read_ucid():
		ucid = [0xFF, 0xFF, 0xFF, 0xFF]
		for i in range(4):
				icp_send_command(CMD_READ_UID, i + 0x20)
				ucid[i] = icp_read_byte(1)
		return (ucid[3] << 24) | (ucid[2] << 16) | (ucid[1] << 8) | ucid[0]


def icp_read_flash(address, length) -> bytes:
		icp_send_command(CMD_READ_FLASH, address)
		# create a list of length `length`
		data = []
		for i in range(length):
				data.append(icp_read_byte(i == (length - 1)))
		return bytes(data)


def icp_write_flash(address: int, data: bytes):
		icp_send_command(CMD_WRITE_FLASH, address)
		for i in range(len(data)):
				icp_write_byte(data[i], i == (len(data) - 1), 200, 50, 1)
				if i % 256 == 0 and len(data) > 256:
						print(".", end="", flush=True)
		print("\n")
		return address + len(data)


def icp_mass_erase():
		icp_send_command(CMD_MASS_ERASE, MASS_ERASE_ADDR)
		icp_write_byte(0xFF, 1, 100000, 10000, 0)


def icp_page_erase(address):
		icp_send_command(CMD_PAGE_ERASE, address)
		icp_write_byte(0xFF, 1, 10000, 1000, 0)


def icp_read_config():
		return ConfigFlags(icp_read_flash(CFG_FLASH_ADDR, CFG_FLASH_LEN))


def init():
		if not pgm_init():
				return False
		icp_init()
		return True


def deinit():
		icp_exit()
		pgm_deinit()


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

def erase_flash():
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
	write_config = ConfigFlags([0x7F, 0xFF, 0xFF, 0xFF, 0xFF])
	write_config.CBS = 0
	write_config.LDS = ((7 - chosen_ldrom_sz_kb) & 0x7)
	icp_write_flash(CFG_FLASH_ADDR, write_config.to_bytes())
	icp_write_flash(FLASH_SIZE - len(ldrom_data), ldrom_data)
	print("Programmed LDROM (%d KB)" % chosen_ldrom_sz_kb)
	return write_config

def verify_flash(data: bytes):
		read_data = icp_read_flash(APROM_ADDR, FLASH_SIZE, read_data)
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
		ldrom_data = []

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
		icp_write_flash(APROM_ADDR, aprom_data)
		print("Programmed APROM (%d KB)" % (aprom_size / 1024))
		combined_data = aprom_data + ldrom_data
		if not verify_flash(combined_data):
			print("Verification failed.")
			return False
		print("Verification succeeded.")
		if lock_chip:
			config.LOCK = 0
			icp_write_flash(CFG_FLASH_ADDR, config.to_bytes())
			print("Locked chip.")
		
		print(config)
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

		if (init() != 0):
			print("ERROR: Failed to initialize ICP!\n\n")
			sys.exit(2)
		
		devinfo = get_device_info()
		# chip's locked, re-enter ICP mode to reload the flash
		if (devinfo.cid == 0xFF):
			icp_reentry()
			devinfo = get_device_info()
		
		print(devinfo)
		if (devinfo.devid != N76E003_DEVID):
			print("ERROR: Unsupported device ID: 0x%04X\n\n" % devinfo.devid)
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
