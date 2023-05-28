import ctypes

# get dir of this file
import os
import platform
dir_path = os.path.dirname(os.path.realpath(__file__))

if platform.system() != 'Linux':
    raise NotImplementedError("%s is not supported yet" % platform.system())

class LibICP:
    def __init__(self, libname = "pigpio"):
        # Load the shared library
        if libname.lower() == "pigpio":
            self.lib = ctypes.CDLL(dir_path + "/libnuvoicp-pigpio.so")
        elif libname.lower() == "gpiod":
            self.lib = ctypes.CDLL(dir_path + "/libnuvoicp-gpiod.so")
        else:
            raise ValueError("Unknown lib: %s\nMust be either 'pigpio' or 'gpiod'" % libname)

        # Function prototypes
        self.lib.icp_send_entry_bits.argtypes = []
        self.lib.icp_send_entry_bits.restype = None

        self.lib.icp_send_exit_bits.argtypes = []
        self.lib.icp_send_exit_bits.restype = None

        self.lib.icp_init.argtypes = [ctypes.c_uint8]
        self.lib.icp_init.restype = ctypes.c_int

        self.lib.icp_entry.argtypes = [ctypes.c_uint8]
        self.lib.icp_entry.restype = None

        self.lib.icp_reentry.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32]
        self.lib.icp_reentry.restype = None

        self.lib.icp_reentry_glitch.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32]
        self.lib.icp_reentry_glitch.restype = None

        self.lib.icp_reentry_glitch_read.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint8, ctypes.POINTER(ctypes.c_uint8)]
        self.lib.icp_reentry_glitch_read.restype = None

        self.lib.icp_deinit.argtypes = []
        self.lib.icp_deinit.restype = None

        self.lib.icp_exit.argtypes = []
        self.lib.icp_exit.restype = None

        self.lib.icp_read_device_id.argtypes = []
        self.lib.icp_read_device_id.restype = ctypes.c_uint32

        self.lib.icp_read_pid.argtypes = []
        self.lib.icp_read_pid.restype = ctypes.c_uint32

        self.lib.icp_read_cid.argtypes = []
        self.lib.icp_read_cid.restype = ctypes.c_uint8

        self.lib.icp_read_uid.argtypes = []
        self.lib.icp_read_uid.restype = ctypes.c_uint32

        self.lib.icp_read_ucid.argtypes = []
        self.lib.icp_read_ucid.restype = ctypes.c_uint32

        self.lib.icp_read_flash.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint8)]
        self.lib.icp_read_flash.restype = ctypes.c_uint32

        self.lib.icp_write_flash.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint8)]
        self.lib.icp_write_flash.restype = ctypes.c_uint32

        self.lib.icp_mass_erase.argtypes = []
        self.lib.icp_mass_erase.restype = None

        self.lib.icp_page_erase.argtypes = [ctypes.c_uint32]
        self.lib.icp_page_erase.restype = None

        # Wrapper functions

    def send_entry_bits(self) -> None:
        self.lib.icp_send_entry_bits()

    def send_exit_bits(self) -> None:
        self.lib.icp_send_exit_bits()

    def init(self,do_reset = True) -> bool:
        ret = self.lib.icp_init(ctypes.c_uint8(do_reset)) 
        return True if ret == 0 else False

    def entry(self,do_reset = True) -> None:
        self.lib.icp_entry(ctypes.c_uint8(do_reset))

    def reentry(self,delay1 = 5000, delay2 = 1000, delay3 = 10):
        self.lib.icp_reentry(ctypes.c_uint32(delay1), ctypes.c_uint32(delay2), ctypes.c_uint32(delay3))

    def reentry_glitch(self,delay1 = 5000, delay2 = 1000, delay3 = 10) -> None:
        self.lib.icp_reentry_glitch(ctypes.c_uint32(delay1), ctypes.c_uint32(delay2), ctypes.c_uint32(delay3))

    def reentry_glitch_read(self,delay1 = 5000, delay2 = 1000, delay3 = 10) -> bytes:
        data_type = ctypes.c_uint8 * 5
        data = data_type()
        self.lib.icp_reentry_glitch_read(ctypes.c_uint32(delay1), ctypes.c_uint32(delay2),ctypes.c_uint32(delay3), data)
        return bytes(data)

    def deinit(self):
        self.lib.icp_deinit()

    def exit(self):
        self.lib.icp_exit()

    def read_device_id(self):
        return self.lib.icp_read_device_id()

    def read_pid(self):
        return self.lib.icp_read_pid()

    def read_cid(self):
        return self.lib.icp_read_cid()

    def read_uid(self):
        return self.lib.icp_read_uid()

    def read_ucid(self):
        return self.lib.icp_read_ucid()

    def read_flash(self,addr, length):
        data_type = ctypes.c_uint8 * length
        data = data_type()
        self.lib.icp_read_flash(ctypes.c_uint32(addr), ctypes.c_uint32(length), data)
        return bytes(data)

    def write_flash(self,addr, data) -> int:
        length = len(data)
        data_type = ctypes.c_uint8 * length
        data_buffer = data_type(*data)
        ret = self.lib.icp_write_flash(ctypes.c_uint32(addr), ctypes.c_uint32(length), data_buffer)
        return int(ret)

    def mass_erase(self):
        self.lib.icp_mass_erase()

    def page_erase(self,addr):
        self.lib.icp_page_erase(ctypes.c_uint32(addr))

class LibPGM:
    def __init__(self, libname = "pigpio"):
        # Load the shared library
        if libname.lower() == "pigpio":
            self.lib = ctypes.CDLL(dir_path + "/libnuvoicp-pigpio.so")
        elif libname.lower() == "gpiod":
            self.lib = ctypes.CDLL(dir_path + "/libnuvoicp-gpiod.so")
        else:
            raise ValueError("Unknown lib: %s\nMust be either 'pigpio' or 'gpiod'" % libname)
        # Initialize the PGM interface.
        self.lib.pgm_init.argtypes = []
        self.lib.pgm_init.restype = ctypes.c_int

        # Shutdown the PGM interface.
        self.lib.pgm_deinit.argtypes = []
        self.lib.pgm_set_dat.restype = None

        # Set the PGM data pin to the given value.
        self.lib.pgm_set_dat.argtypes = [ctypes.c_ubyte]
        self.lib.pgm_set_dat.restype = None

        # Get the current value of the PGM data pin.
        self.lib.pgm_get_dat.argtypes = []
        self.lib.pgm_get_dat.restype = ctypes.c_ubyte

        # Set the PGM reset pin to the given value.
        self.lib.pgm_set_rst.argtypes = [ctypes.c_ubyte]
        self.lib.pgm_set_rst.restype = None

        # Set the PGM clock pin to the given value.
        self.lib.pgm_set_clk.argtypes = [ctypes.c_ubyte]
        self.lib.pgm_set_clk.restype = None

        self.lib.pgm_set_trigger.argtypes = [ctypes.c_ubyte]
        self.lib.pgm_set_trigger.restype = None

        # Sets the direction of the PGM data pin
        self.lib.pgm_dat_dir.argtypes = [ctypes.c_ubyte]
        self.lib.pgm_dat_dir.restype = None

        # Releases all PGM pins by setting them to INPUT mode.
        self.lib.pgm_release_pins.argtypes = []
        self.lib.pgm_release_pins.restype = None

        # Releases the RST pin only
        self.lib.pgm_release_rst.argtypes = []
        self.lib.pgm_release_rst.restype = None

        self.lib.pgm_set_cmd_bit_delay.argtypes = [ctypes.c_int]
        self.lib.pgm_set_cmd_bit_delay.restype = None

        self.lib.pgm_set_read_bit_delay.argtypes = [ctypes.c_int]
        self.lib.pgm_set_read_bit_delay.restype = None

        self.lib.pgm_set_write_bit_delay.argtypes = [ctypes.c_int]
        self.lib.pgm_set_write_bit_delay.restype = None

        self.lib.pgm_get_cmd_bit_delay.argtypes = []
        self.lib.pgm_get_cmd_bit_delay.restype = ctypes.c_int

        self.lib.pgm_get_read_bit_delay.argtypes = []
        self.lib.pgm_get_read_bit_delay.restype = ctypes.c_int

        self.lib.pgm_get_write_bit_delay.argtypes = []
        self.lib.pgm_get_write_bit_delay.restype = ctypes.c_int

        # Device-specific sleep function
        self.lib.pgm_usleep.argtypes = [ctypes.c_ulong]
        self.lib.pgm_usleep.restype = None

        # Device-specific print function
        self.lib.pgm_print.argtypes = [ctypes.c_char_p]
        self.lib.pgm_print.restype = None

    # Initialize the PGM interface.
    def init(self) -> bool:
        return True if self.lib.pgm_init() == 0 else False

    # Shutdown the PGM interface.
    def deinit(self):
        self.lib.pgm_deinit()

    # Set the PGM data pin to the given value.
    def set_dat(self, val):
        self.lib.pgm_set_dat(ctypes.c_ubyte(val))

    # Get the current value of the PGM data pin.
    def get_dat(self)-> int:
        return int(self.lib.pgm_get_dat())

    # Set the PGM reset pin to the given value.
    def set_rst(self, val):
        self.lib.pgm_set_rst(ctypes.c_ubyte(val))

    # Set the PGM clock pin to the given value.
    def set_clk(self, val):
        self.lib.pgm_set_clk(ctypes.c_ubyte(val))

    # Sets the direction of the PGM data pin
    def dat_dir(self, state):
        self.lib.pgm_dat_dir(ctypes.c_ubyte(state))

    # Releases all PGM pins by setting them to INPUT mode.
    def release_pins(self):
        self.lib.pgm_release_pins()

    # Releases the RST pin only
    def release_rst(self):
        self.lib.pgm_release_rst()

    def set_trigger(self, val):
        self.lib.pgm_set_trigger(ctypes.c_ubyte(val))

    def set_read_bit_delay(self, val):
        self.lib.pgm_set_read_bit_delay(ctypes.c_int(val))

    def set_cmd_bit_delay(self, val):
        self.lib.pgm_set_cmd_bit_delay(ctypes.c_int(val))

    def set_write_bit_delay(self, val):
        self.lib.pgm_set_write_bit_delay(ctypes.c_int(val))

    def get_read_bit_delay(self):
        return int(self.lib.pgm_get_read_bit_delay())

    def get_cmd_bit_delay(self):
        return int(self.lib.pgm_get_cmd_bit_delay())

    def get_write_bit_delay(self):
        return int(self.lib.pgm_get_write_bit_delay())

    # Device-specific sleep function
    def usleep(self, usec):
        self.lib.pgm_usleep(ctypes.c_ulong(usec))

    # Device-specific print function
    def print(self, msg):
        self.lib.pgm_print(ctypes.c_char_p(msg.encode()))

