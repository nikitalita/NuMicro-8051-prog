import struct
import ctypes

N76E003_DEVID = 0x3650
APROM_ADDR = 0

CFG_FLASH_ADDR = 0x30000
CFG_FLASH_LEN = 5

LDROM_MAX_SIZE = 4 * 1024
FLASH_SIZE = 18 * 1024


# Configflags bitfield structure:
class ConfigFlags(ctypes.LittleEndianStructure):
    _fields_ = [
        # config byte 0
        ("unk0_0", ctypes.c_uint8, 1),  # 0:0
        (
            "LOCK",
            ctypes.c_uint8,
            1,
        ),  # 0:1   | lock                            -- 1: unlocked, 0: locked
        (
            "RPD",
            ctypes.c_uint8,
            1,
        ),  # 0:2   | Reset pin enable                -- 1: reset function of P2.0/Nrst pin enabled, 0: disabled, P2.0/Nrst only functions as input-only pin P2.0
        ("unk0_3", ctypes.c_uint8, 1),  # 0:3
        (
            "OCDEN",
            ctypes.c_uint8,
            1,
        ),  # 0:4   | OCD enable                      -- 1: OCD Disabled, 0: OCD Enabled
        (
            "OCDPWM",
            ctypes.c_uint8,
            1,
        ),  # 0:5   | PWM output state under OCD halt -- 1: tri-state pins are used as PWM outputs, 0: PWM continues
        ("reserved0_6", ctypes.c_uint8, 1),  # 0:6
        (
            "CBS",
            ctypes.c_uint8,
            1,
        ),  # 0:7   | CONFIG boot select              -- 1: MCU will reboot from APROM after resets except software reset, 0: MCU will reboot from LDROM after resets except software reset
        # config1
        # * 1:3-0 | LDROM size select
        # 111 - No LDROM, APROM is 18k.
        # 110 = LDROM is 1K Bytes. APROM is 17K Bytes.
        # 101 = LDROM is 2K Bytes. APROM is 16K Bytes.
        # 100 = LDROM is 3K Bytes. APROM is 15K Bytes.
        # 0xx = LDROM is 4K Bytes. APROM is 14K Bytes
        ("LDS", ctypes.c_uint8, 3),
        ("unk1_3", ctypes.c_uint8, 5),  # 1:7-3
        # config2
        ("unk2_0", ctypes.c_uint8, 2),  # 2:1-0
        (
            "CBORST",
            ctypes.c_uint8,
            1,
        ),  # 2:2   | CONFIG brown-out reset enable   -- 1 = Brown-out reset Enabled, 0 = Brown-out reset Disabled.
        (
            "BOIAP",
            ctypes.c_uint8,
            1,
        ),  # 2:3   | Brown-out inhibiting IAP        -- 1 = IAP erasing or programming is inhibited if VDD is lower than VBOD, 0 = IAP erasing or programming is allowed under any workable VDD.
        (
            "CBOV",
            ctypes.c_uint8,
            2,
        ),  # 2:5-4 | CONFIG brown-out voltage select -- 11 = VBOD is 2.2V; 10 = VBOD is 2.7V; 01 = VBOD is 3.7V; 00 = VBOD is 4.4V.
        ("unk2_6", ctypes.c_uint8, 1),  # 2:6
        (
            "CBODEN",
            ctypes.c_uint8,
            1,
        ),  # 2:7   | CONFIG brown-out detect enable  -- 1 = Brown-out detection circuit on; 0 = Brown-out detection circuit off.
        # config3 - no flags
        ("unk3", ctypes.c_uint8),  # 3:7-0
        # config4
        ("unk4_0", ctypes.c_uint8, 4),  # 4:3-0
        # 4:4-7 | WDT enable
        #  1111 = WDT is Disabled. WDT can be used as a general purpose timer via software control
        #  0101 = WDT is Enabled as a time-out reset timer and it stops running during Idle or Power-down mode.
        #  Others = WDT is Enabled as a time-out reset timer and it keeps running during Idle or Power-down mode.
        ("WDTEN", ctypes.c_uint8, 4),
    ]

    # default constructor
    # takes in an optional 5-byte array
    def __init__(self, bytes: list = None):
        # print the type of bytes
        if bytes is None or len(bytes) != ctypes.sizeof(self):
            # initialize to all 0xFF
            struct.pack_into("B" * ctypes.sizeof(self), self, 0, *([0xFF] * ctypes.sizeof(self)))
        else:
            # initialize to the given bytes
            struct.pack_into("B" * ctypes.sizeof(self), self, 0, *bytes)

    def to_bytes(self) -> bytes:
        return bytes(struct.unpack_from("B" * ctypes.sizeof(self), self))

    def get_ldrom_size(self):
        return min((7 - (self.LDS & 0x7)) * 1024, LDROM_MAX_SIZE)

    def get_aprom_size(self):
        return FLASH_SIZE - self.get_ldrom_size()

    def get_brown_out_voltage(self):
        if self.CBOV == 1:
            return 3.7
        elif self.CBOV == 2:
            return 2.7
        elif self.CBOV == 3:
            return 2.2
        return 4.4

    def set_brownout_voltage(self, voltage: float) -> bool:
        if voltage == 4.4:
            self.CBOV = 0
        elif voltage == 2.2:
            self.CBOV = 3
        elif voltage == 2.7:
            self.CBOV = 2
        elif voltage == 3.7:
            self.CBOV = 1
        else:
            return False
        return True

    def is_locked(self) -> bool:
        return self.LOCK == 0

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

    def print_config(self):
        print("----- Chip Configuration ----")
        raw_bytes = self.to_bytes()
        print("Raw config bytes:\t", end="")
        for i in range(len(raw_bytes)):
            print("%02X " % raw_bytes[i], end="")
        print("\nMCU Boot select:\t%s" % ("APROM" if self.CBS == 1 else "LDROM"))
        print("LDROM size:\t\t%d Bytes" % self.get_ldrom_size())
        print("APROM size:\t\t%d Bytes" % self.get_aprom_size())
        print("Security lock:\t\t%s" % ("UNLOCKED" if not self.is_locked() else "LOCKED"))
        print("P2.0/Nrst reset:\t%s" % ("enabled" if self.RPD == 1 else "disabled"))
        print("On-Chip Debugger:\t%s" % ("disabled" if self.OCDEN == 1 else "enabled"))
        print("OCD halt PWM output:\t%s" % ("tri-state pins are used as PWM outputs" if self.OCDPWM == 1 else "PWM continues"))
        print("Brown-out detect:\t%s" % ("enabled" if self.CBODEN == 1 else "disabled"))
        print("Brown-out voltage:\t%fV" % self.get_brown_out_voltage())
        print("Brown-out reset:\t%s" % ("enabled" if self.CBORST == 1 else "disabled"))

        wdt_status = ""
        if self.WDTEN == 15:
            wdt_status = "WDT is Disabled. WDT can be used as a general purpose timer via software control."
        elif self.WDTEN == 5:
            wdt_status = "WDT is Enabled as a time-out reset timer and it STOPS running during Idle or Power-down mode."
        else:
            wdt_status = "WDT is Enabled as a time-out reset timer and it KEEPS running during Idle or Power-down mode"

        print("WDT status:\t\t%s" % wdt_status)


assert ctypes.sizeof(ConfigFlags) == CFG_FLASH_LEN

# class DeviceInfo:
