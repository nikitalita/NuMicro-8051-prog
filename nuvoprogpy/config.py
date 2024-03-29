import json
import struct
import ctypes

N76E003_DEVID = 0x3650
APROM_ADDR = 0

CFG_FLASH_ADDR = 0x30000
CFG_FLASH_LEN = 5

# N76E003 values only for now
LDROM_MAX_SIZE = 4 * 1024
FLASH_SIZE = 18 * 1024


supported_devices = [N76E003_DEVID]

devid_to_device = {
    N76E003_DEVID: "N76E003"
}
    
class DeviceInfo:
    def __init__(self, device_id=0xFFFF, pid=0x0000):
        self.device_id = device_id
        self.pid = pid

    @property
    def pid(self):
        return self._pid

    @pid.setter
    def pid(self, pid):
        if pid == self.device_id and pid != 0xffff:
            pid = 0
        self._pid = pid        
    
    @property
    def aprom_addr(self):
        return get_aprom_addr(self.device_id)

    @property
    def ldrom_max_size(self):
        return get_ldrom_max_size(self.device_id)

    @property
    def flash_size(self):
        return get_flash_size(self.device_id)
    
    @property
    def config_addr(self):
        return get_config_addr(self.device_id)
    
    @property
    def config_len(self):
        return get_config_len(self.device_id)

    @property
    def is_unsupported(self):
        return not self.device_id in supported_devices

    def __str__(self):
        if self.pid > 0:
            #concatenate the pid
            device_id = self.pid << 16 | self.device_id
        else:
            device_id = self.device_id
        ret = "Device ID: 0x{:04X} ({})\n".format(self.device_id, devid_to_device[device_id])
        ret += "Flash size: %d kB\n" % (self.flash_size // 1024)
        return ret

    @property
    def is_supported(self):
        return self.device_id in supported_devices


def float_index_to_bit(bit: float) -> int:
    # get the byte
    bytenum = int(bit)
    # get the bit
    bitshift = int((bit - bytenum) * 10)
    if bitshift > 7:
        bytenum += 1
        bitshift = bitshift - 8
    return (bytenum, bitshift)

def get_aprom_addr(device_id: int) -> int:
    # N76E003 only for now
    return APROM_ADDR

def get_config_addr(device_id: int) -> int:
    # N76E003 only for now
    return CFG_FLASH_ADDR

def get_config_len(device_id: int) -> int:
    # N76E003 only for now
    return CFG_FLASH_LEN

def get_flash_size(device_id: int) -> int:
    # N76E003 only for now
    return FLASH_SIZE

def get_ldrom_max_size(device_id: int) -> int:
    # N76E003 only for now
    return LDROM_MAX_SIZE

def get_ldrom_max_size_kb(device_id: int) -> int:
    return int(get_ldrom_max_size(device_id) // 1024)

# Configflags bitfield structure:
# class N8051ConfigFlags:
#     pass
class ConfigFlags:
    def __init__(self, device_id = N76E003_DEVID, cfg_bytes: list = None):
        raise NotImplementedError("Don't call the constructor! Call `from_bytes` or `from_json` instead!")
    
    def to_bytes(self) -> bytes:
        raise NotImplementedError("Not implemented!")

    # get the size of the LDROM in bytes
    def get_ldrom_size(self) -> int:
        raise NotImplementedError("Not implemented!")

    def get_ldrom_size_kb(self) -> int:
        raise NotImplementedError("Not implemented!")

    # get the size of the APROM in bytes
    def get_aprom_size(self):
        raise NotImplementedError("Not implemented!")

    def get_aprom_size_kb(self):
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
        return not self.device_id in supported_devices
        
    @staticmethod
    def from_bytes(config_bytes, device_id):
        if device_id in supported_devices:
            return N8051ConfigFlags(config_bytes, device_id)
        return UnsupportedConfigFlags(config_bytes, device_id)

    @staticmethod
    def from_json(json, device_id=None):
        if device_id is None:
            device_id = N76E003_DEVID
        # unsupported devices
        if 'device_id' in json and json['device_id'] != device_id:
            device_id = json['device_id']
        if 'config_bytes' in json and type(json['config_bytes']) == list and len(json['config_bytes']) == 5:
            config = UnsupportedConfigFlags(json['config_bytes'], device_id)
            return config
        config = N8051ConfigFlags(device_id=device_id)
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
    def from_json_file(filename, device_id=None):
        try:
            with open(filename, "r") as f:
                confinfo = json.load(f)
                return ConfigFlags.from_json(confinfo, device_id)
        except:
            print("Error reading config file")
            return None

class UnsupportedConfigFlags(ConfigFlags):

    # default constructor
    # takes in an optional 5-byte array
    def __init__(self, cfg_bytes: list = None, device_id = N76E003_DEVID):
        # print the type of bytes
        self.device_id = device_id
        self.cfg_bytes = cfg_bytes

    # def get_bit_value_n(self, bytenum: int, bit: int) -> int:
    #     # get the byte
    #     if bytenum > 4 or bit > 7:
    #         raise ValueError("Invalid bit index")
    #     byte = self.to_bytes()[bytenum]
    #     return (byte >> bit) & 0x1

    # # key is in format of [0-4].[0-7]
    # def get_bit_value(self, bit: float) -> int:
    #     bytenum, bitnum = float_index_to_bit(bit)
    #     return self.get_bit_value_n(bytenum, bitnum)

    # def set_bit_value_n(self, bytenum: int, bit: int, value: bool):
    #     if bytenum > 4 or bit > 7:
    #         raise ValueError("Invalid bit index")
    #     # get the byte
    #     value = 1 if value else 0
    #     byte = self.to_bytes()[bytenum]
    #     # set the bit
    #     byte = (byte & ~(1 << bit)) | (value << bit)
    #     # set the byte
    #     struct.pack_into("B", self, bytenum, byte)

    # def set_bit_value(self, bit: float, value: bool):
    #     bytenum, bitnum = float_index_to_bit(bit)
    #     self.set_bit_value_n(bytenum, bitnum, value)

    # def __getitem__(self, key):
    #     # if key is int...
    #     if isinstance(key, int):
    #         return self.to_bytes()[int(key)]
    #     # if str is a int
    #     elif isinstance(key, str) and key.isdigit():
    #         return self.to_bytes()[int(key)]
    #     return getattr(self, key)

    # # Set item
    # def __setitem__(self, key, value):
    #     # if key is int...
    #     if isinstance(key, int):
    #         struct.pack_into("B", self, key, value)
    #     else:
    #         setattr(self, key, value)

    def to_bytes(self) -> bytes:
        return bytes(self.cfg_bytes)

    # get the size of the LDROM in bytes
    def get_ldrom_size(self) -> int:
        return 0

    def get_ldrom_size_kb(self) -> int:
        return 0

    # get the size of the APROM in bytes
    def get_aprom_size(self):
        return get_flash_size(self.device_id) - self.get_ldrom_size()

    def get_aprom_size_kb(self):
        return int(self.get_aprom_size() / 1024)

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
            "device_id": self.device_id,
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
    def __init__(self, cfg_bytes: list = None, device_id = N76E003_DEVID):
        # print the type of bytes
        self.device_id = device_id
        if not self.device_id in supported_devices:
            if cfg_bytes is None:
                cfg_bytes = [0xFF] * 16
            self.bytes = cfg_bytes
        else:
            self.bytes = None
            if cfg_bytes is None or len(cfg_bytes) != ctypes.sizeof(self):
                # initialize to all 0xFF
                struct.pack_into("B" * ctypes.sizeof(self), self,
                                0, *([0xFF] * ctypes.sizeof(self)))
            else:
                # initialize to the given bytes
                struct.pack_into("B" * ctypes.sizeof(self), self, 0, *cfg_bytes)

    # def get_bit_value_n(self, bytenum: int, bit: int) -> int:
    #     # get the byte
    #     if bytenum > 4 or bit > 7:
    #         raise ValueError("Invalid bit index")
    #     byte = self.to_bytes()[bytenum]
    #     return (byte >> bit) & 0x1

    # # key is in format of [0-4].[0-7]
    # def get_bit_value(self, bit: float) -> int:
    #     bytenum, bitnum = float_index_to_bit(bit)
    #     return self.get_bit_value_n(bytenum, bitnum)

    # def set_bit_value_n(self, bytenum: int, bit: int, value: bool):
    #     if bytenum > 4 or bit > 7:
    #         raise ValueError("Invalid bit index")
    #     # get the byte
    #     value = 1 if value else 0
    #     byte = self.to_bytes()[bytenum]
    #     # set the bit
    #     byte = (byte & ~(1 << bit)) | (value << bit)
    #     # set the byte
    #     struct.pack_into("B", self, bytenum, byte)

    # def set_bit_value(self, bit: float, value: bool):
    #     bytenum, bitnum = float_index_to_bit(bit)
    #     self.set_bit_value_n(bytenum, bitnum, value)

    # def __getitem__(self, key):
    #     # if key is int...
    #     if isinstance(key, int):
    #         return self.to_bytes()[int(key)]
    #     # if str is a int
    #     elif isinstance(key, str) and key.isdigit():
    #         return self.to_bytes()[int(key)]
    #     return getattr(self, key)

    # # Set item
    # def __setitem__(self, key, value):
    #     # if key is int...
    #     if isinstance(key, int):
    #         struct.pack_into("B", self, key, value)
    #     else:
    #         setattr(self, key, value)

    def to_bytes(self) -> bytes:
        return bytes(struct.unpack_from("B" * ctypes.sizeof(self), self))

    # get the size of the LDROM in bytes
    def get_ldrom_size(self) -> int:
        return int(self.get_ldrom_size_kb() * 1024)

    def get_ldrom_size_kb(self) -> int:
        return min((7 - (self.LDS & 0x7)), get_ldrom_max_size_kb(self.device_id))

    # get the size of the APROM in bytes
    def get_aprom_size(self):
        return get_flash_size(self.device_id) - self.get_ldrom_size()

    def get_aprom_size_kb(self):
        return int(self.get_aprom_size() / 1024)

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
        size_kb = int(size / 1024)
        if size % 1024 != 0:
            size_kb += 1
        self.set_ldrom_size_kb(size_kb)
        return True

    # Set ldrom size in KB
    def set_ldrom_size_kb(self, size_kb: int):
        if size_kb < 0 or size_kb > get_ldrom_max_size_kb(self.device_id):
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

        if self.device_id not in supported_devices:
            return ret_str

        ret_str +=("\nMCU Boot select:\t%s\n" %
              ("APROM" if self.CBS == 1 else "LDROM"))
        ret_str +=("LDROM size:\t\t%d Bytes\n" % self.get_ldrom_size())
        ret_str +=("APROM size:\t\t%d Bytes\n" % self.get_aprom_size())
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
        if not (self.device_id in supported_devices):
            return json.dumps({
                "device_id": self.device_id,
                "config_bytes": self.to_bytes()
            }, indent=4)
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

# class DeviceInfo:
