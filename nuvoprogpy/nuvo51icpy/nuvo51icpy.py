#!/usr/bin/env python3
import math
import platform
import time
import getopt
import sys
import os
from typing import Union

# detect if we are on a raspberry pi
def is_raspberry_pi():
    # check if /sys/firmware/devicetree/base/model exists
    if os.path.isfile("/sys/firmware/devicetree/base/model"):
        with open("/sys/firmware/devicetree/base/model", "r") as f:
            model = f.read().strip()
            if model.startswith("Raspberry Pi"):
                return True
    return False


try:
    from ..config import DeviceInfo, ConfigFlags
    from ..config import *
    if platform.system() == "Linux" and is_raspberry_pi():
        from .lib.libnuvo51icp import LibICP
    else:
        LibICP = None
    from .libicp_iface import ICPLibInterface
except Exception as e:
    # Hack to allow running nuvo51icpy.py directly from the command line
    if __name__ == "__main__":
        # check if config.py exists in the parent directory
        if not os.path.isfile(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "config.py")):
            raise e
    if platform.system() == "Linux" and is_raspberry_pi():
        from lib.libnuvo51icp import LibICP
    else:
        LibICP = None
    sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
    from config import DeviceInfo, ConfigFlags
    from config import *
    from libicp_iface import ICPLibInterface



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


"""
Nuvo51ICP class
Raises:
        PGMInitException: _description_
        NoDeviceException: _description_
        UnsupportedDeviceException: _description_
        Exception: _description_

Returns:
        
"""


