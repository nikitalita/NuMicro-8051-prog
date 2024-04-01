from curses import flash
import json
import struct
import ctypes
from typing import Tuple

try:
    from .Flash import Flash_8051 as _Flash_8051
    from .PartNumID import lookup_name_and_type, ChipType
except:
    from Flash import Flash_8051 as _Flash_8051
    from PartNumID import lookup_name_and_type, ChipType

N76E003_DEVID = 0x3650
APROM_ADDR = 0

CFG_FLASH_ADDR = 0x30000
CFG_FLASH_LEN = 5

SPROM_ADDR = 0x20180
SPROM_LEN = 128

# N76E003 values only for now
LDROM_MAX_SIZE = 4 * 1024
FLASH_SIZE = 18 * 1024


class FlashInfo:
    # stub class
    def __init__(self):
        raise NotImplementedError("Don't call the constructor! Call `get_flash_info` instead!")
    
    @property
    def max_memory_size(self):
        raise NotImplementedError("Not implemented!")
    
    @property
    def static_ldrom_size(self):
        raise NotImplementedError("Not implemented!")
    
    @property
    def maximum_ldrom_size(self):
        raise NotImplementedError("Not implemented!")
    
    def get_ldrom_size(self, config):
        raise NotImplementedError("Not implemented!")
    
    def get_aprom_size(self, config):
        raise NotImplementedError("Not implemented!")
    
    def get_dataflash_size(self, config):
        raise NotImplementedError("Not implemented!")
    
    def get_dataflash_addr(self, config):
        raise NotImplementedError("Not implemented!")
    
    @property
    def ram_size(self):
        raise NotImplementedError("Not implemented!")
    
    @property
    def did(self):
        raise NotImplementedError("Not implemented!")
    
    @property
    def flash_type(self):
        raise NotImplementedError("Not implemented!")
    
    @property
    def max_dataflash_size(self):
        raise NotImplementedError("Not implemented!")
    
    @property
    def dataflash_addr(self):
        raise NotImplementedError("Not implemented!")
    
    @property
    def page_size(self):
        raise NotImplementedError("Not implemented!")
    
    @property
    def has_configurable_size_ldrom(self):
        raise NotImplementedError("Not implemented!")
    
    @property
    def config_addr(self):
        raise NotImplementedError("Not implemented!")

    @property
    def config_len(self):
        raise NotImplementedError("Not implemented!")

    @property
    def sprom_addr(self):
        raise NotImplementedError("Not implemented!")

    @property
    def sprom_len(self):
        raise NotImplementedError("Not implemented!")
    
    @property
    def program_times(self) -> Tuple[int, int]:
        raise NotImplementedError("Not implemented!")
    
    @property
    def page_erase_times(self) -> Tuple[int, int]:
        raise NotImplementedError("Not implemented!")
    
    @property
    def mass_erase_times(self) -> Tuple[int, int]:
        raise NotImplementedError("Not implemented!")


class FlashInfo8051(FlashInfo):
    def __init__(self, memory_size:int, LDROM_size:int, RAM_size:int, DID:int, Flash_type:int):
        self._memory_size = memory_size
        self._LDROM_size = LDROM_size
        self._RAM_size = RAM_size
        self._DID = DID
        self._Flash_type = Flash_type
        _, type = lookup_name_and_type(DID)
        self._chip_type = type

    @property
    def max_memory_size(self):
        return self._memory_size

    @property
    def static_ldrom_size(self):
        # return self._LDROM_size
        # they're all 0
        return 0
    
    @property
    def maximum_ldrom_size(self):
        return 4 * 1024
    
    def get_ldrom_size(self, config):
        return config.get_ldrom_size()
    
    def get_aprom_size(self, config):
        return self.max_memory_size - self.get_dataflash_size(config) - self.get_ldrom_size(config)
    
    def get_dataflash_size(self, config):
        data_flash_size = self.max_dataflash_size
        if data_flash_size > 0:
            data_flash_size -= self.get_ldrom_size(config)
        return data_flash_size
    
    def get_dataflash_addr(self, config):
        return self.get_aprom_size(config)
    
    @property
    def ram_size(self):
        return self._RAM_size
    
    @property
    def did(self):
        return self._DID
    
    @property
    def flash_type(self):
        return self._Flash_type

    @property
    def max_dataflash_size(self):
        if self.flash_type & 0x3 != 0:
            return 0x2800
        return 0
    
    @property
    def page_size(self):
        return 128
    
    @property
    def has_configurable_size_ldrom(self):
        return True

    @property
    def config_addr(self):
        return CFG_FLASH_ADDR

    @property
    def config_len(self):
        return CFG_FLASH_LEN

    @property
    def has_sprom(self):
        return self.flash_type & 0x70

    @property
    def sprom_addr(self):
        """
        TODO: This is a guess; Need to check to see if N76S003 actually has SPROM
        If it does, this is correct; if not, we should check bit 24.
        """
        # check if bits [6:4] are set
        if self.flash_type & 0x70:
            return SPROM_ADDR
        return 0

    @property
    def sprom_len(self):
        if self.flash_type & 0x70:
            return SPROM_LEN
        return 0

    @property
    def program_times(self) -> Tuple[int, int]:
        if self.flash_type & 0x4:
            return (40, 5)
        return (25, 5)
    
    @property
    def page_erase_times(self) -> Tuple[int, int]:
        if self.flash_type & 0x4:
            return (40000, 100)
        return (6000, 100)
    
    @property
    def mass_erase_times(self) -> Tuple[int, int]:
        return (65000, 1000)


def dump_Flash_8051_to_dict():
    flash_8051_dict = {}
    for flash in _Flash_8051:
        flash_8051_dict[flash[3]] = FlashInfo8051(flash[0], flash[1], flash[2], flash[3], flash[4])
    return flash_8051_dict

Flash_8051: dict[int, FlashInfo8051] = dump_Flash_8051_to_dict()


# supported_types = [ChipType.N76E003, ChipType.MS51_16K, ChipType.MS51_32K, ChipType.MG51]

def get_flash_info(device_id: int) -> FlashInfo:
    did = device_id & 0xFFFF
    if did in Flash_8051:
        # have to do this because one of the 8051 chips shares a DID with a NuMicro chip
        _, type = lookup_name_and_type(device_id)
        if type != ChipType.UNKNOWN and not type.is_8051:
            return FlashInfo8051(0, 0, 0, did, 0)
        return Flash_8051[did]
    return FlashInfo8051(0, 0, 0, did, 0)

class DeviceInfo:
    def __init__(self, device_id=0xFFFF, pid=0x0000):
        self._did = device_id
        self._pid = 0
        self.pid = pid

    def _refresh_flash_info(self):
        self.flash_info: FlashInfo = get_flash_info(self.device_id)
        name, chip_type = lookup_name_and_type(self.device_id)
        self._name = name
        self._chip_type = chip_type

    @property
    def did(self):
        return self._did
    
    @did.setter
    def did(self, did):
        self._did = did
        self._refresh_flash_info()

    @property
    def pid(self):
        return self._pid

    @pid.setter
    def pid(self, pid):
        if pid == self.did and pid != 0xffff:
            pid = 0
        self._pid = pid
        self._refresh_flash_info() 
    
    @property
    def device_id(self):
        if self.did & 0xFFFF == self.did:
            return self.did | (self.pid << 16)
        else:
            return self.did
    
    @property
    def aprom_addr(self): # it's always 0
        return 0

    @property
    def ldrom_max_size(self):
        return self.flash_info.maximum_ldrom_size

    @property
    def flash_size(self):
        return self.flash_info.max_memory_size
        
    @property
    def max_nvm_size(self):
        return self.flash_info.max_dataflash_size
    
    @property
    def config_addr(self):
        return self.flash_info.config_addr
    
    @property
    def config_len(self):
        return self.flash_info.config_len

    @property
    def is_unsupported(self):
        if self._chip_type.is_8051:
            return False
        return True
    
    @property
    def chip_name(self):
        return self._name
    
    @property
    def chip_type(self):
        return self._chip_type
    
    @property
    def page_size(self):
        return self.flash_info.page_size
    
    @property
    def has_configurable_size_ldrom(self):
        return self.flash_info.has_configurable_size_ldrom
    
    @property
    def sprom_addr(self):
        return self.flash_info.sprom_addr

    @property
    def sprom_len(self):
        return self.flash_info.sprom_len

    @property
    def program_times(self) -> Tuple[int, int]:
        return self.flash_info.program_times
    
    @property
    def page_erase_times(self) -> Tuple[int, int]:
        return self.flash_info.page_erase_times
    
    @property
    def mass_erase_times(self) -> Tuple[int, int]:
        return self.flash_info.mass_erase_times

    def get_aprom_size(self, config):
        return self.flash_info.get_aprom_size(config)
    
    def get_ldrom_size(self, config):
        return self.flash_info.get_ldrom_size(config)
    
    def get_ldrom_addr(self, config):
        return self.get_aprom_size(config)
    
    def get_dataflash_size(self, config):
        return self.flash_info.get_dataflash_size(config)

    def get_dataflash_addr(self, config):
        return self.flash_info.get_dataflash_addr(config)

    def __str__(self):
        ret = "Device ID: 0x{:08X} ({})\n".format(self.device_id, self.chip_name)
        ret += "RAM size: %d bytes\n" % self.flash_info.ram_size
        ret += "Max Flash size: %d kB\n" % (self.flash_size // 1024)
        ret += "Max LDROM size: %d kB\n" % (self.ldrom_max_size // 1024)
        ret += "Max NVM size: %d kB\n" % (self.max_nvm_size // 1024)
        return ret

def float_index_to_bit(bit: float) -> int:
    # get the byte
    bytenum = int(bit)
    # get the bit
    bitshift = int((bit - bytenum) * 10)
    if bitshift > 7:
        bytenum += 1
        bitshift = bitshift - 8
    return (bytenum, bitshift)

class ConfigFlags:
    def __init__(self, cfg_bytes: list = None):
        raise NotImplementedError("Don't call the constructor! Call `from_bytes` or `from_json` instead!")
    
    def to_bytes(self) -> bytes:
        raise NotImplementedError("Not implemented!")

    # get the size of the LDROM in bytes
    def get_ldrom_size(self) -> int:
        raise NotImplementedError("Not implemented!")

    def get_ldrom_size_kb(self) -> int:
        raise NotImplementedError("Not implemented!")

    def is_locked(self) -> bool:
        raise NotImplementedError("Not implemented!")

    def is_ldrom_boot(self):
        raise NotImplementedError("Not implemented!")

    def is_ocd_enabled(self):
        raise NotImplementedError("Not implemented!")

    def is_brownout_detect(self):
        raise NotImplementedError("Not implemented!")

    def is_brownout_reset(self):
        raise NotImplementedError("Not implemented!")

    def is_wdt_enabled(self):
        raise NotImplementedError("Not implemented!")

    def is_wdt_keep_active(self):
        raise NotImplementedError("Not implemented!")

    def is_brownout_inhibits_IAP(self):
        raise NotImplementedError("Not implemented!")

    def set_ldrom_boot(self, enable: bool) -> bool:
        raise NotImplementedError("Not implemented!")

    # Set ldrom size in bytes

    def set_ldrom_size(self, size: int):
        raise NotImplementedError("Not implemented!")

    # Set ldrom size in KB
    def set_ldrom_size_kb(self, size_kb: int):
        raise NotImplementedError("Not implemented!")

    def set_brownout_detect(self, enable: bool) -> bool:
        raise NotImplementedError("Not implemented!")

    def set_brownout_reset(self, enable: bool) -> bool:
        raise NotImplementedError("Not implemented!")

    def set_ocd_enable(self, enable: bool) -> bool:
        raise NotImplementedError("Not implemented!")

    def set_brownout_inhibits_IAP(self, enable: bool) -> bool:
        raise NotImplementedError("Not implemented!")

    def get_brown_out_voltage(self):
        raise NotImplementedError("Not implemented!")

    def set_brownout_voltage(self, voltage: float) -> bool:
        raise NotImplementedError("Not implemented!")

    def set_lock(self, enable: bool) -> bool:
        raise NotImplementedError("Not implemented!")

    def enable_ldrom(self, kb_size: int) -> bool:
        raise NotImplementedError("Not implemented!")

    def set_wdt(self, enable: bool, keep_active: bool = False) -> bool:
        raise NotImplementedError("Not implemented!")

    def get_config_status(self) -> str:
        raise NotImplementedError("Not implemented!")


    def print_config(self):
        raise NotImplementedError("Not implemented!")

    def __str__(self) -> str:
        raise NotImplementedError("Not implemented!")

    def to_json(self):
        raise NotImplementedError("Not implemented!")

    # Dumps config to file
    def to_json_file(self, filename) -> bool:
        raise NotImplementedError("Not implemented!")

    @property
    def is_unsupported(self):
        return True
        
    @staticmethod
    def from_bytes(config_bytes, device_id):
        _, type = lookup_name_and_type(device_id)
        if type.is_8051:
            return N8051ConfigFlags(config_bytes)
        return UnsupportedConfigFlags(config_bytes)

    @staticmethod
    def from_json(json, device_id = None):
        if 'config_bytes' in json and type(json['config_bytes']) == list and len(json['config_bytes']) == 5:
            config = UnsupportedConfigFlags(json['config_bytes'])
            return config
        config = N8051ConfigFlags()
        # check that key exists
        if 'lock' in json and type(json['lock']) == bool:
            config.set_lock(json['lock'])
        if 'boot_from_ldrom' in json and type(json['boot_from_ldrom']) == bool:
            config.set_ldrom_boot(json['boot_from_ldrom'])
        if 'ldrom_size' in json and json['ldrom_size'] >= 0 and json['ldrom_size'] <= 4096:
            config.set_ldrom_size(json['ldrom_size'])
        if 'OCD_enable' in json and type(json['OCD_enable']) == bool:
            config.set_ocd_enable(json['OCD_enable'])
        if 'brownout_detect' in json and type(json['brownout_detect']) == bool:
            config.set_brownout_detect(json['brownout_detect'])
        if 'brownout_reset' in json and type(json['brownout_reset']) == bool:
            config.set_brownout_reset(json['brownout_reset'])
        if 'brownout_voltage' in json and (json['brownout_voltage'] == 2.2 or json['brownout_voltage'] == 4.4 or json['brownout_voltage'] == 2.7 or json['brownout_voltage'] == 3.7):
            config.set_brownout_voltage(json['brownout_voltage'])
        if 'brownout_inhibits_IAP' in json and type(json['brownout_inhibits_IAP']) == bool:
            config.set_brownout_inhibits_IAP(json['brownout_inhibits_IAP'])
        if 'WDT_enable' in json and type(json['WDT_enable']) == bool:
            keep_active = False if not json['WDT_keep_active'] else True
            config.set_wdt(json['WDT_enable'], keep_active)
        return config

    @staticmethod
    def from_json_file(filename, device_id = None):
        try:
            with open(filename, "r") as f:
                confinfo = json.load(f)
                return ConfigFlags.from_json(confinfo, device_id)
        except:
            print("Error reading config file")
            return None

class UnsupportedConfigFlags(ConfigFlags):

    # default constructor
    # takes in a byte array
    def __init__(self, cfg_bytes: list = None):
        # print the type of bytes
        self.cfg_bytes = cfg_bytes if cfg_bytes is not None else [0xFF] * (14 * 4)

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    @property
    def is_unsupported(self):
        return True

    def to_bytes(self) -> bytes:
        return bytes(self.cfg_bytes)

    # get the size of the LDROM in bytes
    def get_ldrom_size(self) -> int:
        return None

    def get_ldrom_size_kb(self) -> int:
        return None

    def is_locked(self) -> bool:
        return False

    def is_ldrom_boot(self):
        return False

    def is_ocd_enabled(self):
        return False

    def is_brownout_detect(self):
        return False

    def is_brownout_reset(self):
        return False

    def is_wdt_enabled(self):
        return False

    def is_wdt_keep_active(self):
        return False

    def is_brownout_inhibits_IAP(self):
        return False

    def set_ldrom_boot(self, enable: bool) -> bool:
        return False

    # Set ldrom size in bytes

    def set_ldrom_size(self, size: int):
        return False

    # Set ldrom size in KB
    def set_ldrom_size_kb(self, size_kb: int):
        return False

    def set_brownout_detect(self, enable: bool) -> bool:
        return False

    def set_brownout_reset(self, enable: bool) -> bool:
        return False

    def set_ocd_enable(self, enable: bool) -> bool:
        return False

    def set_brownout_inhibits_IAP(self, enable: bool) -> bool:
        return False

    def get_brown_out_voltage(self):
        return 0

    def set_brownout_voltage(self, voltage: float) -> bool:
        return False

    def set_lock(self, enable: bool) -> bool:
        return False

    def enable_ldrom(self, kb_size: int) -> bool:
        return False

    def set_wdt(self, enable: bool, keep_active: bool = False) -> bool:
        return False

    def get_config_status(self) -> str:
        ret_str = ""
        ret_str +=("----- Chip Configuration ----\n")
        raw_bytes = self.to_bytes()
        ret_str +=("Raw config bytes:\t")
        for i in range(len(raw_bytes)):
            ret_str +=("%02X " % raw_bytes[i])
        return ret_str

    def print_config(self):
        print(self.get_config_status())

    def __str__(self) -> str:
        return " ".join(["%02X" % b for b in self.to_bytes()])

    def to_json(self):
        return json.dumps({
            "config_bytes": self.to_bytes()
        }, indent=4)

    # Dumps config to file
    def to_json_file(self, filename) -> bool:
        obj = self.to_json()
        try:
            with open(filename, "w") as f:
                f.write(obj)
                return True
        except:
            print("Error writing config file")
            return False

class N8051ConfigFlags(ctypes.LittleEndianStructure, ConfigFlags):
    _fields_ = [
        # config byte 0
        ("unk0_0", ctypes.c_uint8, 1),       # 0:0
        # Security lock bit
        # 1: unlocked, 0: locked
        ("LOCK", ctypes.c_uint8, 1),         # 0:1
        # Reset pin enable
        # 1: reset function of P2.0/Nrst pin enabled
        # 0: disabled, P2.0/Nrst only functions as input-only pin P2.0
        # 0:2 -- Please make sure you know what you're doing before unsetting this, as this will disable the reset pin and make it difficult to get back into the programmer
        ("RPD", ctypes.c_uint8, 1),
        ("unk0_3", ctypes.c_uint8, 1),       # 0:3
        # OCD enable
        # 1: OCD Disabled
        # 0: OCD Enabled
        ("OCDEN", ctypes.c_uint8, 1),         # 0:4
        # PWM output state under OCD halt
        # 1: tri-state pins are used as PWM outputs
        # 0: PWM continues
        ("OCDPWM", ctypes.c_uint8, 1),        # 0:5
        ("reserved0_6", ctypes.c_uint8, 1),  # 0:6
        # CONFIG boot selection
        # 1: MCU will reboot from APROM after resets except software reset
        # 0: MCU will reboot from LDROM after resets except software reset
        ("CBS", ctypes.c_uint8, 1),            # 0:7
        # config1
        # LDROM size select
        # 111 - No LDROM, APROM is 18k.
        # 110 = LDROM is 1K Bytes. APROM is 17K Bytes.
        # 101 = LDROM is 2K Bytes. APROM is 16K Bytes.
        # 100 = LDROM is 3K Bytes. APROM is 15K Bytes.
        # 0xx = LDROM is 4K Bytes. APROM is 14K Bytes
        ("LDS", ctypes.c_uint8, 3),          # 1:3-0
        ("unk1_3", ctypes.c_uint8, 5),       # 1:7-3
        # config2
        ("unk2_0", ctypes.c_uint8, 2),       # 2:1-0
        # CONFIG brown-out reset enable
        # 1 = Brown-out reset Enabled.
        # 0 = Brown-out reset Disabled.
        ("CBORST", ctypes.c_uint8, 1),        # 2:2
        # Brown-out inhibiting IAP
        # 1 = IAP erasing or programming is inhibited if VDD is lower than VBOD
        # 0 = IAP erasing or programming is allowed under any workable VDD.
        ("BOIAP", ctypes.c_uint8, 1),          # 2:3
        # CONFIG brown-out voltage select
        # Other NuMicro 8051 chips use the last bit, but the N76E003 doesn't
        # x11 = 2.2V
        # x10 = 2.7V
        # x01 = 3.7V
        # x00 = 4.4V
        ("CBOV", ctypes.c_uint8, 3),           # 2:6-4
        # CONFIG brown-out detect enable
        # 1 = Brown-out detection circuit on.
        # 0 = Brown-out detection circuit off.
        ("CBODEN", ctypes.c_uint8, 1),         # 2:7
        # config3 - no flags
        ("unk3", ctypes.c_uint8),            # 3:7-0
        # config4
        ("unk4_0", ctypes.c_uint8, 4),       # 4:3-0
        #  WDT enable
        #  1111 = WDT is Disabled. WDT can be used as a general purpose timer via software control
        #  0101 = WDT is Enabled as a time-out reset timer and it stops running during Idle or Power-down mode.
        #  Others = WDT is Enabled as a time-out reset timer and it keeps running during Idle or Power-down mode.
        ("WDTEN", ctypes.c_uint8, 4),       # 4:4-7
    ]

    # default constructor
    # takes in an optional 5-byte array
    def __init__(self, cfg_bytes: list = None):
        if cfg_bytes is None or len(cfg_bytes) != ctypes.sizeof(self):
            # initialize to all 0xFF
            struct.pack_into("B" * ctypes.sizeof(self), self,
                            0, *([0xFF] * ctypes.sizeof(self)))
        else:
            # initialize to the given bytes
            struct.pack_into("B" * ctypes.sizeof(self), self, 0, *cfg_bytes)

    def __getitem__(self, key):
        # # if key is int...
        # if isinstance(key, int):
        #     return self.to_bytes()[int(key)]
        # # if str is a int
        # elif isinstance(key, str) and key.isdigit():
        #     return self.to_bytes()[int(key)]
        return getattr(self, key)

    # Set item
    def __setitem__(self, key, value):
        # # if key is int...
        # if isinstance(key, int):
        #     struct.pack_into("B", self, key, value)
        # else:
            setattr(self, key, value)
    @property
    def is_unsupported(self):
        return False

    def to_bytes(self) -> bytes:
        return bytes(struct.unpack_from("B" * ctypes.sizeof(self), self))

    # get the size of the LDROM in bytes
    def get_ldrom_size(self) -> int:
        return int(self.get_ldrom_size_kb() * 1024)

    def get_ldrom_size_kb(self) -> int:
        return min((7 - (self.LDS & 0x7)), LDROM_MAX_SIZE)

    def is_locked(self) -> bool:
        return self.LOCK == 0

    def is_ldrom_boot(self):
        return self.CBS == 0

    def is_ocd_enabled(self):
        return self.OCDEN == 0

    def is_brownout_detect(self):
        return self.CBODEN == 1

    def is_brownout_reset(self):
        return self.CBORST == 1

    def is_wdt_enabled(self):
        return self.WDTEN != 0b1111

    def is_wdt_keep_active(self):
        return self.is_wdt_enabled() and self.WDTEN != 0b0101

    def is_brownout_inhibits_IAP(self):
        return self.BOIAP == 1

    def set_ldrom_boot(self, enable: bool) -> bool:
        self.CBS = 0 if enable else 1
        return True

    # Set ldrom size in bytes

    def set_ldrom_size(self, size: int):
        size_kb = int(size // 1024)
        if size % 1024 != 0:
            size_kb += 1
        self.set_ldrom_size_kb(size_kb)
        return True

    # Set ldrom size in KB
    def set_ldrom_size_kb(self, size_kb: int):
        if size_kb < 0 or size_kb > LDROM_MAX_SIZE // 1024:
            raise ValueError("Invalid LDROM size")
        self.LDS = ((7 - size_kb) & 0x7)
        return True

    def set_brownout_detect(self, enable: bool) -> bool:
        self.CBODEN = 1 if enable else 0
        return True

    def set_brownout_reset(self, enable: bool) -> bool:
        self.CBORST = 1 if enable else 0
        return True

    def set_ocd_enable(self, enable: bool) -> bool:
        self.OCDEN = 0 if enable else 1
        return True

    def set_brownout_inhibits_IAP(self, enable: bool) -> bool:
        self.BOIAP = 1 if enable else 0
        return True

    def get_brown_out_voltage(self):
        CBOV_val = self.CBOV & 0x3
        if CBOV_val == 1:
            return 3.7
        elif CBOV_val == 2:
            return 2.7
        elif CBOV_val == 3:
            return 2.2
        # else 0
        return 4.4

    def set_brownout_voltage(self, voltage: float) -> bool:
        if voltage == 2.2:
            # Don't set the last bit
            self.CBOV = 3 | 4
        elif voltage == 2.7:
            self.CBOV = 2 | 4
        elif voltage == 3.7:
            self.CBOV = 1 | 4
        if voltage == 4.4:
            self.CBOV = 0 | 4
        else:
            return False
        return True

    def set_lock(self, enable: bool) -> bool:
        if enable:
            self.LOCK = 0
        else:
            self.LOCK = 1
        return True

    def enable_ldrom(self, kb_size: int) -> bool:
        if kb_size < 0 or kb_size > 4:
            return False
        self.LDS = 7 - kb_size
        self.CBS = 0
        return True

    def set_wdt(self, enable: bool, keep_active: bool = False) -> bool:
        if enable:
            self.WDTEN = 0b0 if keep_active else 0b0101
        else:
            self.WDTEN = 0b1111
        return True

    def get_config_status(self) -> str:
        ret_str = ""
        ret_str +=("----- Chip Configuration ----\n")
        raw_bytes = self.to_bytes()
        ret_str +=("Raw config bytes:\t")
        for i in range(len(raw_bytes)):
            ret_str +=("%02X " % raw_bytes[i])
        ret_str +=("\nMCU Boot select:\t%s\n" %
              ("APROM" if self.CBS == 1 else "LDROM"))
        ret_str +=("LDROM size:\t\t%d Bytes\n" % self.get_ldrom_size())
        ret_str +=("Security lock:\t\t%s\n" %
              ("UNLOCKED" if not self.is_locked() else "LOCKED"))
        ret_str +=("P2.0/Nrst reset:\t%s\n" %
              ("enabled" if self.RPD == 1 else "disabled"))
        ret_str +=("On-Chip Debugger:\t%s\n" %
              ("disabled" if self.OCDEN == 1 else "enabled"))
        ret_str +=("OCD halt PWM output:\t%s\n" % (
            "tri-state pins are used as PWM outputs" if self.OCDPWM == 1 else "PWM continues"))
        ret_str +=("Brown-out detect:\t%s\n" %
              ("enabled" if self.CBODEN == 1 else "disabled"))
        ret_str +=("Brown-out voltage:\t%.1fV\n" % self.get_brown_out_voltage())
        ret_str +=("Brown-out reset:\t%s\n" %
              ("enabled" if self.CBORST == 1 else "disabled"))
        ret_str +=("Brown-out inhibits IAP:\t%s\n" %
              ("enabled" if self.BOIAP == 1 else "disabled"))

        wdt_status = ""
        if self.WDTEN & 15:
            wdt_status = "WDT is Disabled. WDT can be used as a general purpose timer via software control."
        elif self.WDTEN & 5:
            wdt_status = "WDT is Enabled as a time-out reset timer and it STOPS running during Idle or Power-down mode."
        else:
            wdt_status = "WDT is Enabled as a time-out reset timer and it KEEPS running during Idle or Power-down mode"

        ret_str +=("WDT status:\t\t%s\n" % wdt_status)
        return ret_str

    def print_config(self):
        print(self.get_config_status())

    def __str__(self) -> str:
        return " ".join(["%02X" % b for b in self.to_bytes()])

    def to_json(self):
        return json.dumps({
            "lock": self.is_locked(),
            "boot_from_ldrom": self.is_ldrom_boot(),
            "ldrom_size": self.get_ldrom_size(),
            "OCD_enable": self.is_ocd_enabled(),
            "brownout_detect": self.is_brownout_detect(),
            "brownout_reset": self.is_brownout_reset(),
            "brownout_voltage": self.get_brown_out_voltage(),
            "brownout_inhibits_IAP": self.is_brownout_inhibits_IAP(),
            "WDT_enable": self.is_wdt_enabled(),
            "WDT_keep_active": self.is_wdt_keep_active()
        }, indent=4)

    # Dumps config to file
    def to_json_file(self, filename) -> bool:
        obj = self.to_json()
        try:
            with open(filename, "w") as f:
                f.write(obj)
                return True
        except:
            print("Error writing config file")
            return False


def is_config_flags(thing):
    return isinstance(thing, ConfigFlags)


assert ctypes.sizeof(N8051ConfigFlags) == CFG_FLASH_LEN
