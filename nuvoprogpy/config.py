import json
import struct
import ctypes

N76E003_DEVID = 0x3650
APROM_ADDR = 0

CFG_FLASH_ADDR = 0x30000
CFG_FLASH_LEN = 5

LDROM_MAX_SIZE = 4 * 1024
LDROM_MAX_SIZE_KB = int(LDROM_MAX_SIZE / 1024)
FLASH_SIZE = 18 * 1024


class DeviceInfo:
    def __init__(self, device_id=0xFFFF, uid=0xFFFFFF, cid=0xFF, ucid=0xFFFFFFFF):
        self.device_id = device_id
        self.uid = uid
        self.cid = cid
        self.ucid = ucid

    def __str__(self):
        return "Device ID: 0x%04X\nCID: 0x%02X\nUID: 0x%08X\nUCID: 0x%08X" % (self.device_id, self.cid, self.uid, self.ucid)

    def is_supported(self):
        return self.device_id == N76E003_DEVID


def float_index_to_bit(bit: float) -> int:
    # get the byte
    bytenum = int(bit)
    # get the bit
    bitshift = int((bit - bytenum) * 10)
    if bitshift > 7:
        bytenum += 1
        bitshift = bitshift - 8
    return (bytenum, bitshift)


# Configflags bitfield structure:
class ConfigFlags(ctypes.LittleEndianStructure):
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
        # 11 = 2.2V
        # 10 = 2.7V
        # 01 = 3.7V
        # 00 = 4.4V
        ("CBOV", ctypes.c_uint8, 2),           # 2:5-4
        ("unk2_6", ctypes.c_uint8, 1),       # 2:6
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
        # print the type of bytes
        if cfg_bytes is None or len(cfg_bytes) != ctypes.sizeof(self):
            # initialize to all 0xFF
            struct.pack_into("B" * ctypes.sizeof(self), self,
                             0, *([0xFF] * ctypes.sizeof(self)))
        else:
            # initialize to the given bytes
            struct.pack_into("B" * ctypes.sizeof(self), self, 0, *cfg_bytes)

    def get_bit_value_n(self, bytenum: int, bit: int) -> int:
        # get the byte
        if bytenum > 4 or bit > 7:
            raise ValueError("Invalid bit index")
        byte = self.to_bytes()[bytenum]
        return (byte >> bit) & 0x1

    # key is in format of [0-4].[0-7]
    def get_bit_value(self, bit: float) -> int:
        bytenum, bitnum = float_index_to_bit(bit)
        return self.get_bit_value_n(bytenum, bitnum)

    def set_bit_value_n(self, bytenum: int, bit: int, value: bool):
        if bytenum > 4 or bit > 7:
            raise ValueError("Invalid bit index")
        # get the byte
        value = 1 if value else 0
        byte = self.to_bytes()[bytenum]
        # set the bit
        byte = (byte & ~(1 << bit)) | (value << bit)
        # set the byte
        struct.pack_into("B", self, bytenum, byte)

    def set_bit_value(self, bit: float, value: bool):
        bytenum, bitnum = float_index_to_bit(bit)
        self.set_bit_value_n(bytenum, bitnum, value)

    def __getitem__(self, key):
        # if key is int...
        if isinstance(key, int):
            return self.to_bytes()[int(key)]
        # if str is a int
        elif isinstance(key, str) and key.isdigit():
            return self.to_bytes()[int(key)]
        return getattr(self, key)

    # Set item
    def __setitem__(self, key, value):
        # if key is int...
        if isinstance(key, int):
            struct.pack_into("B", self, key, value)
        else:
            setattr(self, key, value)

    def to_bytes(self) -> bytes:
        return bytes(struct.unpack_from("B" * ctypes.sizeof(self), self))

    # get the size of the LDROM in bytes
    def get_ldrom_size(self) -> int:
        return int(self.get_ldrom_size_kb() * 1024)

    def get_ldrom_size_kb(self) -> int:
        return min((7 - (self.LDS & 0x7)), LDROM_MAX_SIZE_KB)

    # get the size of the APROM in bytes
    def get_aprom_size(self):
        return FLASH_SIZE - self.get_ldrom_size()

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
        if size_kb < 0 or size_kb > LDROM_MAX_SIZE_KB:
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
        if self.CBOV == 1:
            return 3.7
        elif self.CBOV == 2:
            return 2.7
        elif self.CBOV == 3:
            return 2.2
        # else 0
        return 4.4

    def set_brownout_voltage(self, voltage: float) -> bool:
        if voltage == 2.2:
            self.CBOV = 3
        elif voltage == 2.7:
            self.CBOV = 2
        elif voltage == 3.7:
            self.CBOV = 1
        if voltage == 4.4:
            self.CBOV = 0
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

    def print_config(self):
        print("----- Chip Configuration ----")
        raw_bytes = self.to_bytes()
        print("Raw config bytes:\t", end="")
        for i in range(len(raw_bytes)):
            print("%02X " % raw_bytes[i], end="")
        print("\nMCU Boot select:\t%s" %
              ("APROM" if self.CBS == 1 else "LDROM"))
        print("LDROM size:\t\t%d Bytes" % self.get_ldrom_size())
        print("APROM size:\t\t%d Bytes" % self.get_aprom_size())
        print("Security lock:\t\t%s" %
              ("UNLOCKED" if not self.is_locked() else "LOCKED"))
        print("P2.0/Nrst reset:\t%s" %
              ("enabled" if self.RPD == 1 else "disabled"))
        print("On-Chip Debugger:\t%s" %
              ("disabled" if self.OCDEN == 1 else "enabled"))
        print("OCD halt PWM output:\t%s" % (
            "tri-state pins are used as PWM outputs" if self.OCDPWM == 1 else "PWM continues"))
        print("Brown-out detect:\t%s" %
              ("enabled" if self.CBODEN == 1 else "disabled"))
        print("Brown-out voltage:\t%.1fV" % self.get_brown_out_voltage())
        print("Brown-out reset:\t%s" %
              ("enabled" if self.CBORST == 1 else "disabled"))
        print("Brown-out inhibits IAP:\t%s" %
              ("enabled" if self.BOIAP == 1 else "disabled"))

        wdt_status = ""
        if self.WDTEN == 15:
            wdt_status = "WDT is Disabled. WDT can be used as a general purpose timer via software control."
        elif self.WDTEN == 5:
            wdt_status = "WDT is Enabled as a time-out reset timer and it STOPS running during Idle or Power-down mode."
        else:
            wdt_status = "WDT is Enabled as a time-out reset timer and it KEEPS running during Idle or Power-down mode"

        print("WDT status:\t\t%s" % wdt_status)

    def __str__(self) -> str:
        return " ".join(["%02X" % b for b in self.to_bytes()])

    def from_json(json):
        # check that key exists
        config = ConfigFlags()
        # check if boolean
        if 'lock' in json and type(json['lock']) == bool:
            config.set_lock(json['lock'])
        if 'boot_from_ldrom' in json and type(json['boot_from_ldrom']) == bool:
            config.set_ldrom_boot(json['boot_from_ldrom'])
        if 'ldrom_size' in json and json['ldrom_size'] >= 0 and json['ldrom_size'] <= 4:
            config.set_ldrom_size_kb(json['ldrom_size'])
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

    def from_json_file(filename):
        try:
            with open(filename, "r") as f:
                confinfo = json.load(f)
                return ConfigFlags.from_json(confinfo)
        except:
            print("Error reading config file")
            return None

    def to_json(self):
        return json.dumps({
            "lock": self.is_locked(),
            "boot_from_ldrom": self.is_ldrom_boot(),
            "ldrom_size": self.get_ldrom_size_kb(),
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


assert ctypes.sizeof(ConfigFlags) == CFG_FLASH_LEN

# class DeviceInfo:
