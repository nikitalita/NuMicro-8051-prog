#!/usr/bin/env python3
import platform
import signal

if platform.system() != "Linux":
    raise NotImplementedError("%s is not supported yet" % platform.system())

import atexit
from enum import Enum
from io import BufferedReader
import time
import getopt
import sys
import os

try:
    from ..config import DeviceInfo, ConfigFlags
    from ..config import *
    from .lib.libnuvoicp import LibICP, LibPGM
    from .lib.libnuvoicp import *
except Exception as e:
    # Hack to allow running nuvoicpy.py directly from the command line
    if __name__ == "__main__":
        # check if config.py exists in the parent directory
        if not os.path.isfile(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "config.py")):
            raise e

    from lib.libnuvoicp import LibICP, LibPGM
    from lib.libnuvoicp import *

    sys.path.append(os.path.join(
        os.path.dirname(os.path.realpath(__file__)), ".."))
    from config import DeviceInfo, ConfigFlags
    from config import *


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


class ICPInitException(Exception):
    pass


class PGMInitException(Exception):
    pass


class NoDeviceException(Exception):
    pass


class UnsupportedDeviceException(Exception):
    pass


# class HostPGM:
#   def __init__(self, host_type: str = "Raspberry Pi"):
#     self.host_type = ICPHostType.from_str(host_type)
# 		self.initialized = False

"""
NuvoICP class
Raises:
        PGMInitException: _description_
        NoDeviceException: _description_
        UnsupportedDeviceException: _description_
        Exception: _description_

Returns:
        
"""