class Nuvo51ICP:
    can_write_locked_without_mass_erase = False
    can_mass_erase = True

    @property
    def can_write_ldrom(self):
        return True

    def __init__(self, silent=False, library: Union[ICPLibInterface, str] = "gpiod", _enter_no_init=None, _deinit_reset_high=False, logfunc=None):
        """
        Nuvo51ICP constructor
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
        if library is None:
            library = "gpiod"
        if isinstance(library, str):
            if LibICP is None:
                raise Exception("LibICP not available on this platform!")
            self.icp = LibICP(library)
        else:
            self.icp: ICPLibInterface = library
        self._enter_no_init = _enter_no_init
        self.deinit_reset_high = _deinit_reset_high
        self.initialized = False
        self.silent = silent
        self.pad_data = True
        self.print_func = print if logfunc is None else logfunc
        self.print_err_func = eprint if logfunc is None else logfunc

    def __enter__(self):
        """
        Called when using Nuvo51ICP in a with statement, such as "with Nuvo51ICP() as icp:"

        #### Returns:
            Nuvo51ICP: The Nuvo51ICP object
        """
        if self._enter_no_init:
            return self
        self.init(True, True, True)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def print_vb(self, *args, **kwargs):
        """
        Print a message if print progress is enabled
        """
        if not self.silent:
            self.print_func(*args, **kwargs)

    def print_err(self, *args, **kwargs):
        """
        Print an error message
        """
        self.print_err_func(*args, **kwargs)

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
                    device_id = self.icp.entry()
                    if device_id != 0:
                        self.print_vb("Connected!")
                        return True
                    fullexit_tries += 1
                fullexit_tries = 0
                self.print_vb("Attempting reinitialization...")
                self.icp.exit()
                self.icp.deinit(self.deinit_reset_high)
                time.sleep(0.5)
                self.icp.init()
                device_id = self.icp.entry()
                if device_id != 0:
                    self.print_vb("Connected!")
                    return True
                reinit_tries += 1
        except KeyboardInterrupt:
            self.print_err("Retry aborted!")
        except Exception as e:
            self.print_err("Retry error!")
            raise e
        self.print_err("Retry failed!")
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
        self.initialized = self.icp.init()
        self.icp.entry(do_reset_seq)
        if not self.initialized:
            raise PGMInitException("ERROR: Could not initialize ICP.")
        if check_device:
            dev_info = self.get_device_info()
            cid = self.icp.read_cid()
            if dev_info.did == 0:
                if not retry or not self.retry():
                    self.icp.exit()
                    self.icp.deinit(self.deinit_reset_high)
                    raise NoDeviceException(
                        "ERROR: No device detected, please check your connections!")
                dev_info = self.get_device_info()
                cid = self.icp.read_cid()
            if dev_info.did == 0xFFFF and cid == 0xFF:
                self.print_err("WARNING: Read Device ID of 0xFFFF and cid of 0xFF, device may be locked!")
                self.print_err("Proceeding anyway...")
            elif dev_info.is_unsupported:
                self.close()
                raise UnsupportedDeviceException(
                    "ERROR: Unsupported device detected: %08X (%s)!" % (dev_info.device_id, dev_info.chip_name))

    def close(self):
        """
        Deinitialize the ICP interface
        ------

        """
        if self.initialized:
            self.initialized = False
            self.icp.exit()
            self.icp.deinit(self.deinit_reset_high)

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

    def get_pid(self) -> int:
        self._fail_if_not_init()
        return self.icp.read_pid()

    def get_cid(self) -> int:
        self._fail_if_not_init()
        return self.icp.read_cid()

    def get_uid(self) -> bytes:
        self._fail_if_not_init()
        return self.icp.read_uid()
    
    def get_ucid(self) -> bytes:
        self._fail_if_not_init()
        return self.icp.read_ucid()

    def read_config(self) -> ConfigFlags:
        self._fail_if_not_init()
        device_info = self.get_device_info()
        return ConfigFlags.from_bytes(self.icp.read_flash(device_info.config_addr, device_info.config_len), device_info.device_id)

    def write_config(self, config_bytes: bytes) -> bool:
        self._fail_if_not_init()
        device_info = self.get_device_info()
        return self.icp.write_flash(device_info.config_addr, config_bytes)
                    
    def mass_erase(self):
        self._fail_if_not_init()
        self.print_vb("Erasing flash...")
        cid = self.get_cid()
        if not self.icp.mass_erase():
            self.print_err("ERROR: Mass erase failed, device not found.")
            return False
        if cid == 0xFF or cid == 0x00:
            self.reenter_icp()
            device_info = self.get_device_info()
            cid = self.get_cid()
            if (device_info.is_unsupported) or cid == 0xFF or cid == 0x00:
                self.print_err("ERROR: Mass erase failed, device not found.")
                return False
        return True

    def get_device_info(self) -> DeviceInfo:
        self._fail_if_not_init()
        return DeviceInfo(self.get_device_id(), self.get_pid())

    def page_erase(self, addr):
        self._fail_if_not_init()
        return self.icp.page_erase(addr)

    def read_flash(self, addr, len) -> bytes:
        self._fail_if_not_init()
        return self.icp.read_flash(addr, len)

    def write_flash(self, addr, data) -> bool:
        self._fail_if_not_init()
        return self.icp.write_flash(addr, data)
    
    def erase_sprom(self, addr) -> bool:
        self._fail_if_not_init()
        device_info = self.get_device_info()
        if device_info.sprom_len == 0:
            self.print_err("ERROR: Device does not have SPROM.")
            return False
        return self.icp.page_erase(device_info.sprom_addr + addr)

    def read_sprom(self, addr, len) -> bytes:
        self._fail_if_not_init()
        device_info = self.get_device_info()
        if device_info.sprom_len == 0:
            self.print_err("ERROR: Device does not have SPROM.")
            return None
        addr = device_info.sprom_addr + addr
        return self.read_flash(addr, len)
    
    def write_sprom(self, addr, data: bytes) -> bool:
        self._fail_if_not_init()
        device_info = self.get_device_info()
        if device_info.sprom_len == 0:
            self.print_err("ERROR: Device does not have SPROM.")
            return False
        addr = device_info.sprom_addr + addr
        return self.write_flash(addr, data)
    
    def is_locked(self):
        self._fail_if_not_init()
        return (self.get_cid() == 0xFF or self.read_config().is_locked())

    def dump_flash(self) -> bytes:
        self._fail_if_not_init()
        device_info = self.get_device_info()
        return self.read_flash(device_info.aprom_addr, device_info.flash_size)

    def dump_flash_to_file(self, read_file:str) -> bool:
        self._fail_if_not_init()
        try:
            f = open(read_file, "wb")
        except OSError as e:
            self.print_err("Dump to %s failed: %s" % (read_file, e))
            raise e
        self.print_vb("Reading flash...")
        ext = read_file.split(".")[-1]
        config = self.read_config()
        device_info = self.get_device_info()
        ldrom_size = device_info.get_ldrom_size(config)
        if ldrom_size > 0:
            ldrom_addr = device_info.get_ldrom_addr(config)
            ldrom_file = read_file.rsplit(".", 1)[0] + "-ldrom.bin"
            lf = open(ldrom_file, "wb")
            lf.write(self.read_flash(ldrom_addr, ldrom_size))
            lf.close()
        f.write(self.read_flash(device_info.aprom_addr, device_info.get_aprom_size(config)))
        f.close()
        self.print_vb("Done.")
        return True


    def verify_flash(self, data: bytes, start_address: int, report_unmatched_bytes=True) -> bool:
        """
        #### Args:
            data (bytes): 
                bytes to verify
            start_address (int):
                The start address to verify the data at
            report_unmatched_bytes (bool) (=False)):
                If True, the number of unmatched bytes will be printed to stderr

        #### Returns:
            bool:
                True if the data matches the flash, False otherwise
        """
        self._fail_if_not_init()
        read_data = self.read_flash(start_address, len(data))
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
            self.print_err("Verification failed. %d byte errors." % byte_errors)
        return result

    def check_rom_size(self, aprom_size, ldrom_size) -> bool:
        self._fail_if_not_init()
        device_info = self.get_device_info()
        if aprom_size > device_info.flash_size:
            self.print_err("ERROR: APROM size too large for flash size of ".format(device_info.flash_size))
            return False
        if ldrom_size > device_info.ldrom_max_size:
            self.print_err("ERROR: LDROM size above max of {}.".format(device_info.ldrom_max_size))
            return False
        # if ldrom_size > 0 and aprom_size + ldrom_size > device_info.flash_size:
        #     self.print_err("ERROR: APROM and LDROM sizes exceed flash size of {}.".format(device_info.flash_size))
        #     return False
        return True

    @staticmethod
    def pad_rom(data: bytes, max_length: int) -> bytes:
        if max_length - len(data) < 0:
            return data
        return data + bytes([0xFF] * (max_length - len(data)))

    def erase_aprom_area(self, config: ConfigFlags) -> bool:
        self._fail_if_not_init()
        if not config:
            self.print_err("ERROR: No config provided.")
            return False
        dev_info = self.get_device_info()
        aprom_size = dev_info.get_aprom_size(config)
        for i in range(dev_info.aprom_addr,dev_info.aprom_addr + aprom_size, dev_info.page_size):
            self.page_erase(i)
        return True

    def erase_ldrom_area(self, config: ConfigFlags):
        self._fail_if_not_init()
        if not config:
            self.print_err("ERROR: No config provided.")
            return False
        dev_info: DeviceInfo = self.get_device_info()
        ldrom_size = dev_info.get_ldrom_size(config)
        if not ldrom_size:
            self.print_err("ERROR: LDROM size is 0 in config.")
            return False
        ldrom_addr = dev_info.get_ldrom_addr(config)
        for i in range(ldrom_addr, ldrom_addr + ldrom_size, dev_info.page_size):
            self.page_erase(i)
        return True

    def _needs_unlock(self):
        return (not self.can_write_locked_without_mass_erase) and self.is_locked()

    def _aprom_config_precheck(self, aprom_data: bytes, config: ConfigFlags) -> int:
        self._fail_if_not_init()
        dev_info = self.get_device_info()
        aprom_size = dev_info.get_aprom_size(config)
        if aprom_size != len(aprom_data):
            self.print_err("WARNING: APROM file size does not match config: %d KB vs %d KB" % (
                len(aprom_data) / 1024, aprom_size / 1024))
            if aprom_size < len(aprom_data):
                self.print_err("APROM data is too large for configuration ({} KB vs {} KB).".format(
                    len(aprom_data) / 1024, aprom_size / 1024))
                self.print_err("Please provide a smaller APROM file or update the configuration.")
                return -1
            else:
                if self.pad_data:
                    self.print_err("APROM will be padded with 0xFF.")
        return aprom_size

    def _ldrom_config_precheck(self, ldrom_data: bytes, config: ConfigFlags, override_size: bool, override_bootable:bool) -> bool:
        self._fail_if_not_init()
        dev_info = self.get_device_info()
        if not self.can_write_ldrom:
            self.print_err("ERROR: LDROM programming is not supported on this device.")
            return False
        if not config:
            self.print_err("ERROR: No config provided.")
            return False
        if len(ldrom_data) == 0:
            self.print_err("ERROR: No LDROM data provided.")
            return False
        else:
            if config.is_ldrom_boot() != True:
                self.print_err("WARNING: LDROM boot flag not set in config")
                if override_bootable:
                    self.print_err("Overriding LDROM boot in config.")
                    config.set_ldrom_boot(True)
                else:
                    self.print_err("LDROM will not be bootable.")
            if not dev_info.has_configurable_size_ldrom:
                return True
            if len(ldrom_data) % 1024 != 0 and self.pad_data:
                self.print_err("WARNING: LDROM is not a multiple of 1024 bytes, data will be padded with 0xFF.")
            ldrom_size_kb = math.ceil(len(ldrom_data) / 1024)
            if ldrom_size_kb > config.get_ldrom_size_kb():
                if override_size:
                    self.print_err("WARNING: LDROM size does not match config: %d KB vs %d KB" % (
                        ldrom_size_kb, config.get_ldrom_size_kb()))
                    self.print_err("Overriding LDROM size in config.")
                    config.set_ldrom_size_kb(ldrom_size_kb)
                else:
                    self.print_err("ERROR: LDROM size in config is greater than LDROM data size (%d KB vs %d KB)" % (
                        config.get_ldrom_size_kb(), ldrom_size_kb))
                    self.print_err("Not programming LDROM. Either truncate the LDROM data or update the config.")
                    return False
            elif ldrom_size_kb < config.get_ldrom_size_kb():
                self.print_err("WARNING: LDROM size does not match config: %d KB vs %d KB" % (
                    ldrom_size_kb, config.get_ldrom_size_kb()))
                if override_size:
                    self.print_err("Overriding LDROM size in config.")
                    config.set_ldrom_size_kb(ldrom_size_kb)
                elif self.pad_data:
                    self.print_err("LDROM will be padded with 0xFF.")
        return True

    def program_config(self, config: ConfigFlags, erase=True) -> bool:
        """
        Programs the config bytes.
        ------

        #### Keyword args:
            config: ConfigFlags:
                The configuration flags to program
            erase: bool (=True):
                If False, the config block will not be erased before writing.

                PLEASE NOTE: We avoid erasing the configuration bytes after a mass_erase() to prevent flash wear.
                You don't want to use this if you're using program_config() by itself, as the config will
                fail to be written if the config isn't the default (FF FF FF FF FF).
        """
        self._fail_if_not_init()
        device_info = self.get_device_info()
        if erase:
            self.page_erase(device_info.config_addr)
        self.write_flash(device_info.config_addr, config.to_bytes())
        return True

    def program_aprom(self, aprom_data, config: ConfigFlags = None, verify=True, erase=True) -> bool:
        """
        Programs the APROM with the given data.

        #### Keyword args:
            aprom_data: bytes:
                The data to program to the APROM
            config: ConfigFlags:
                The configuration flags for this operation
            verify: bool (=True):
                If True, the data will be verified after writing.
            erase: bool (=True):
                If True, the APROM area will be erased before writing the data.
        """
        self._fail_if_not_init()
        device_info = self.get_device_info()
        if len(aprom_data) > device_info.flash_size:
            self.print_err("ERROR: APROM size too large for flash size of {}".format(device_info.flash_size))
            return False
        if not config and not self._needs_unlock():
            config = self.read_config()
        if config:
            if not self._aprom_config_precheck(aprom_data, config):
                return False
        if self._needs_unlock():
            if erase:
                if not self.mass_erase():
                    return False
                erase = False
            else:
                self.print_err("ERROR: Device is locked, cannot program aprom.")
                return False
        if not config:
            config = self.read_config()
            if not self._aprom_config_precheck(aprom_data, config):
                return False
        if erase:
            self.erase_aprom_area(config)
        if self.pad_data:
            aprom_data = self.pad_rom(aprom_data, device_info.get_aprom_size(config))
        self.print_vb("Programming APROM...")
        if not self.write_flash(device_info.aprom_addr, aprom_data):
            self.print_err("Programming APROM Failed!")
            return False
        self.print_vb("APROM programmed.")
        if not verify:
            return True
        if not self.verify_flash(aprom_data, device_info.aprom_addr):
            self.print_err("APROM verification failed.")
            return False
        self.print_vb("APROM verification succeeded.")
        self.print_vb("Finished programming APROM.")
        return True

    def program_ldrom(self, ldrom_data: bytes, config: ConfigFlags, erase=True, verify=True) -> bool:
        """
        Programs the LDROM with the given data.

        #### Keyword args:
            ldrom_data: bytes:
                The data to program to the LDROM
            config: ConfigFlags:
                The configuration flags for this operation
            erase: bool (=True):
                If True, the LDROM area will be erased before writing the data.
            verify: bool (=True):
                If True, the data will be verified after writing.

        #### Returns:
            bool:
                True if the operation succeeded, False otherwise
        """
        self._fail_if_not_init()
        if not config:
            self.print_err("ERROR: No config provided.")
            return False
        device_info = self.get_device_info()
        if device_info.is_unsupported:
            self.print_err("ERROR: Device is not supported for LDROM programming.")
            return False
        start_addr = device_info.get_ldrom_addr(config)
        if len(ldrom_data) > device_info.ldrom_max_size:
            self.print_err("ERROR: LDROM size greater than max of 4KB. Not programming...")
            return False
        if not self._ldrom_config_precheck(ldrom_data, config, False, False):
            return False
        if self.pad_data:
            ldrom_data = self.pad_rom(ldrom_data, device_info.get_ldrom_size(config))
        self.print_vb("Programming LDROM (%d KB)..." % int(len(ldrom_data) / 1024))
        if erase:
            if self._needs_unlock():
                if not self.mass_erase():
                    return False
            else:
                self.erase_ldrom_area(config)
        self.write_flash(start_addr, ldrom_data)
        if verify:
            if not self.verify_flash(ldrom_data, start_addr):
                self.print_vb("LDROM verification failed.")
                return False
            else:
                self.print_vb("LDROM verification succeeded.")
        self.print_vb("LDROM programmed.")
        return True

    def _run_prechecks(self, aprom_data, ldrom_data, config, ldrom_config_override):
        passed = True
        if len(ldrom_data) > 0:
            passed = self._ldrom_config_precheck(ldrom_data, config, ldrom_config_override, ldrom_config_override)
        if passed and len(aprom_data) > 0:
            passed = self._aprom_config_precheck(aprom_data, config)
        return passed

    def _try_mass_erase(self, _erase: bool):
        if _erase:
            if not self.mass_erase():
                return False
        else:
            self.print_err("ERROR: Device is locked, cannot program.")
            return False
        self.print_vb("Flash erased.")
        return True

    def program_all(self, aprom_data, ldrom_data=bytes(), config: ConfigFlags = None, verify=True, ldrom_config_override=False, _erase=True) -> bool:
        self._fail_if_not_init()
        if not self.check_rom_size(len(aprom_data), len(ldrom_data)):
            return False
        # if we don't have a config and the device isn't locked, get the current config
        if not config and not self._needs_unlock():
            config = self.read_config()
        if config:
            if not self._run_prechecks(aprom_data, ldrom_data, config, ldrom_config_override):
                return False

        did_mass_erase = False
        if self._needs_unlock():
            if not self._try_mass_erase(_erase):
                return False
            # don't need to erase anything if we did a mass erase
            _erase = False
            did_mass_erase = True
        if not config:
            config = self.read_config()
            # config will be set to the default values if it's not provided, so set override to True
            ldrom_config_override = True
            if not self._run_prechecks(aprom_data, ldrom_data, config, ldrom_config_override):
                return False
        device_info = self.get_device_info()
        ldrom_addr = device_info.get_ldrom_addr(config)
        if len(aprom_data) > 0:
            if self.pad_data:
                aprom_data = self.pad_rom(aprom_data, device_info.get_aprom_size(config))
            if _erase:
                self.erase_aprom_area(config)
            self.print_vb("Programming APROM ({} KB)...".format(len(aprom_data) // 1024))
            self.write_flash(device_info.aprom_addr, aprom_data)
        if len(ldrom_data) > 0:
            if self.pad_data:
                ldrom_data = self.pad_rom(ldrom_data, device_info.get_ldrom_size(config))
            if _erase:
                self.erase_ldrom_area(config)
            self.print_vb("Programming LDROM ({} KB)...".format(len(ldrom_data) // 1024))
            self.write_flash(ldrom_addr, ldrom_data)
        if str(config) != str(self.read_config()):
            self.program_config(config, (not did_mass_erase))

        if verify:
            if len(aprom_data) > 0 or len(ldrom_data) > 0:
                if len(aprom_data) > 0 and not (self.verify_flash(aprom_data, device_info.aprom_addr)):
                    self.print_vb("APROM Verification failed.")
                    return False
                if len(ldrom_data) > 0 and not (self.verify_flash(ldrom_data, ldrom_addr)):
                    self.print_vb("LDROM Verification failed.")
                    return False
                self.print_vb("ROM data verified.")
            # check that the config was really written
            # self.reenter_icp()
            new_config = self.read_config()
            if str(new_config) != str(config):
                self.print_err("Config verification failed.")
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

    def program_all_files(self, write_file:str="", ldrom_file:str="", config_file: str = "", ldrom_override=True) -> bool:
        self._fail_if_not_init()
        wf = None
        lf = None
        if not write_file and not ldrom_file and not config_file:
            self.print_err("ERROR: No data to program.")
            return False
        if write_file != "":
            try:
                wf = open(write_file, "rb")
            except OSError as e:
                self.print_err("Could not open %s for reading." % write_file)
                raise e
        if ldrom_file != "":
            try:
                lf = open(ldrom_file, "rb")
            except OSError as e:
                self.print_err("Could not open %s for reading." % ldrom_file)
                raise e
        config = None
        if config_file != "":
            config = ConfigFlags.from_json_file(config_file, self.get_device_id())
            if not config:
                self.print_err("ERROR: Could not read config file.")
                return False

        aprom_data = bytes()
        ldrom_data = bytes()
        if wf:
            aprom_data = wf.read()
        if lf:
            ldrom_data = lf.read()
        return self.program_all(aprom_data, ldrom_data, config=config, ldrom_config_override=ldrom_override)


def print_usage():
    print("nuvo51icpy, an ICP flasher for the Nuvoton NuMicro 8051 line of chips")
    print("written by Nikita Lita\n")
    print("Usage:")
    print("\t-h, --help:                       print this help")
    print("* Status Commands:")
    print("\t-u, --status:                     print the connected device info and configuration and exit")
    print("* Read Commands:")
    print("\t-r, --read=<filename>             read entire flash to file")
    print("* Write Commands (can be used in combination or seperately):")
    print("\t-w, --write=<filename>            write file to APROM")
    print("\t-l, --ldrom=<filename>            write file to LDROM")
    print("\t-e, --mass-erase                  mass erase the chip")
    print("\t-c, --config <filename>           write configuration bytes with the settings in the specified config.json file")
    print("\t                                        * look at 'config-example.json' for the format")
    print("Options:")
    print("\t-s, --silent                      silence all output except for errors")
    print("Pinout:\n")
    print("                           40-pin header J8")
    print(" connect 3.3V of MCU ->    3V3  (1) (2)  5V")
    print("                                 [...]")
    print("                               (35) (36) GPIO16 <- connect TRIGGER (optional)")
    print("        connect CLK ->  GPIO26 (37) (38) GPIO20 <- connect DAT")
    print("        connect GND ->     GND (39) (40) GPIO21 <- connect RST\n")
    print("                            ________")
    print("                           |   USB  |")
    print("                           |  PORTS |")
    print("                           |________|\n")
    print("Please refer to the 'pinout' command on your RPi\n")

def exit_with_code(message, num, usage=True):
    eprint(message)
    if usage:
        print_usage()
    return num

def main() -> int:
    argv = sys.argv[1:]
    try:
        opts, _ = getopt.getopt(argv, "hur:w:l:seb:c:")
    except getopt.GetoptError:
        return exit_with_code("Invalid command line arguments. Please refer to the usage documentation.", 2)

    status_cmd = False
    read_cmd = False
    read_file = ""
    aprom_cmd = False
    mass_erase_cmd = False
    write_file = ""
    ldrom_file = ""
    config_file = ""
    silent = False
    main_cmds = 0
    if len(opts) == 0:
        print_usage()
        return 1
    for opt, arg in opts:
        if opt == "-h" or opt == "--help":
            print_usage()
            return 0
        elif opt == "-u" or opt == "--status":
            main_cmds += 1
            status_cmd = True
        elif opt == "-r" or opt == "--read":
            main_cmds += 1
            read_cmd = True
            read_file = arg
        elif opt == "-w" or opt == "--write":
            write_file = arg
            aprom_cmd = True
        elif opt == "-e" or opt == "--mass-erase":
            mass_erase_cmd = True
        elif opt == "-l" or opt == "--ldrom":
            ldrom_file = arg
        elif opt == "-c" or opt == "--config":
            config_file = arg
        elif opt == "-s" or opt == "--silent":
            silent = True
        else:
            print_usage()
            return 2
    is_writing = False
    if aprom_cmd or ldrom_file or mass_erase_cmd or config_file:
        is_writing = True
        main_cmds += 1
    if main_cmds > 1:
        return exit_with_code("ERROR: --read, --write, and --status are mutually exclusive.\n\n", 2)
    if main_cmds == 0 and not (mass_erase_cmd or config_file != ""):
        return exit_with_code("ERROR: No command specified.\n\n", 2)
    # read can't be used with write commands, and vice versa
    if (read_cmd or status_cmd) and (aprom_cmd or ldrom_file or mass_erase_cmd or config_file):
        return exit_with_code("ERROR: --read and --status cannot be used with write commands!\n\n", 2)

    # check to see if the files exist before we start the ICP
    if (not read_cmd) and (not status_cmd):
        for filename in [write_file, ldrom_file, config_file]:
            if (filename and filename != ""):
                if not os.path.isfile(filename):
                    return exit_with_code("ERROR: %s does not exist.\n\n" % filename, 2)
                elif not os.access(filename, os.R_OK):
                    return exit_with_code("ERROR: %s is not readable.\n\n" % filename, 2)

    with Nuvo51ICP(silent=silent) as nuvo:
        devinfo = nuvo.get_device_info()
        did_mass_erase = False
        if devinfo.is_unsupported:
            if is_writing and nuvo._needs_unlock():
                print("Device not found, chip may be locked, Do you want to attempt a mass erase? (y/N)")
                if input() == "y" or input() == "Y":
                    if not nuvo.mass_erase():
                        return exit_with_code("Mass erase failed! Exiting...", 2, False)
                    did_mass_erase = True
                    devinfo = nuvo.get_device_info()
                    eprint(devinfo)
                else:
                    return exit_with_code("Device not found! Exiting...", 2, False)
                if devinfo.is_unsupported:
                    return exit_with_code("ERROR: Unsupported device ID: 0x%04X (mass erase failed!)\n\n" % devinfo.device_id, 2, False)
            else:
                if devinfo.device_id == 0:
                    return exit_with_code("ERROR: Device not found, please check your connections.\n\n", 2, False)
                return exit_with_code("ERROR: Unsupported device ID: 0x%04X (chip may be locked)\n\n" % devinfo.device_id, 2, False)
        if not did_mass_erase and mass_erase_cmd:
            if not nuvo.mass_erase():
                return exit_with_code("Mass erase failed! Exiting...", 2, False)
            devinfo = nuvo.get_device_info()
            eprint(devinfo)
            print("Mass erase successful.")
        # process commands
        if status_cmd:
            print(devinfo)
            cfg = nuvo.read_config()
            if not cfg:
                return exit_with_code("Config read failed!!", 1, False)
            cfg.print_config()
            return 0
        elif read_cmd:
            print(devinfo)
            cfg = nuvo.read_config()
            cfg.print_config()
            print()
            if nuvo._needs_unlock():
                return exit_with_code("Error: Chip is locked, cannot read flash", 1, False)
            nuvo.dump_flash_to_file(read_file)
            # remove extension from read_file
            config_file = read_file.rsplit(".", 1)[0] + "-config.json"
            cfg.to_json_file(config_file)
        elif ldrom_file or write_file or config_file:
            if not nuvo.program_all_files(write_file, ldrom_file, config_file, not(config_file != "")):
                return exit_with_code("Programming failed!!", 1, False)
        return 0


try:
    if __name__ == "__main__":
        sys.exit(main())
except Exception as e:
    eprint("%s" % e)
    eprint("Exiting...")
    sys.exit(2)
