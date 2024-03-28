import ctypes

# get dir of this file
import os
import platform
import signal
dir_path = os.path.dirname(os.path.realpath(__file__))

if platform.system() != 'Linux':
    raise NotImplementedError("%s is not supported yet" % platform.system())

# detect if we are on a raspberry pi
def is_raspberry_pi():
    # check if /sys/firmware/devicetree/base/model exists
    if os.path.isfile("/sys/firmware/devicetree/base/model"):
        with open("/sys/firmware/devicetree/base/model", "r") as f:
            model = f.read().strip()
            if model.startswith("Raspberry Pi"):
                return True
    return False

# pigpio is dumb and overrides the signal handlers for SIGINT and SIGTERM
# so every time we call anything that calls gpioInitialise(), we need to override the signal handlers
def catch_ctrlc(signum, frame):
    if signum == signal.SIGINT:
        raise KeyboardInterrupt("Caught SIGINT")
    elif signum == signal.SIGTERM:
        # raise a non-KeyboardInterrupt exception
        raise Exception("Caught SIGTERM")


def override_signals():
    signal.signal(signal.SIGINT, catch_ctrlc)
    signal.signal(signal.SIGTERM, catch_ctrlc)

class LibICP:
    def __init__(self, libname="gpiod"):
        if not is_raspberry_pi():
            raise NotImplementedError("This library is only supported on a Raspberry Pi")
        # Load the shared library
        self.libname = libname
        if libname.lower() == "pigpio":
            self.lib = ctypes.CDLL(dir_path + "/libnuvo51icp-pigpio.so")
        elif libname.lower() == "gpiod":
            self.lib = ctypes.CDLL(dir_path + "/libnuvo51icp-gpiod.so")
        else:
            raise ValueError(
                "Unknown lib: %s\nMust be either 'pigpio' or 'gpiod'" % libname)

        # Function prototypes
        self.lib.N51ICP_send_entry_bits.argtypes = []
        self.lib.N51ICP_send_entry_bits.restype = None

        self.lib.N51ICP_send_exit_bits.argtypes = []
        self.lib.N51ICP_send_exit_bits.restype = None

        self.lib.N51ICP_init.argtypes = [ctypes.c_uint8]
        self.lib.N51ICP_init.restype = ctypes.c_int

        self.lib.N51ICP_enter_icp_mode.argtypes = [ctypes.c_uint8]
        self.lib.N51ICP_enter_icp_mode.restype = None

        self.lib.N51ICP_reentry.argtypes = [
            ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32]
        self.lib.N51ICP_reentry.restype = None

        self.lib.N51ICP_reentry_glitch.argtypes = [
            ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32]
        self.lib.N51ICP_reentry_glitch.restype = None

        self.lib.N51ICP_deinit.argtypes = [ctypes.c_uint8]
        self.lib.N51ICP_deinit.restype = None

        self.lib.N51ICP_exit_icp_mode.argtypes = []
        self.lib.N51ICP_exit_icp_mode.restype = None

        self.lib.N51ICP_read_device_id.argtypes = []
        self.lib.N51ICP_read_device_id.restype = ctypes.c_uint32

        self.lib.N51ICP_read_pid.argtypes = []
        self.lib.N51ICP_read_pid.restype = ctypes.c_uint32

        self.lib.N51ICP_read_cid.argtypes = []
        self.lib.N51ICP_read_cid.restype = ctypes.c_uint8

        self.lib.N51ICP_read_uid.argtypes = [ctypes.POINTER(ctypes.c_uint8)]
        self.lib.N51ICP_read_uid.restype = None

        self.lib.N51ICP_read_ucid.argtypes = [ctypes.POINTER(ctypes.c_uint8)]
        self.lib.N51ICP_read_ucid.restype = None

        self.lib.N51ICP_read_flash.argtypes = [
            ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint8)]
        self.lib.N51ICP_read_flash.restype = ctypes.c_uint32

        self.lib.N51ICP_write_flash.argtypes = [
            ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint8)]
        self.lib.N51ICP_write_flash.restype = ctypes.c_uint32

        self.lib.N51ICP_mass_erase.argtypes = []
        self.lib.N51ICP_mass_erase.restype = None

        self.lib.N51ICP_page_erase.argtypes = [ctypes.c_uint32]
        self.lib.N51ICP_page_erase.restype = None

        self.lib.N51ICP_set_program_time.argtypes = [ctypes.c_uint32]
        self.lib.N51ICP_set_program_time.restype = None
    
        self.lib.N51ICP_set_page_erase_time.argtypes = [ctypes.c_uint32]
        self.lib.N51ICP_set_page_erase_time.restype = None

        # Wrapper functions

    def send_entry_bits(self) -> bool:
        self.lib.N51ICP_send_entry_bits()
        return True

    def send_exit_bits(self) -> bool:
        self.lib.N51ICP_send_exit_bits()
        return True

    def init(self, do_reset=True) -> bool:
        ret = self.lib.N51ICP_init(ctypes.c_uint8(do_reset))
        if ret == 0:  # PGM initialized
            # This ends up calling gpioInitialise(), so take the signals back
            if self.libname == "pigpio":
                override_signals()
            return True
        # ret != 0 means PGM not initialized, don't override signals
        return False

    def entry(self, do_reset=True) -> bool:
        self.lib.N51ICP_enter_icp_mode(ctypes.c_uint8(do_reset))
        return True

    def reentry(self, delay1=5000, delay2=1000, delay3=10) -> bool:
        self.lib.N51ICP_reentry(ctypes.c_uint32(
            delay1), ctypes.c_uint32(delay2), ctypes.c_uint32(delay3))
        return True

    def reentry_glitch(self, delay1=5000, delay2=1000, delay_after_trigger_high=0, delay_before_trigger_low=280) -> bool:
        self.lib.N51ICP_reentry_glitch(ctypes.c_uint32(delay1), ctypes.c_uint32(delay2), ctypes.c_uint32(
            delay_after_trigger_high), ctypes.c_uint32(delay_before_trigger_low))
        return True

    def deinit(self, leave_reset_high: bool) -> bool:
        val = 1 if leave_reset_high else 0
        self.lib.N51ICP_deinit(ctypes.c_ubyte(val))
        return True

    def exit(self) -> bool:
        self.lib.N51ICP_exit_icp_mode()
        return True

    def read_device_id(self):
        return self.lib.N51ICP_read_device_id()

    def read_pid(self) -> int:
        return self.lib.N51ICP_read_pid()

    def read_cid(self) -> int:
        return self.lib.N51ICP_read_cid()

    def read_uid(self) -> bytes:
        data_type = ctypes.c_uint8 * 12
        data = data_type()
        self.lib.N51ICP_read_uid(data)
        return bytes(data)

    def read_ucid(self) -> bytes:
        data_type = ctypes.c_uint8 * 16
        data = data_type()
        self.lib.N51ICP_read_ucid(data)
        return bytes(data)

    def read_flash(self, addr, length) -> bytes:
        data_type = ctypes.c_uint8 * length
        data = data_type()
        self.lib.N51ICP_read_flash(ctypes.c_uint32(
            addr), ctypes.c_uint32(length), data)
        return bytes(data)

    def write_flash(self, addr, data) -> int:
        length = len(data)
        data_type = ctypes.c_uint8 * length
        data_buffer = data_type(*data)
        ret = self.lib.N51ICP_write_flash(ctypes.c_uint32(
            addr), ctypes.c_uint32(length), data_buffer)
        return int(ret)

    def mass_erase(self) -> bool:
        self.lib.N51ICP_mass_erase()
        return True

    def page_erase(self, addr) -> bool:
        self.lib.N51ICP_page_erase(ctypes.c_uint32(addr))
        return True

    def set_program_time(self, time_us: int) -> bool:
        self.lib.N51ICP_set_program_time(ctypes.c_uint32(time_us))
        return True

    def set_page_erase_time(self, time_us: int) -> bool:
        self.lib.N51ICP_set_page_erase_time(ctypes.c_uint32(time_us))
        return True

