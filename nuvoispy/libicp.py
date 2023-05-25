import ctypes

# get dir of this file
import os
dir_path = os.path.dirname(os.path.realpath(__file__))

# Load the shared library
lib = ctypes.CDLL(dir_path + "/libnuvoicp.so")

# Function prototypes
lib.icp_init.argtypes = [ctypes.c_uint8]
lib.icp_init.restype = ctypes.c_int

lib.icp_reentry.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32]
lib.icp_reentry.restype = None

lib.icp_reentry_glitch.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
lib.icp_reentry_glitch.restype = None

lib.icp_reentry_glitch_read.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint8)]
lib.icp_reentry_glitch_read.restype = None

lib.icp_exit.argtypes = []
lib.icp_exit.restype = None

lib.icp_read_device_id.argtypes = []
lib.icp_read_device_id.restype = ctypes.c_uint32

lib.icp_read_pid.argtypes = []
lib.icp_read_pid.restype = ctypes.c_uint32

lib.icp_read_cid.argtypes = []
lib.icp_read_cid.restype = ctypes.c_uint8

lib.icp_read_uid.argtypes = []
lib.icp_read_uid.restype = ctypes.c_uint32

lib.icp_read_ucid.argtypes = []
lib.icp_read_ucid.restype = ctypes.c_uint32

lib.icp_read_flash.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint8)]
lib.icp_read_flash.restype = ctypes.c_uint32

lib.icp_write_flash.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint8)]
lib.icp_write_flash.restype = ctypes.c_uint32

lib.icp_mass_erase.argtypes = []
lib.icp_mass_erase.restype = None

lib.icp_page_erase.argtypes = [ctypes.c_uint32]
lib.icp_page_erase.restype = None

# Wrapper functions

def icp_init(do_reset = True) -> bool:
    ret = lib.icp_init(ctypes.c_uint8(do_reset)) 
    return True if ret == 0 else False

def icp_reentry(delay1 = 5000, delay2 = 1000, delay3 = 10):
    lib.icp_reentry(ctypes.c_uint32(delay1), ctypes.c_uint32(delay2), ctypes.c_uint32(delay3))

def icp_reentry_glitch(delay1 = 5000, delay2 = 1000) -> None:
    lib.icp_reentry_glitch(ctypes.c_uint32(delay1), ctypes.c_uint32(delay2))

def icp_reentry_glitch_read(delay1 = 5000, delay2 = 1000) -> bytes:
    data_type = ctypes.c_uint8 * 5
    data = data_type()
    lib.icp_reentry_glitch_read(ctypes.c_uint32(delay1), ctypes.c_uint32(delay2), data)
    return bytes(data)

def icp_exit():
    lib.icp_exit()

def icp_read_device_id():
    return lib.icp_read_device_id()

def icp_read_pid():
    return lib.icp_read_pid()

def icp_read_cid():
    return lib.icp_read_cid()

def icp_read_uid():
    return lib.icp_read_uid()

def icp_read_ucid():
    return lib.icp_read_ucid()

def icp_read_flash(addr, length):
    data_type = ctypes.c_uint8 * length
    data = data_type()
    lib.icp_read_flash(ctypes.c_uint32(addr), ctypes.c_uint32(length), data)
    return bytes(data)

def icp_write_flash(addr, data) -> int:
    length = len(data)
    data_type = ctypes.c_uint8 * length
    data_buffer = data_type(*data)
    ret = lib.icp_write_flash(ctypes.c_uint32(addr), ctypes.c_uint32(length), data_buffer)
    return int(ret)

def icp_mass_erase():
    lib.icp_mass_erase()

def icp_page_erase(addr):
    lib.icp_page_erase(ctypes.c_uint32(addr))

# default module export function: exports all of the above
def export():
    return {
        "icp_init": icp_init,
        "icp_reentry": icp_reentry,
        "icp_exit": icp_exit,
        "icp_read_device_id": icp_read_device_id,
        "icp_read_pid": icp_read_pid,
        "icp_read_cid": icp_read_cid,
        "icp_read_uid": icp_read_uid,
        "icp_read_ucid": icp_read_ucid,
        "icp_read_flash": icp_read_flash,
        "icp_write_flash": icp_write_flash,
        "icp_mass_erase": icp_mass_erase,
        "icp_page_erase": icp_page_erase
    }

# EOF