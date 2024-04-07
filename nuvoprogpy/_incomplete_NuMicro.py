# Incomplete, not hooked up attempt at adding NuMicro ARM support
# If you are interested in finishing this, leave an issue and I can give further guidance.
# Look at the following repos for information:
# * ICP Protocol:
# The ICP protocol for NuMicro ARM chips is different from the 8051 ICP protocol, and I have not implemented it.
# Someone appears to have reverse-engineered the ICP protocol for these chips here
# This could easily be adapted to the nuvo51icp library:
# https://github.com/elfmimi/NuMaker_UART_ICPLib_Samples/blob/823060741e3dc4c7076ebf7999ccc8dfd4c7b265/ISP_UART_ICP_Bridge/SampleCode/ISP/ISP_UART_ICP_Bridge/ICPLib.c

# Information on chip part numbers can be found here: 
# https://github.com/OpenNuvoton/NuTool-PinConfigure/blob/4cdc5594954f10e953555f775bfb0a6afd997247/src/PartNumID.cpp#L1
# https://github.com/OpenNuvoton/ISPTool/blob/7a28ad98c98b54972d2c9871ba58d8fa01082610/NuvoISP/DataBase/PartNumID.cpp#L929
# https://github.com/OpenNuvoton/ISPTool/blob/7a28ad98c98b54972d2c9871ba58d8fa01082610/NuvoISP/DataBase/NuDataBase.cpp#L292

# this has information on the flash characteristics of all these chips:
# https://github.com/OpenNuvoton/ISPTool/blob/7a28ad98c98b54972d2c9871ba58d8fa01082610/NuvoISP/DataBase/FlashInfo.cpp
# https://github.com/OpenNuvoton/ISPTool_Cross_Platform/blob/master/ISP_Tool_SampleCode/FlashInfo.py

# this has information on all the configuration flag characteristics of these chips:
# https://github.com/OpenNuvoton/OpenOCD-Nuvoton/blob/master/src/flash/nor/numicro.c
# It is also recommended to look at the technical reference manuals for these chips to get a better understanding of what these bits do.
# (some chips have all this stuff located in a singular datasheet document, but most have it in a seperate TRM document)
# You can find these on the Nuvoton website.
# Look for "Config0", "Config1", "Config2", etc. to find what each of these bits mean for these chips.

# additional useful info:
# https://github.com/OpenNuvoton/NuLink2_ICP_Library
# https://github.com/OpenNuvoton/ISPTool_Cross_Platform

import ctypes
from ctypes import c_uint32, Structure
from config import ConfigFlags
from PartNumID import lookup_name_and_type, ChipType


NUMICRO_CONFIG_TYPE_NO_FLASH = [ChipType.M2351, ChipType.M2354ES, ChipType.M2354]
#        if chip_type == PROJ_NUC123AN or chip_type == PROJ_NUC123AE or chip_type == PROJ_NUC1311 or chip_type == PROJ_M0518:
NUMICRO_CONFIG_TYPE_OPTIONAL_FIXED_DATA_FLASH = [ChipType.NUC123AN, ChipType.NUC123AE, ChipType.NUC1311, ChipType.M0518]

            
NUMICRO_CONFIG_TYPE_FLASH_TYPE_200 = [ChipType.NUC400AE, ChipType.M451HD, ChipType.M471, ChipType.M0564, ChipType.NUC1262, ChipType.NUC1263, ChipType.M031_512K, ChipType.M031_256K]

NUMICRO_CONFIG_TYPE_FLASH_TYPE_300 = [ChipType.M480, ChipType.M480LD, ChipType.M460HD, ChipType.M460LD]


class FlashInfoNuMicro(FlashInfo):
    def __init__(self, AP_Size:int, DataFlash_Size:int, RAM_size:int, DF_Address:int, LDROM_size:int, DID:int):
        self._memory_size = AP_Size
        self._DataFlash_Size = DataFlash_Size
        self._DF_Address = DF_Address
        self._LDROM_size = LDROM_size
        self._RAM_size = RAM_size
        self._DID = DID
        _, type = lookup_name_and_type(DID)
        self._chip_type = type  

    @property
    def has_optional_fixed_data_flash(self):
        return self._chip_type in NUMICRO_CONFIG_TYPE_OPTIONAL_FIXED_DATA_FLASH

    @property
    def max_memory_size(self):
        if self.has_optional_fixed_data_flash:
            return self._memory_size + self._DataFlash_Size
        return self._memory_size
    
    @property
    def static_ldrom_size(self):
        return self._LDROM_size

    @property
    def maximum_ldrom_size(self):
        return self._LDROM_size

    def _has_shared_dataflash(self, config):
        utype = self.flash_type & 0xFF 
        shared_dataflash = True if (utype == 0) else False
        if self.has_optional_fixed_data_flash:
            if config.DFVSEN and config.DFEN:
                shared_dataflash = False
            else:
                shared_dataflash = True
        return shared_dataflash
    
    # TODO: parse this out
    def _get_dynamic_info(self, config):
        memory_size = self.max_memory_size
        shared_dataflash = self._has_shared_dataflash(config)
        if self.has_optional_fixed_data_flash and self._has_shared_dataflash(config):
            memory_size -= self._DataFlash_Size
        if shared_dataflash:
            if config.DFEN:
                page_size = ((self.flash_type & 0x0000FF00) >>  8) + 9
                addr = config.DFBADR
                addr &= ~((1 << page_size) - 1)
                aprom_size = addr if (memory_size > addr) else memory_size
                nvm_size = memory_size - aprom_size
            else:
                aprom_size = memory_size
                nvm_size = 0
            nvm_addr = aprom_size
        else:
            aprom_size = memory_size
            nvm_size = 0x1000
            nvm_addr = 0x1F000
        return aprom_size, nvm_size, nvm_addr

    def get_ldrom_size(self, config):
        return self._LDROM_size
    
    def get_aprom_size(self, config):
        return self._get_dynamic_info(config)[0]

    def get_dataflash_size(self, config):
        return self._get_dynamic_info(config)[1]
    
    def get_dataflash_addr(self, config):
        return self._get_dynamic_info(config)[2]

    @property
    def ram_size(self):
        return self._RAM_size
    
    @property
    def did(self):
        return self._DID
    
    @property
    def flash_type(self):
        flash_type = 0
        if self._chip_type in NUMICRO_CONFIG_TYPE_NO_FLASH:
            return 0
        elif self._chip_type in NUMICRO_CONFIG_TYPE_OPTIONAL_FIXED_DATA_FLASH:
            flash_type = 2
        else:
            flash_type = 1 if self._DataFlash_Size != 0 else 0
        
        if self._chip_type in NUMICRO_CONFIG_TYPE_FLASH_TYPE_200:
            flash_type |= 0x200
        elif self._chip_type in NUMICRO_CONFIG_TYPE_FLASH_TYPE_300:
            flash_type |= 0x300
        return flash_type

    @property
    def max_dataflash_size(self):
        return self._DataFlash_Size
    
    @property
    def dataflash_addr(self):
        return self._DF_Address

    @property
    def page_size(self):
        return 1 << (((self.flash_type & 0x0000FF00) >>  8) + 9)

    @property
    def has_configurable_size_ldrom(self):
        return False
    
    #TODO: Do these even exist on NuMicro chips?
    @property
    def sprom_addr(self):
        return 0

    @property
    def sprom_len(self):
        return 0




# M029G/M030G/M031G Series masks:
# a 1 in the mask means the bit is used
DEFAULT_ARM_BYTES = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF

MG29_30_31_MASK_CONFIG0 = 0x800017DB
MG29_30_31_MASK_CONFIG1 = 0X000FFFFF
MG29_30_31_MASK_CONFIG2 = 0X000000FF
MG29_30_31_MASK_CONFIG3 = 0X00000000

# concatenate them all together
MG29_30_31_MASK = [MG29_30_31_MASK_CONFIG0, MG29_30_31_MASK_CONFIG1, MG29_30_31_MASK_CONFIG2, MG29_30_31_MASK_CONFIG3]


class NuMicroArmConfigFlags(ctypes.LittleEndianStructure, ConfigFlags):
    _fields_ = [
        # config word 0
        # Data Flash Enable Bit
        # 0 = Data flash Enabled.
        # 1 = Data flash Disabled.
        ("DFEN", ctypes.c_uint32, 1),       # 0:0

        # Security lock bit
        # 1: unlocked, 0: locked
        ("LOCK", ctypes.c_uint32, 1),         # 0:1

        # DATA Flash Variable Size Enable Bit
        # 0 = Data flash size is variable and it base address is based on DFBADR (Config1).
        # 1 = Data flash size is fixed as 4 Kbytes.
        ("DFVSEN", ctypes.c_uint32, 1),     # 0:2

        # Only on certain chips
        ("CWDTEN1_0", ctypes.c_uint32, 2),       # 0:4-3

        # Chip Boot Selection
        # When CBS[0] = 0, the LDROM base address is mapping to 0x100000 and APROM base
        # address is mapping to 0x0. User could access both APROM and LDROM without boot
        # switching. In other words, if IAP mode is supported, the code in LDROM and APROM can
        # be called by each other.
        # 00 = Boot from LDROM with IAP mode.
        # 01 = Boot from LDROM without IAP mode.
        # 10 = Boot from APROM with IAP mode.
        # 11 = Boot from APROM without IAP mode.
        # Note: BS (ISPCON[1]) is only used to control boot switching when IAP mode is disabled
        # and VECMAP (ISPSTA[20:9]) is only used to remap 0x0~0x1ff when IAP mode is enabled.        
        ("CBS", ctypes.c_uint32, 2),            # 0:7-6

        # RST Pin Width Selection
        # 0 = RST pin debounce width is 2us.
        # 1 = RST pin debounce width is 32us.
        ("RSTWSEL", ctypes.c_uint32, 1),        # 0:8
        # Chip Reset Time Extend
        # 0 = Extend reset time to 26.6ms if chip release from power-on reset/LVR/BOD/RST pin reset happened.
        # 1 = Extend reset time to 3.2ms if chip release from power-on reset/LVR/BOD/RST pin reset happened.
        ("RSTEXT", ctypes.c_uint32, 1),         # 0:9
        # I/O Initial State Selection
        # 0 = All GPIO set as Quasi-bidirectional mode after chip powered on or active from reset pin.
        # 1 = All GPIO set as input mode after powered on or active from reset pin.
        ("CIOINI", ctypes.c_uint32, 1),         # 0:10
        # Reserved
        ("unk0_11", ctypes.c_uint32, 1),        # 0:11
        # ICE Lock Bit
        # This bit is only used to disable ICE function. User may use it with LOCK (CONFIG0[1]) bit to increase
        # security level.
        # 0 = ICE function Disabled.
        # 1 = ICE function Enabled.
        ("ICELOCK", ctypes.c_uint32, 1),        # 0:12
        # Reserved
        ("unk0_13", ctypes.c_uint32, 7),        # 0:19-13

        # Brown-out Reset Enable Bit
        # 0 = Brown-out reset Enabled after powered on.
        # 1 = Brown-out reset Disabled after powered on.
        ("CBORST", ctypes.c_uint32, 1),        # 0:20

        # Brown-out Voltage Selection
        # For NUC123xxxAN
        # 00 = Brown-out voltage is 2.2V.
        # 01 = Brown-out voltage is 2.7V.
        # 10 = Brown-out voltage is 3.8V.
        # 11 = Brown-out voltage is 4.5V.
        # For NUC123xxxAE
        # 00 = Brown-out voltage is 2.2V.
        # 01 = Brown-out voltage is 2.7V.
        # 10 = Brown-out voltage is 3.7V.
        # 11 = Brown-out voltage is 4.4V.        
        ("CBOV", ctypes.c_uint32, 2),           # 0:22-21

        # Brown-out Detector Enable Bit
        # 0= Brown-out detect Enabled after powered on.
        # 1= Brown-out detect Disabled after powered on.
        ("CBODEN", ctypes.c_uint32, 1),         # 0:23

        # CPU Clock Source Selection After Reset
        # The value of CFOSC will be loaded to CLKSEL0.HCLK_S[2:0] in system register after any
        # reset occurs except CPU reset.
        # 000 = 4 ~ 24 MHz external high speed crystal oscillators (HXT).
        # 111 = 22.1184 MHz internal high speed RC oscillator (HIRC).
        # Others = Reserved
        ("CFOSC", ctypes.c_uint32, 3),          # 0:26-24

        # GPF Multi-function Selection
        # 0 = PF.0 & PF.1 pins are configured as GPIO function.
        # 1 = PF.0 & PF.1 pins are used as external 4~24MHz crystal oscillator pin.
        # Note1: For NUC123xxxANx, PF.0 and PF.1 multi-function is controlled by CGPFMFP
        # (Config0[27]) when power-up, user can change PF.0 and PF.1 multi-function by writing
        # GPF_MFP0 (GPF_MFP[1]) and GPF_MFP1 (GPF_MFP[0]).
        # Note2: For NUC123xxxAEx, PF.0 and PF.1 multi-function can only be controlled by
        # CGPFMFP (Config0[27]).
        ("CGPFMFP", ctypes.c_uint32, 1),        # 0:27
        ("unk0_28", ctypes.c_uint32, 2),        # 0:29-28

        # Watchdog Clock Power-down Enable Bit
        # 0 = Watchdog Timer clock kept enabled when chip enters Power-down.
        # 1 = Watchdog Timer clock is controlled by OSC10K_EN (PWRCON[3]) when chip enters
        # Power-down.
        # Note: This bit only works if CWDTEN is set to 0
        ("CWDTPDEN", ctypes.c_uint32, 1),       # 0:30

        # Watchdog Hardware Enable Bit

        # When chips don't have CWDTEN_1_0:
        # When watchdog timer hardware enable function is enabled, the watchdog enable bit WTE
        # (WTCR[7]) and watchdog reset enable bit WTRE (WTCR[1]) is set to 1 automatically after
        # power on. The clock source of watchdog timer is force at LIRC and LIRC can’t be disabled.
        # 0 = WDT hardware enable function is active. WDT clock is always on except chip enters
        #     Power- down mode. When chip enter Power-down mode, WDT clock is always on if
        #     CWDTPDEN is 0 or WDT clock is controlled by OSC10K_EN (PWRCON[3]) if
        #     CWDTPDEN is 1. Please refer to bit field description of CWDTPDEN.
        # 1 = WDT hardware enable function is inactive.

        # When other chips have CWDTEN_1_0:
        # CWDTEN[2:0] is CONFIG0[31][4][3],
        # 111 = WDT hardware enable function is inactive, WDT clock source only can be changed in this case.
        # Others = WDT hardware enable function is active. WDT clock is always on
        ("CWDTEN_2", ctypes.c_uint32, 1),         # 0:31

        # Config1
        # Data Flash Base Address (this Register Works Only When DFEN Set to 0)
        # If DFEN is set to 0, the Data Flash base address is defined by user. Since on-chip flash
        # erase unit is 512 bytes, it is mandatory to keep bit 8-0 as 0.
        ("DFBADR", ctypes.c_uint32, 20),        # 1:19-0
        ("unk1_20", ctypes.c_uint32, 12),       # 1:31-20

        # Config2
        # Advance Security Lock Control
        # 0x5A = Flash memory content is unlocked if LOCK (CONFIG0[1]) is set to 1.
        # Others = Flash memory content is locked.
        # Note: ALOCK will be programmed as 0x5A after executing ISP page erase or ISP/ICP whole chip erase
        ("ALOCK", ctypes.c_uint32, 8),          # 2:7-0
        ("unk2_8", ctypes.c_uint32, 24),        # 2:31-8

        # Config3
        ("unk3_0", ctypes.c_uint32, 32),        # 3:31-0
    ]

    # default constructor
    # takes in an optional 16-byte array
    def __init__(self, cfg_bytes: list = None):
        if cfg_bytes is None or len(cfg_bytes) != ctypes.sizeof(self):
            # initialize to all 0xFF
            DEFAULT = bytes(([0xFF] * 16))
            struct.pack_into("16B", self, 0, *DEFAULT)
        else:
            struct.pack_into("16B", self, 0, *cfg_bytes)

    def check_if_masked(self, mask: list) -> bool:
        for i in range(ctypes.sizeof(self)):
            if (self.to_bytes()[i] & mask[i]) != mask[i]:
                return False
        return True

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
        return True

    def to_bytes(self) -> bytes:
        return bytes(struct.unpack_from("B" * ctypes.sizeof(self), self))
    
    def to_words(self) -> list[int]:
        # unpack from
        return list(struct.unpack("IIII", self.to_bytes()))


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