class NuvoICP:

    def __init__(self, silent=False, library: str = "gpiod", _enter_no_init=None, _deinit_reset_high=False):
        """
        NuvoICP constructor
        ------

        #### Keyword args:
            library: ["pigpio"|"gpiod"] (="gpiod"):
                The library to use for GPIO control
            silent: bool (=False):
                If True, do not print any progress messages
            _enter_no_init: _type_ (=None):
                If True, do not initialize the ICP module when entering a with statement
            _deinit_reset_high: _type_ (=True):
                If True, set the reset pin high when deinitializing the ICP module and do not release the pin
        """
        self.library = library
        self.icp = LibICP(library)
        self.pgm = LibPGM(library)
        self._enter_no_init = _enter_no_init
        self.deinit_reset_high = _deinit_reset_high
        self.initialized = False
        self.silent = silent

    def __enter__(self):
        """
        Called when using NuvoICP in a with statement, such as "with NuvoICP() as icp:"

        #### Returns:
            NuvoICP: The NuvoICP object
        """
        if self._enter_no_init:
            return self
        self.init(True, True, True)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.initialized:
            self.close()
        else:
            # pgm may still be initialized, this is reentrant
            self.pgm.deinit(self.deinit_reset_high)

    def print_vb(self, *args, **kwargs):
        """
        Print a message if print progress is enabled
        """
        if not self.silent:
            print(*args, **kwargs)

    def init_pgm(self):
        if not self.pgm.init():
            raise PGMInitException("Unable to initialize PGM module")

    @property
    def CMD_BIT_DELAY(self) -> int:
        """
        The delay between each bit sent to the device during `icp_send_cmd()` in microseconds

        #### Returns:
            int
        """
        return self.icp.get_cmd_bit_delay()

    @CMD_BIT_DELAY.setter
    def CMD_BIT_DELAY(self, delay_us):
        self.icp.set_cmd_bit_delay(delay_us)

    @property
    def READ_BIT_DELAY(self) -> int:
        """
        The delay between each bit read from the device during `icp_read_byte()` in microseconds

        #### Returns:
            int: The current READ_BIT_DELAY value
        """
        return self.icp.get_read_bit_delay()

    @READ_BIT_DELAY.setter
    def READ_BIT_DELAY(self, delay_us):
        self.icp.set_read_bit_delay(delay_us)

    @property
    def WRITE_BIT_DELAY(self) -> int:
        """
        The delay between each bit written to the device during `icp_write_byte()` in microseconds
        ------

        #### Returns:
            int: The current WRITE_BIT_DELAY value
        """
        return self.icp.get_write_bit_delay()

    @WRITE_BIT_DELAY.setter
    def WRITE_BIT_DELAY(self, delay_us):
        self.icp.set_write_bit_delay(delay_us)

    def retry(self) -> bool:
        """
        Attempt to retry entering ICP Programming mode
        ------

        This is mostly needed when the chip is configured to not have P2.0 as the reset pin
        It is often a crapshoot to get it into ICP Programming mode as it will not stay in a reset state when nRST is low and will reboot itself
        So, we have to keep trying at random intervals to try and catch it in a reset state

        #### Returns:
            bool:
                False if the device is not found, True otherwise
        """
        max_reentry = 5
        max_reinit = 2
        max_fullexit = 3
        reentry_tries = 0
        fullexit_tries = 0
        reinit_tries = 0
        realtries = reentry_tries
        self.print_vb("No device found, attempting reentry...")
        try:
            while reinit_tries < max_reinit:
                while fullexit_tries < max_fullexit:
                    while reentry_tries < max_reentry:
                        self.print_vb("Reentry attempt " + str(realtries) + " of " +
                                      str(max_reentry * max_reinit * max_fullexit - 1) + "...")
                        self.icp.reentry(
                            8000 + (reentry_tries * 1000), 1000, 100 + (reentry_tries * 100))
                        reentry_tries += 1
                        realtries += 1
                        if self.icp.read_device_id() != 0:
                            self.print_vb("Connected!")
                            return True
                    reentry_tries = 0
                    self.print_vb("Attempting full exit and entry...")
                    self.icp.exit()
                    time.sleep(0.5)
                    self.icp.entry()
                    if self.icp.read_device_id() != 0:
                        self.print_vb("Connected!")
                        return True
                    fullexit_tries += 1
                fullexit_tries = 0
                self.print_vb("Attempting reinitialization...")
                self.icp.deinit()
                time.sleep(0.5)
                self.icp.init()
                if self.icp.read_device_id() != 0:
                    self.print_vb("Connected!")
                    return True
                reinit_tries += 1
        except KeyboardInterrupt:
            eprint("Retry aborted!")
        except Exception as e:
            eprint("Retry error!")
            raise e
        eprint("Retry failed!")
        return False

    def init(self, do_reset_seq=True, check_device=True, retry=True):
        """
        Initialize the ICP interface
        ------

        Must be called before any other ICP functions

        #### Keyword args:
            do_reset_seq: bool (=True):
                Whether to perform the reset sequence before entering ICP mode

            check_device: bool (=True):
                Whether to check that a device is connected/supported before continuing

            retry: bool (=True):
                Whether to retry if no device is found

        #### Raises:
            PGMInitException
                If the PGM (GPIO pin interface) module fails to initialize
            **NoDeviceException**
                If no device is detected
            **UnsupportedDeviceException**
                If the detected device is not supported
        """
        if not self.icp.init(do_reset_seq):
            raise PGMInitException("ERROR: Could not initialize ICP.")
        if check_device:
            devid = self.icp.read_device_id()
            cid = self.icp.read_cid()
            if devid == 0:
                if not retry or not self.retry():
                    self.icp.deinit()
                    raise NoDeviceException(
                        "ERROR: No device detected, please check your connections!")
                devid = self.icp.read_device_id()
                cid = self.icp.read_cid()
            if devid == 0xFFFF and cid == 0xFF:
                eprint("WARNING: Read Device ID of 0xFFFF and cid of 0xFF, device may be locked!")
                eprint("Proceeding anyway...")
            elif devid != N76E003_DEVID:
                self.icp.deinit()
                raise UnsupportedDeviceException(
                    "ERROR: Non-N76E003 device detected (devid: %d)\nThis programmer only supports N76E003 (devid: %d)!" % (devid, N76E003_DEVID))
        self.initialized = True

    def close(self):
        """
        Deinitialize the ICP interface
        ------

        """
        if self.initialized:
            self.initialized = False
            self.icp.exit()
            self.pgm.deinit(self.deinit_reset_high)
        else:
            self.pgm.deinit(self.deinit_reset_high)  # just in case

    def reinit(self, do_reset_seq=True, check_device=True):
        """
        Reinitialize the ICP interface
        ------

        #### Keyword args:
            do_reset_seq: bool (=True):
                Whether to perform the reset sequence before entering ICP mode
            check_device: bool (=True):
                Whether to check that a device is connected/supported before continuing
        """
        self.close()
        time.sleep(0.2)
        self.init(do_reset_seq, check_device, True)

    def _fail_if_not_init(self):
        if not self.initialized:
            raise ICPInitException("ICP is not initialized")

    def reenter_icp(self):
        self._fail_if_not_init()
        self.icp.exit()
        self.icp.entry()

    def get_device_id(self) -> int:
        """
        Get the device ID
        ------

        #### Returns:
            int: 
                The device ID
        """
        self._fail_if_not_init()
        return self.icp.read_device_id()

    def get_cid(self):
        self._fail_if_not_init()
        return self.icp.read_cid()

    def read_config(self):
        self._fail_if_not_init()
        return ConfigFlags(self.icp.read_flash(CFG_FLASH_ADDR, CFG_FLASH_LEN))

    def mass_erase(self):
        self._fail_if_not_init()
        self.print_vb("Erasing flash...")
        cid = self.icp.read_cid()
        self.icp.mass_erase()
        if cid == 0xFF or cid == 0x00:
            self.reenter_icp()
        return True

    def get_device_info(self):
        self._fail_if_not_init()
        devinfo = DeviceInfo()
        devinfo.device_id = self.icp.read_device_id()
        devinfo.uid = self.icp.read_uid()
        devinfo.cid = self.icp.read_cid()
        devinfo.ucid = self.icp.read_ucid()
        return devinfo

    def page_erase(self, addr):
        self._fail_if_not_init()
        self.icp.page_erase(addr)
        return True

    def read_flash(self, addr, len) -> bytes:
        self._fail_if_not_init()
        return self.icp.read_flash(addr, len)

    def write_flash(self, addr, data) -> bool:
        self._fail_if_not_init()
        self.icp.write_flash(addr, data)
        return True

    def dump_flash(self) -> bytes:
        self._fail_if_not_init()
        return self.icp.read_flash(APROM_ADDR, FLASH_SIZE)

    def dump_flash_to_file(self, read_file) -> bool:
        self._fail_if_not_init()
        try:
            f = open(read_file, "wb")
        except OSError as e:
            eprint("Dump to %s failed: %s" % (read_file, e))
            raise e
        self.print_vb("Reading flash...")
        f.write(self.icp.read_flash(APROM_ADDR, FLASH_SIZE))
        f.close()
        self.print_vb("Done.")
        return True

    def write_config(self, config: ConfigFlags, _skip_erase=False):
        """
        Programs the config bytes.
        ------

        #### Keyword args:
            config: ConfigFlags:
                The configuration flags to program
            _skip_erase: bool (=False):
                If True, the config block will not be erased before writing.

                We avoid erasing the configuration bytes after a mass_erase() to prevent flash wear.
                You don't want to use this if you're using write_config() by itself, as the config will
                fail to be written if the config isn't the default (FF FF FF FF FF).
        """
        self._fail_if_not_init()
        if not _skip_erase:
            self.icp.page_erase(CFG_FLASH_ADDR)
        self.icp.write_flash(CFG_FLASH_ADDR, config.to_bytes())

    def program_ldrom(self, ldrom_data: bytes, write_config: ConfigFlags = None, _skip_config_erase=False) -> ConfigFlags:
        """
        Programs the LDROM with the given data, and programs the config block with the given configuration flags.

        #### Keyword args:
            ldrom_data: bytes:
                The data to program to the LDROM
            write_config: ConfigFlags (=None):
                The configuration flags to program to the config block.
                If None, the default configuration for booting the ldrom of its size will be written.
            _skip_config_erase: bool (=False):
                If True, the config block will not be erased before writing. For more info, see write_config().

        #### Returns:
            ConfigFlags:
                The configuration flags that were written to the config block during this operation.
        """
        self._fail_if_not_init()
        self.print_vb("Programming LDROM (%d KB)..." % int(len(ldrom_data) / 1024))
        if not write_config:
            write_config = ConfigFlags()
            write_config.set_ldrom_boot(True)
            write_config.set_ldrom_size(len(ldrom_data))
        self.write_config(write_config, _skip_config_erase)
        self.icp.write_flash(FLASH_SIZE - len(ldrom_data), ldrom_data)
        self.print_vb("LDROM programmed.")
        return write_config

    def verify_flash(self, data: bytes, report_unmatched_bytes=False) -> bool:
        """


        #### Args:
            data (bytes): 
                bytes to verify
            report_unmatched_bytes (bool) (=False)):
                If True, the number of unmatched bytes will be printed to stderr

        #### Returns:
            bool:
                True if the data matches the flash, False otherwise
        """
        self._fail_if_not_init()
        read_data = self.icp.read_flash(APROM_ADDR, FLASH_SIZE)
        if read_data == None:
            return False
        if len(read_data) != len(data):
            return False
        result = True
        byte_errors = 0
        for i in range(len(data)):
            if read_data[i] != data[i]:
                if not report_unmatched_bytes:
                    return False
                result = False
                byte_errors += 1
        if not result:
            eprint("Verification failed. %d byte errors." % byte_errors)
        return result

    def program_aprom(self, data: bytes) -> bool:
        self._fail_if_not_init()
        self.print_vb("Programming APROM...")
        self.icp.write_flash(APROM_ADDR, data)
        self.print_vb("APROM programmed.")
        return True

    @staticmethod
    def check_ldrom_size(size) -> int:
        if size > LDROM_MAX_SIZE:
            return -1
        return size if size % 1024 == 0 else size + (1024 - (size % 1024))

    @staticmethod
    def pad_ldrom(data: bytes) -> bytes:
        # pad to the next highest KB
        return data + bytes([0xFF] * (1024 - (len(data) % 1024)))

    def program_data(self, aprom_data, ldrom_data=bytes(), config: ConfigFlags = None, verify=True, ldrom_config_override=True, _erase=True) -> bool:
        self._fail_if_not_init()
        if len(ldrom_data) > 0:
            ldrom_size = len(ldrom_data)
            if not self.check_ldrom_size(ldrom_size):
                eprint("ERROR: LDROM size greater than max of 4KB. Not programming...")
                return False
            else:
                if len(ldrom_data) % 1024 != 0:
                    eprint("WARNING: LDROM is not a multiple of 1024 bytes. Padding with 0xFF.")
                    ldrom_data = self.pad_ldrom(ldrom_data)
                    ldrom_size = len(ldrom_data)
                if config:
                    if config.get_ldrom_size() != ldrom_size:
                        eprint("WARNING: LDROM size does not match config: %d KB vs %d KB" % (
                            ldrom_size / 1024, config.get_ldrom_size_kb()))
                        if ldrom_config_override:
                            eprint("Overriding LDROM size in config.")
                            config.set_ldrom_size(ldrom_size)
                        else:
                            if len(ldrom_data) < config.get_ldrom_size():
                                eprint("LDROM will be padded with 0xFF.")
                                ldrom_data = ldrom_data + \
                                    bytes(
                                        [0xFF] * (config.get_ldrom_size() - len(ldrom_data)))
                            else:
                                eprint("LDROM will be truncated.")
                                ldrom_data = ldrom_data[: config.get_ldrom_size(
                                )]
                    if config.is_ldrom_boot() != True:
                        eprint("WARNING: LDROM boot flag not set in config")
                        if ldrom_config_override:
                            eprint("Overriding LDROM boot in config.")
                            config.set_ldrom_boot(True)
                        else:
                            eprint("LDROM will not be bootable.")
                else:  # No config, set defaults
                    config = ConfigFlags()
                    config.set_ldrom_size(ldrom_size)
                    config.set_ldrom_boot(True)
        elif config == None:
            config = ConfigFlags()

        aprom_size = config.get_aprom_size()
        if aprom_size != len(aprom_data):
            eprint("WARNING: APROM file size does not match config: %d KB vs %d KB" % (
                len(aprom_data) / 1024, aprom_size / 1024))
            if aprom_size < len(aprom_data):
                eprint("APROM will be truncated.")
                aprom_data = aprom_data[:aprom_size]
            else:
                eprint("APROM will be padded with 0xFF.")
                # Pad with 0xFF
                aprom_data += bytes([0xFF] * (aprom_size - len(aprom_data)))

        if _erase:
            self.mass_erase()

        dev_id = self.get_device_id()
        if dev_id != N76E003_DEVID:
            # failed to reenter ICP mode
            err_str = "Failed to reenter ICP mode after mass erase."
            if not _erase:
                err_str = "Failed to find device."
            eprint(err_str)
            return False

        cid = self.get_cid()
        if cid == 0xFF or cid == 0x00:
            self.reenter_icp()
            cid = self.get_cid()
            if cid == 0xFF or cid == 0x00:
                eprint("Device locked or not found.")
                return False
        if len(ldrom_data) > 0:
            config = self.program_ldrom(ldrom_data, config, True)
            if not config:
                eprint("Could not write LDROM.")
                return False
        else:
            self.write_config(config, True)

        self.print_vb("Programming APROM (%d KB)..." % (aprom_size / 1024))
        self.icp.write_flash(APROM_ADDR, aprom_data)
        self.print_vb("APROM programmed.")
        if verify:
            combined_data = aprom_data + ldrom_data
            if not self.verify_flash(combined_data):
                self.print_vb("Verification failed.")
                return False
            self.print_vb("ROM data verified.")
            # check that the config was really written
            self.reenter_icp()
            new_config = self.read_config()
            if str(new_config) != str(config):
                eprint("Config verification failed.")
                if not self.silent:
                    self.print_vb("Expected:")
                    config.print_config()
                    self.print_vb("Got:")
                    new_config.print_config()
                return False
            self.print_vb("Config verified.")
            self.print_vb("Verification succeeded.")

            self.print_vb("\nResulting Device info:")
            devinfo = self.get_device_info()
            self.print_vb(devinfo)
            self.print_vb()
            if not self.silent:
                config.print_config()
        self.print_vb("Finished programming!\n")
        return True

    def program(self, write_file, ldrom_file="", config: ConfigFlags = None, ldrom_override=True) -> bool:
        """
        Program the device with the given files and config.
        ------



        If ldrom_file is not specified, the LDROM will not be written.
        If config is not specified, the default config for the given aprom and ldrom files will be used.
        If ldrom_override is False, the chosen configuration will not be overridden.


        """
        self._fail_if_not_init()
        lf = None
        try:
            wf = open(write_file, "rb")
        except OSError as e:
            eprint("Could not open %s for reading." % write_file)
            raise e
        if ldrom_file != "":
            try:
                lf = open(ldrom_file, "rb")
            except OSError as e:
                eprint("Could not open %s for reading." % ldrom_file)
                raise e
        aprom_data = wf.read()

        ldrom_data = bytes()
        if lf:
            ldrom_data = lf.read()
        return self.program_data(aprom_data, ldrom_data, config=config, ldrom_config_override=ldrom_override)


def print_usage():
    print("nuvoicpy, a RPi ICP flasher for the Nuvoton N76E003")
    print("written by Nikitalita\n")
    print("Usage:")
    print("\t[-h, --help:                       print this help]")
    print("\t[-u, --status:                     print the connected device info and configuration and exit\n\t\tIf -c is specified, it will also write it to the specified config file.]")
    print("\t[-r, --read=<filename>             read entire flash to file]")
    print("\t[-w, --write=<filename>            write file to APROM/entire flash (if LDROM is disabled)]")
    print("\t[-l, --ldrom=<filename>            write file to LDROM]")
    print("\t[-k, --lock                        lock the chip after writing]")
    print("\t[-c, --config <filename>           use config file for writing (overrides -b and -k)]")
    print("\t[-s, --silent                      silence all output except for errors]")
    print("Pinout:\n")
    print("                           40-pin header J8")
    print(" connect 3.3V of MCU ->    3V3  (1) (2)  5V")
    print("                                 [...]")
    print("	                              (35) (36) GPIO16 <- connect TRIGGER (optional)")
    print("        connect CLK ->  GPIO26 (37) (38) GPIO20 <- connect DAT")
    print("        connect GND ->     GND (39) (40) GPIO21 <- connect RST\n")
    print("                      ________")
    print("                     |   USB  |")
    print("                     |  PORTS |")
    print("                     |________|\n")
    print("Please refer to the 'pinout' command on your RPi\n")


def main() -> int:
    argv = sys.argv[1:]
    try:
        opts, _ = getopt.getopt(argv, "hur:w:l:skb:c:")
    except getopt.GetoptError:
        eprint("Invalid command line arguments. Please refer to the usage documentation.")
        print_usage()
        return 2

    config_dump_cmd = False
    read = False
    read_file = ""
    write = False
    write_file = ""
    ldrom_file = ""
    config_file = ""
    lock_chip = False
    silent = False
    if len(opts) == 0:
        print_usage()
        return 1
    for opt, arg in opts:
        if opt == "-h" or opt == "--help":
            print_usage()
            return 0
        elif opt == "-u" or opt == "--status":
            config_dump_cmd = True
        elif opt == "-r" or opt == "--read":
            read = True
            read_file = arg
        elif opt == "-w" or opt == "--write":
            write_file = arg
            write = True
        elif opt == "-l" or opt == "--ldrom":
            ldrom_file = arg
        elif opt == "-c" or opt == "--config":
            config_file = arg
        elif opt == "-k" or opt == "--lock":
            lock_chip = True
        elif opt == "-s" or opt == "--silent":
            silent = True
        else:
            print_usage()
            return 2

    if read and write:
        eprint("ERROR: Please specify either -r or -w, not both.\n\n")
        print_usage()
        return 2

    if not (read or write or config_dump_cmd):
        eprint("ERROR: Please specify either -r, -w, or -u.\n\n")
        print_usage()
        return 2

    # check to see if the files exist before we start the ICP
    for filename in [write_file, ldrom_file, config_file]:
        if (filename and filename != "") and not os.path.isfile(filename):
            if filename == config_file and config_dump_cmd:
                continue
            eprint("ERROR: %s does not exist.\n\n" % filename)
            print_usage()
            return 2

    try:
        # check to see if the files are the correct size
        if write and os.path.getsize(write_file) > FLASH_SIZE:
            eprint("ERROR: %s is too large for APROM.\n\n" % write_file)
            print_usage()
            return 2
    except:
        eprint("ERROR: Could not read %s.\n\n" % write_file)
        return 2
    # check the length of the ldrom file
    ldrom_size = 0
    if ldrom_file != "":
        try:
            # check the length of the ldrom file
            ldrom_size = os.path.getsize(ldrom_file)
            if not NuvoICP.check_ldrom_size(ldrom_size):
                eprint("Error: LDROM file invalid.")
                return 1
        except:
            eprint("Error: Could not read LDROM file")
            return 2

    # setup write config
    write_config: ConfigFlags = None
    if write:
        if config_file != "":
            write_config = ConfigFlags.from_json_file(config_file)
            if write_config == None:
                eprint("Error: Could not read config file")
                return 1
        else:  # default config
            write_config = ConfigFlags()
            write_config.set_lock(lock_chip)
            write_config.set_ldrom_boot(ldrom_file != "")
            write_config.set_ldrom_size(ldrom_size)

    with NuvoICP(silent=silent) as nuvo:
        devinfo = nuvo.get_device_info()
        if devinfo.device_id != N76E003_DEVID:
            if write and devinfo.cid == 0xFF:
                print("Device not found, chip may be locked, Do you want to attempt a mass erase? (y/N)")
                if input() == "y" or input() == "Y":
                    if not nuvo.mass_erase():
                        eprint("Mass erase failed, exiting...")
                        return 2
                    devinfo = nuvo.get_device_info()
                    eprint(devinfo)
                else:
                    eprint("ERROR: Device not found")
                    return 2
                if devinfo.device_id != N76E003_DEVID:
                    eprint(
                        "ERROR: Unsupported device ID: 0x%04X (mass erase failed!)\n\n" % devinfo.device_id)
                    return 2
            else:
                if devinfo.device_id == 0:
                    eprint("ERROR: Device not found, please check your connections.\n\n")
                    return 2
                eprint(
                    "ERROR: Unsupported device ID: 0x%04X (chip may be locked)\n\n" % devinfo.device_id)
                return 2

        # process commands
        if config_dump_cmd:
            print(devinfo)
            cfg = nuvo.read_config()
            if not cfg:
                eprint("Config read failed!!")
                return 1
            cfg.print_config()
            # if -c is specified, write it to a file
            if config_file != "":
                cfg.to_json_file(config_file)
            return 0
        elif read:
            print(devinfo)
            cfg = nuvo.read_config()
            cfg.print_config()
            print()
            if devinfo.cid == 0xFF or cfg.is_locked():
                eprint("Error: Chip is locked, cannot read flash")
                return 1
            nuvo.dump_flash_to_file(read_file)
            # remove extension from read_file
            config_file = read_file.rsplit(".", 1)[0] + "-config.json"
            cfg.to_json_file(config_file)
        elif write:
            if not nuvo.program(write_file, ldrom_file, write_config):
                eprint("Programming failed!!")
                return 1
        return 0


try:
    if __name__ == "__main__":
        sys.exit(main())
except Exception as e:
    eprint("%s" % e)
    eprint("Exiting...")
    sys.exit(2)
