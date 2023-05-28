import ctypes
from enum import Enum

# get dir of this file
import os
dir_path = os.path.dirname(os.path.realpath(__file__))


# Load the shared library
lib = ctypes.CDLL(dir_path + "/libnuvoicp.so")


# Initialize the PGM interface.
lib.pgm_init.argtypes = []
lib.pgm_init.restype = ctypes.c_int

# Shutdown the PGM interface.
lib.pgm_deinit.argtypes = []
lib.pgm_set_dat.restype = None

# Set the PGM data pin to the given value.
lib.pgm_set_dat.argtypes = [ctypes.c_ubyte]
lib.pgm_set_dat.restype = None

# Get the current value of the PGM data pin.
lib.pgm_get_dat.argtypes = []
lib.pgm_get_dat.restype = ctypes.c_ubyte

# Set the PGM reset pin to the given value.
lib.pgm_set_rst.argtypes = [ctypes.c_ubyte]
lib.pgm_set_rst.restype = None

# Set the PGM clock pin to the given value.
lib.pgm_set_clk.argtypes = [ctypes.c_ubyte]
lib.pgm_set_clk.restype = None

lib.pgm_set_trigger.argtypes = [ctypes.c_ubyte]
lib.pgm_set_trigger.restype = None

# Sets the direction of the PGM data pin
lib.pgm_dat_dir.argtypes = [ctypes.c_ubyte]
lib.pgm_dat_dir.restype = None

# Releases all PGM pins by setting them to INPUT mode.
lib.pgm_release_pins.argtypes = []
lib.pgm_release_pins.restype = None

# Releases the RST pin only
lib.pgm_release_rst.argtypes = []
lib.pgm_release_rst.restype = None

lib.pgm_set_cmd_bit_delay.argtypes = [ctypes.c_int]
lib.pgm_set_cmd_bit_delay.restype = None

lib.pgm_set_read_bit_delay.argtypes = [ctypes.c_int]
lib.pgm_set_read_bit_delay.restype = None

lib.pgm_set_write_bit_delay.argtypes = [ctypes.c_int]
lib.pgm_set_write_bit_delay.restype = None

lib.pgm_get_cmd_bit_delay.argtypes = []
lib.pgm_get_cmd_bit_delay.restype = ctypes.c_int

lib.pgm_get_read_bit_delay.argtypes = []
lib.pgm_get_read_bit_delay.restype = ctypes.c_int

lib.pgm_get_write_bit_delay.argtypes = []
lib.pgm_get_write_bit_delay.restype = ctypes.c_int

# Device-specific sleep function
lib.pgm_usleep.argtypes = [ctypes.c_ulong]
lib.pgm_usleep.restype = None

# Device-specific print function
lib.pgm_print.argtypes = [ctypes.c_char_p]
lib.pgm_print.restype = None

# Initialize the PGM interface.
def pgm_init() -> bool:
    return True if lib.pgm_init() == 0 else False

# Shutdown the PGM interface.
def pgm_deinit():
    lib.pgm_deinit()

# Set the PGM data pin to the given value.
def pgm_set_dat(val):
    lib.pgm_set_dat(ctypes.c_ubyte(val))

# Get the current value of the PGM data pin.
def pgm_get_dat()-> int:
    return int(lib.pgm_get_dat())

# Set the PGM reset pin to the given value.
def pgm_set_rst(val):
    lib.pgm_set_rst(ctypes.c_ubyte(val))

# Set the PGM clock pin to the given value.
def pgm_set_clk(val):
    lib.pgm_set_clk(ctypes.c_ubyte(val))

# Sets the direction of the PGM data pin
def pgm_dat_dir(state):
    lib.pgm_dat_dir(ctypes.c_ubyte(state))

# Releases all PGM pins by setting them to INPUT mode.
def pgm_release_pins():
    lib.pgm_release_pins()

# Releases the RST pin only
def pgm_release_rst():
    lib.pgm_release_rst()

def pgm_set_trigger(val):
    lib.pgm_set_trigger(ctypes.c_ubyte(val))

def pgm_set_read_bit_delay(val):
    lib.pgm_set_read_bit_delay(ctypes.c_int(val))

def pgm_set_cmd_bit_delay(val):
    lib.pgm_set_cmd_bit_delay(ctypes.c_int(val))

def pgm_set_write_bit_delay(val):
    lib.pgm_set_write_bit_delay(ctypes.c_int(val))

def pgm_get_read_bit_delay():
    return int(lib.pgm_get_read_bit_delay())

def pgm_get_cmd_bit_delay():
    return int(lib.pgm_get_cmd_bit_delay())

def pgm_get_write_bit_delay():
    return int(lib.pgm_get_write_bit_delay())

# Device-specific sleep function
def pgm_usleep(usec):
    lib.pgm_usleep(ctypes.c_ulong(usec))

# Device-specific print function
def pgm_print(msg):
    lib.pgm_print(ctypes.c_char_p(msg.encode()))