class LibPGM:
    def __init__(self, libname="gpiod"):
        # Load the shared library
        self.libname = libname
        if libname.lower() == "pigpio":
            self.lib = ctypes.CDLL(dir_path + "/libnuvo51icp-pigpio.so")
        elif libname.lower() == "gpiod":
            self.lib = ctypes.CDLL(dir_path + "/libnuvo51icp-gpiod.so")
        else:
            raise ValueError(
                "Unknown lib: %s\nMust be either 'pigpio' or 'gpiod'" % libname)
        # Initialize the PGM interface.
        self.lib.N51PGM_init.argtypes = []
        self.lib.N51PGM_init.restype = ctypes.c_int

        # Shutdown the PGM interface.
        self.lib.N51PGM_deinit.argtypes = [ctypes.c_ubyte]
        self.lib.N51PGM_set_dat.restype = None

        # Set the PGM data pin to the given value.
        self.lib.N51PGM_set_dat.argtypes = [ctypes.c_ubyte]
        self.lib.N51PGM_set_dat.restype = None

        # Get the current value of the PGM data pin.
        self.lib.N51PGM_get_dat.argtypes = []
        self.lib.N51PGM_get_dat.restype = ctypes.c_ubyte

        # Set the PGM reset pin to the given value.
        self.lib.N51PGM_set_rst.argtypes = [ctypes.c_ubyte]
        self.lib.N51PGM_set_rst.restype = None

        # Set the PGM clock pin to the given value.
        self.lib.N51PGM_set_clk.argtypes = [ctypes.c_ubyte]
        self.lib.N51PGM_set_clk.restype = None

        self.lib.N51PGM_set_trigger.argtypes = [ctypes.c_ubyte]
        self.lib.N51PGM_set_trigger.restype = None

        # Sets the direction of the PGM data pin
        self.lib.N51PGM_dat_dir.argtypes = [ctypes.c_ubyte]
        self.lib.N51PGM_dat_dir.restype = None

        # Device-specific sleep function
        self.lib.N51PGM_usleep.argtypes = [ctypes.c_uint32]
        self.lib.N51PGM_usleep.restype = ctypes.c_uint32

        # Device-specific print function
        self.lib.N51PGM_print.argtypes = [ctypes.c_char_p]
        self.lib.N51PGM_print.restype = None

    # Initialize the PGM interface.
    def init(self) -> bool:
        ret = self.lib.N51PGM_init()
        if ret < 0:  # PGM failed to initialize
            # This ends up calling gpioInitialise(), so take the signals back
            if self.libname == "pigpio":
                override_signals()
            return True
        return False

    # Shutdown the PGM interface.
    def deinit(self, leave_reset_high=True):
        self.lib.N51PGM_deinit(ctypes.c_ubyte(1 if leave_reset_high else 0))

    # Set the PGM data pin to the given value.
    def set_dat(self, val):
        self.lib.N51PGM_set_dat(ctypes.c_ubyte(val))

    # Get the current value of the PGM data pin.
    def get_dat(self) -> int:
        return int(self.lib.N51PGM_get_dat())

    # Set the PGM reset pin to the given value.
    def set_rst(self, val):
        self.lib.N51PGM_set_rst(ctypes.c_ubyte(val))

    # Set the PGM clock pin to the given value.
    def set_clk(self, val):
        self.lib.N51PGM_set_clk(ctypes.c_ubyte(val))

    # Sets the direction of the PGM data pin
    def dat_dir(self, state):
        self.lib.N51PGM_dat_dir(ctypes.c_ubyte(state))

    def set_trigger(self, val):
        self.lib.N51PGM_set_trigger(ctypes.c_ubyte(val))

    # Device-specific sleep function

    def usleep(self, usec):
        return int(self.lib.N51PGM_usleep(ctypes.c_uint32(usec)))

    # Device-specific print function
    def print(self, msg):
        self.lib.N51PGM_print(ctypes.c_char_p(msg.encode()))
