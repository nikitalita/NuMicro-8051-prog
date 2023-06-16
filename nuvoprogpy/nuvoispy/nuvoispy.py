#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# nuvoispy - ISP-over-UART programmer for cheap N76E003-based devboards
# requires the N76E003_ISP example from Nuvoton flashed on the chip
# (some boards come preprogrammed with it)
#
# Copyright (c) 2019-2020 Steve Markgraf <steve@steve-m.de>
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


import getopt
import os
import platform
import sys
import serial
import time


try:
    from ..nuvoprog import NuvoProg
    from ..config import *
    from ..config import ConfigFlags
except Exception as e:
    # Hack to allow running nuvoicpy.py directly from the command line
    if __name__ == "__main__":
        # check if config.py exists in the parent directory
        if not os.path.isfile(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "config.py")):
            raise e
    sys.path.append(os.path.join(
        os.path.dirname(os.path.realpath(__file__)), ".."))
    from config import *
    from nuvoprog import NuvoProg

CMD_UPDATE_APROM = 0xa0
CMD_UPDATE_CONFIG = 0xa1
CMD_READ_CONFIG = 0xa2
CMD_ERASE_ALL = 0xa3
CMD_SYNC_PACKNO = 0xa4
CMD_GET_FWVER = 0xa6
CMD_RUN_APROM = 0xab
CMD_RUN_LDROM = 0xac
CMD_CONNECT = 0xae
CMD_GET_DEVICEID = 0xb1

# FW version that we know we can use the extended commands on
EXTENDED_CMDS_FW_VER = 0xD0

CMD_RESET = 0xad   # not implemented in default N76E003 ISP rom
CMD_GET_FLASHMODE = 0xCA  # not implemented in default N76E003 ISP rom
CMD_WRITE_CHECKSUM = 0xC9  # not implemented in default N76E003 ISP rom
CMD_RESEND_PACKET = 0xFF  # not implemented in default N76E003 ISP rom
CMD_READ_ROM = 0xa5   # non-official
CMD_DUMP_ROM = 0xaa   # non-official
CMD_GET_UID = 0xb2   # non-official
CMD_GET_CID = 0xb3   # non-official
CMD_GET_UCID = 0xb4   # non-official
CMD_ISP_PAGE_ERASE = 0xD5   # non-official

# special commands for NuvoICP arduino sketch
ICP_BRIDGE_FW_VER = 0xE0

CMD_UPDATE_DATAFLASH = 0xC3  # not implemented in default N76E003 ISP rom
CMD_ISP_MASS_ERASE = 0xD6   # non-official

PKT_CMD_START = 0
PKT_CMD_SIZE = 4
PKT_SEQ_START = 4
PKT_SEQ_SIZE = 4
PKT_HEADER_END = 8
PACKSIZE = 64
UPDATE_PKT_SIZE = 56

DUMP_PKT_CHECKSUM_START = PKT_HEADER_END
DUMP_PKT_CHECKSUM_SIZE = 0  # disabled for now
DUMP_DATA_START = (DUMP_PKT_CHECKSUM_START + DUMP_PKT_CHECKSUM_SIZE)
DUMP_DATA_SIZE = (PACKSIZE - DUMP_DATA_START)

DEFAULT_SER_BAUD = 115200
DEFAULT_SER_TIMEOUT = 0.025  # 25ms


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


class NoDevice(Exception):
    pass


class NotInitialized(Exception):
    pass


class ExtendedCmdsNotSupported(Exception):
    pass


class ChecksumError(Exception):
    pass


def progress_bar(text, value, endvalue, bar_length=54):
    percent = float(value) / endvalue
    arrow = '-' * int(round(percent * bar_length)-1) + '>'
    spaces = ' ' * (bar_length - len(arrow))

    print("\r{0}: [{1}] {2}%".format(text, arrow +
          spaces, int(round(percent * 100))), end='\r')


class NuvoISP(NuvoProg):
    def __init__(self, serial_rate=DEFAULT_SER_BAUD, serial_timeout=DEFAULT_SER_TIMEOUT, serial_port=("COM1" if platform.system() == "Windows" else "/dev/ttyACM0"), open_wait: float = 0.2, silent=False):
        """
        NuvoISP constructor
        ------

        #### Keyword args:
            serial_rate (int): Serial baud rate
            serial_timeout (float): Serial timeout in seconds
            serial_port (str): Serial port to use (default = "COM1" on Windows, "/dev/ttyACM0" on Linux)
            open_wait (float): Time to wait for the serial port to open before sending commands (default = 0.2s)
            silent (bool): If True, suppresses all output

        """
        self.ser = None
        self.silent = silent
        self.serial_rate = serial_rate
        self.serial_timeout = serial_timeout
        self.open_wait = open_wait
        self.serial_port = serial_port
        self.seq_num = 0
        self.fw_ver = 0
        self._connected = False

    def __enter__(self):
        """
        Called when using NuvoISP in a with statement, such as "with NuvoISP() as prog:"

        #### Returns:
            NuvoISP: The NuvoProg object
        """
        self.init()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @ property
    def connected(self):
        return self._connected

    def _fail_if_not_init(self):
        if not self.connected:
            raise NotInitialized("ISP is not connected")

    def _fail_if_not_extended(self):
        if not self.supports_extended_cmds:
            raise ExtendedCmdsNotSupported("Extended commands are not supported by this firmware version")

    def _fail_if_not_icp_bridge(self):
        if not self.is_icp_bridge:
            raise ExtendedCmdsNotSupported("ICP-bridge only commands are not supported in LDROM")

    @ property
    def serial_timeout(self):
        return self._serial_timeout

    @ serial_timeout.setter
    def serial_timeout(self, value):
        self._serial_timeout = value
        if self.ser:
            if self.ser.is_open:
                self.reopen_serial()
            else:
                self.ser.timeout = value

    @ property
    def serial_rate(self):
        return self._serial_rate

    @ serial_rate.setter
    def serial_rate(self, value):
        self._serial_rate = value
        if self.ser:
            if self.ser.is_open:
                self.reopen_serial()
            else:
                self.ser.baudrate = value

    @ property
    def serial_port(self):
        return self._serial_port

    @ serial_port.setter
    def serial_port(self, value):
        self._serial_port = value
        if self.ser:
            if self.ser.is_open:
                self.reopen_serial()
            else:
                self.ser.port = value

    @ property
    def supports_extended_cmds(self):
        return self.fw_ver >= EXTENDED_CMDS_FW_VER

    @ property
    def is_icp_bridge(self):
        return self.fw_ver == ICP_BRIDGE_FW_VER

    def print_vb(self, *args, **kwargs):
        """
        Print a message if print progress is enabled
        """
        if not self.silent:
            print(*args, **kwargs)

    @staticmethod
    def verify_chksum(tx, rx):
        txsum = 0
        for i in range(len(tx)):
            txsum += tx[i]

        txsum &= 0xffff
        rxsum = (rx[1] << 8) + rx[0]

        return (rxsum == txsum)

    def _disconnect(self):
        cmd = self._cmd_packet(CMD_RUN_APROM)
        self.ser.write(cmd)
        time.sleep(self.serial_timeout)
        rx = self.ser.read(PACKSIZE)
        self._connected = False

    def reopen_serial(self, wait: float = None):
        if wait is None:
            wait = self.open_wait
        if not self.ser:
            self.ser = serial.Serial(self.serial_port, self.serial_rate, timeout=self.serial_timeout)
        else:
            if self.ser.is_open:
                self.ser.close()
                time.sleep(0.5)
            self.ser = serial.Serial(self.serial_port, self.serial_rate, timeout=self.serial_timeout)
        time.sleep(wait)

    def _cmd_packet(self, cmd):
        self.seq_num = self.seq_num + 1
        return bytes([cmd]) + bytes(3) + bytes([self.seq_num & 0xff, (self.seq_num >> 8) & 0xff]) + bytes(PACKSIZE-6)

    def _connect_req(self, retry=True):
        time.sleep(self.serial_timeout)
        MAX_CONNECT_RETRIES = 3
        MAX_SEND_RETRIES = 100
        MAX_READ_RETRIES = 0
        connect_retries = 0
        send_retries = 0
        connected = False
        _open_wait = self.open_wait if self.open_wait > 0 else 1
        while not connected:
            cmd = self._cmd_packet(CMD_CONNECT)
            self.ser.write(cmd)
            time.sleep(self.serial_timeout)

            read_retries = 0

            while (self.ser.in_waiting != PACKSIZE):
                if read_retries > MAX_READ_RETRIES:
                    break
                read_retries += 1
                time.sleep(self.serial_timeout)
            if self.ser.in_waiting != PACKSIZE:
                self.ser.read(self.ser.in_waiting)
                send_retries += 1
                # the device likely reset on opening serial and we didn't wait long enough, try again
                if send_retries == MAX_SEND_RETRIES:
                    if not retry or connect_retries == MAX_CONNECT_RETRIES:
                        raise NoDevice
                    connect_retries += 1
                    send_retries = 0
                    _open_wait = _open_wait * connect_retries
                    self.print_vb("Attempting to reconnect... (backoff = {}s)".format(_open_wait))
                    self.reopen_serial(_open_wait)
                    time.sleep(_open_wait)
                    self._disconnect()  # in case the device does not reset on opening serial and we're still connected
                    time.sleep(0.2)
                    self.print_vb("If not using the arduino ICP programmer, hit reset on the chip")
                continue

            rx = self.ser.read(self.ser.in_waiting)

            if NuvoISP.verify_chksum(cmd, rx):
                # print("Got valid reply")
                connected = True

    def _connect(self, retry=True):
        self._connect_req(retry)
        self.send_cmd(self._cmd_packet(CMD_SYNC_PACKNO))
        self.fw_ver = self.get_fwver()
        self._connected = True

    def send_cmd(self, tx, timeout=None, fail_on_checksum_error=True):
        if timeout is None:
            timeout = self.serial_timeout
        # todo: only have 5 retries
        sent = False
        retries = 0
        while not sent:
            try:
                self.ser.write(tx)
                sent = True
            except serial.SerialTimeoutException:
                retries = retries + 1
                if (retries > 5):
                    raise TimeoutError("Too many retries, aborting!")
                self.print_vb("Timeout sending packet, retrying...")
                time.sleep(timeout)

        tries = 0
        success = True
        while True:
            time.sleep(timeout)
            nbytes = self.ser.in_waiting

            if (nbytes < PACKSIZE):
                tries = tries + 1
                if (tries > 5):
                    print("Re-sending packet!")
                    self.ser.write(tx)
                continue

            rx = self.ser.read(PACKSIZE)

            if (len(rx) != PACKSIZE):
                continue
            else:
                if not NuvoISP.verify_chksum(tx, rx):
                    if fail_on_checksum_error:
                        raise ChecksumError("Invalid checksum received!")
                    success = False
                break

        return success, rx

    def get_fwver(self):
        _, rx = self.send_cmd(self._cmd_packet(CMD_GET_FWVER))
        return rx[8]

    def init(self, retry=True, check_for_device=True):
        self.reopen_serial(self.open_wait)
        self.print_vb("Connecting...")
        self.print_vb("If not using the arduino ICP programmer, hit reset on the chip")
        self._connect(retry)
        self.print_vb("Connected!")
        self.print_vb("ISP firmware version: " + hex(self.fw_ver) +
                      (" (custom ICP tool, extended commands supported)" if self.supports_extended_cmds else ""))
        # check device id
        if check_for_device:
            dev_id = self.get_device_id()
            if dev_id == 0:
                raise NoDevice("Device not found, please check your connections!")
            if dev_id != N76E003_DEVID:
                raise NoDevice("Unsupported device ID: " + hex(dev_id))

    def close(self):
        if self.ser and self.ser.is_open:
            if self._connected:
                self._disconnect()
            self.ser.close()

    def reinit(self, retry=True, check_fw=True):
        self.close()
        self.init(retry=retry, check_fw=check_fw)

    def get_device_id(self) -> int:
        self._fail_if_not_init()
        _, rx = self.send_cmd(self._cmd_packet(CMD_GET_DEVICEID))
        return (rx[9] << 8) + rx[8]

    def get_cid(self):
        self._fail_if_not_init()
        self._fail_if_not_extended()
        _, rx = self.send_cmd(self._cmd_packet(CMD_GET_CID))
        return rx[8]

    def get_uid(self):
        self._fail_if_not_init()
        self._fail_if_not_extended()
        _, rx = self.send_cmd(self._cmd_packet(CMD_GET_UID))
        return (rx[10] << 16) + (rx[9] << 8) + rx[8]

    def get_ucid(self):
        self._fail_if_not_init()
        self._fail_if_not_extended()
        _, rx = self.send_cmd(self._cmd_packet(CMD_GET_UCID))
        return (rx[11] << 24) + (rx[10] << 16) + (rx[9] << 8) + rx[8]

    def read_config(self):
        self._fail_if_not_init()
        _, rx = self.send_cmd(self._cmd_packet(CMD_READ_CONFIG))
        return ConfigFlags(rx[8:13])

    def erase_aprom(self):
        self._fail_if_not_init()
        _, rx = self.send_cmd(self._cmd_packet(CMD_ERASE_ALL), 1)

    def mass_erase(self, _reconnect=True):
        self._fail_if_not_init()
        self._fail_if_not_icp_bridge()
        cid = self.get_cid()
        success, rx = self.send_cmd(self._cmd_packet(CMD_ISP_MASS_ERASE), 1, fail_on_checksum_error=False)
        if not success:
            raise Exception("Mass erase failed!")
        # need to reentry after erase if the chip was previously locked
        if _reconnect and (cid == 0xFF or cid == 0x00):
            self._disconnect()
            time.sleep(self.open_wait)
            self._connect()

    def get_device_info(self):
        self._fail_if_not_init()
        if self.supports_extended_cmds:
            return DeviceInfo(self.get_device_id(),  self.get_uid(), self.get_cid(), self.get_ucid())
        else:
            return DeviceInfo(self.get_device_id())

    def page_erase(self, addr):
        self._fail_if_not_init()
        self._fail_if_not_extended()
        cmd = bytes([CMD_ISP_PAGE_ERASE]) + bytes(7) + bytes([addr & 0xff, (addr >> 8) & 0xff])
        return self.send_cmd(self._cmd_packet(cmd))

    def read_flash(self, addr, len) -> bytes:
        self._fail_if_not_init()
        self.seq_num = self.seq_num + 1
        cmd = bytes([CMD_READ_ROM]) + bytes(7) + bytes([addr & 0xff, (addr >> 8) & 0xff]) + \
            bytes(2) + bytes([0x00, 0x30]) + bytes(2) + bytes([0x00, 0x30]) + bytes(PACKSIZE-18)
        return self.send_cmd(cmd)

    def update_flash(self, addr, data, size, update_dataflash=False):
        self._fail_if_not_init()
        flen = size
        ipos = 0
        cmd_name = CMD_UPDATE_APROM
        if update_dataflash:
            self._fail_if_not_icp_bridge()
            cmd_name = CMD_UPDATE_DATAFLASH
        cmd = bytes([cmd_name]) + bytes(7) + bytes([addr & 0xff, (addr >> 8) & 0xff]) + \
            bytes(2) + bytes([flen & 0xff, (flen >> 8) & 0xff]) + \
            bytes(2) + bytes(data[0:48])

        # Program first block of 48 bytes
        if update_dataflash:
            self.send_cmd(cmd, 1)
        else:
            self.send_cmd(cmd)
        ipos += 48
        while (ipos <= flen):
            self.update_progress_bar("Programming Rom", ipos, flen)
            # Program remaing blocks (56 byte)
            if ((ipos + 56) < flen):
                cmd = bytes(8) + bytes(data[ipos:ipos+56])
            else:
                # Last block
                cmd = bytes(8) + bytes(data[ipos:flen]) + bytes(56-(flen-ipos))
            self.send_cmd(cmd)
            ipos += 56
        self.update_progress_bar("Programming Rom", flen, flen)

    def write_flash(self, addr, data) -> bool:
        self._fail_if_not_init()
        self.update_flash(addr, data, len(data), False)

    def update_progress_bar(self, name, step, total):
        self._fail_if_not_init()
        if not self.silent:
            progress_bar(name, step, total)

    def dump_flash(self) -> bytes:
        self._fail_if_not_init()
        self._fail_if_not_extended()
        addr = APROM_ADDR
        step_size = DUMP_DATA_SIZE
        data = bytes()
        while (addr < FLASH_SIZE):
            self.update_progress_bar("Dumping...", addr, FLASH_SIZE)
            # Give initial cmd time to dump entire rom
            if addr == APROM_ADDR:
                _, rx = self.send_cmd(self._cmd_packet(CMD_DUMP_ROM), 1)
            else:
                _, rx = self.send_cmd(self._cmd_packet(0))

            min = PACKSIZE-step_size
            max = PACKSIZE if (addr + step_size <=
                               FLASH_SIZE) else FLASH_SIZE - addr + min
            data += rx[min:max]
            addr += step_size
        return data

    def dump_flash_to_file(self, read_file) -> bool:
        self._fail_if_not_init()
        self._fail_if_not_extended()
        f = open(read_file, "wb")
        if (f == None):
            print("Error opening file!")
            return False
        f.write(self.dump_flash())
        return True

    def write_config(self, config: ConfigFlags):
        self._fail_if_not_init()
        self.seq_num = self.seq_num + 1
        pkt = bytes([CMD_UPDATE_CONFIG]) + bytes(3) + bytes([self.seq_num & 0xff, (self.seq_num >> 8)
                                                            & 0xff]) + bytes(2) + config.to_bytes() + config.to_bytes() + bytes(PACKSIZE-18)
        self.send_cmd(pkt)

    @staticmethod
    def check_ldrom_size(size) -> bool:
        if size > LDROM_MAX_SIZE:
            return False
        if size % 1024 != 0:
            return False
        return True

    def _check_ldrom_config(self, config: ConfigFlags, ldrom_size, ldrom_data=None, override=True) -> tuple[ConfigFlags, bytes]:
        if config.get_ldrom_size() != ldrom_size:
            self.print_vb("WARNING: LDROM size does not match config: %d KB vs %d KB" % (
                ldrom_size / 1024, config.get_ldrom_size_kb()))
            if override:
                self.print_vb("Overriding LDROM size in config.")
                config.set_ldrom_size(ldrom_size)
            else:
                if not (ldrom_data is None):
                    if len(ldrom_data) < config.get_ldrom_size():
                        self.print_vb("LDROM will be padded with 0xFF.")
                        ldrom_data = ldrom_data + \
                            bytes(
                                [0xFF] * (config.get_ldrom_size() - len(ldrom_data)))
                    else:
                        self.print_vb("LDROM will be truncated.")
                        ldrom_data = ldrom_data[: config.get_ldrom_size()]
                else:
                    raise Exception("Configuration error! LDROM size does not match config.")
        if config.is_ldrom_boot() != True and ldrom_size > 0:
            eprint("WARNING: LDROM boot flag not set in config")
            if override:
                eprint("Overriding LDROM boot in config.")
                config.set_ldrom_boot(True)
            else:
                # eprint("LDROM will not be bootable with this config!")
                raise Exception("Configuration error! LDROM is not bootable with this config!")
        return config, ldrom_data

    def _check_config(self, prev_config, curr_config=None, ldrom_data=None, override=True, _lock=False) -> tuple[ConfigFlags, bytes]:
        ldrom_size = 0
        if not (ldrom_data is None):
            if len(ldrom_data) > 0:
                ldrom_size = len(ldrom_data)
                if not self.check_ldrom_size(ldrom_size):
                    raise Exception("ERROR: Invalid LDROM size. Not programming...")
                else:
                    if not curr_config:  # No config, set defaults
                        curr_config = prev_config
                        curr_config.set_ldrom_size(ldrom_size)
                        curr_config.set_ldrom_boot(True)
                        curr_config.set_lock(_lock)
            else:  # LDROM = 0 size, which means it is getting blown out
                ldrom_data = bytes()
                ldrom_size = 0
                if curr_config is None:
                    curr_config = prev_config
                    curr_config.set_ldrom_size(0)
                    curr_config.set_ldrom_boot(False)
                    curr_config.set_lock(_lock)
        else:  # No ldrom data, leave as is
            ldrom_data = None
            ldrom_size = prev_config.get_ldrom_size()
            if curr_config is None:
                curr_config = prev_config
                curr_config.set_lock(_lock)
        curr_config, ldrom_data = self._check_ldrom_config(curr_config, ldrom_size, ldrom_data, override)
        if ldrom_data is None:
            ldrom_data = bytes()
        return curr_config, ldrom_data

    def program_data(self, aprom_data, ldrom_data=None, config: ConfigFlags = None, ldrom_config_override=True, verify_flash=None, _lock=False) -> bool:
        self._fail_if_not_init()
        update_flashrom = False
        read_config = self.read_config()
        cid = self.get_cid()
        if (read_config.is_locked() or cid == 0xFF):
            if not self.is_icp_bridge:
                raise Exception("ERROR: Device is locked and cannot override. Not programming...")
            elif ldrom_data is None:
                raise Exception("ERROR: Device is locked; must provide LDROM data to overwrite. Not programming...")
        if not (ldrom_data is None):
            if not self.is_icp_bridge:
                raise ExtendedCmdsNotSupported("Programming the LDROM is only supported when using the ICP bridge.")
            update_flashrom = True
        write_config: ConfigFlags
        write_config, ldrom_data = self._check_config(read_config, config, ldrom_data, ldrom_config_override, _lock)

        aprom_size = write_config.get_aprom_size()
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

        combined_data = aprom_data + ldrom_data
        self.print_vb("Programming Rom (%d KB)..." % (len(combined_data) / 1024))
        if not update_flashrom:
            self.erase_aprom()
        self.update_flash(APROM_ADDR, combined_data, len(combined_data), update_flashrom)
        self.write_config(write_config)

        self.print_vb("ROM programmed.")
        if verify_flash is None:
            verify_flash = self.supports_extended_cmds
        if verify_flash:
            self._fail_if_not_extended()
            self.print_vb("Verifying ROM data...")
            if not self.verify_flash(combined_data, report_unmatched_bytes=True, rom_size=len(combined_data)):
                self.print_vb("Verification failed.")
                return False
            self.print_vb("ROM data verified.")
            # check that the config was really written correctly (do this AFTER verifying the flash because the device may be locked after programming)
            self._disconnect()
            self._connect()
            new_config = self.read_config()
            if str(new_config) != str(write_config):
                eprint("Config verification failed.")
                if not self.silent:
                    self.print_vb("Expected:")
                    write_config.print_config()
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
            write_config.print_config()
        self.print_vb("Finished programming!\n")
        return True

    def program(self, write_file, ldrom_file=None, config: ConfigFlags = None, ldrom_override=True, _no_ldrom=False, _lock=False) -> bool:
        """
        Program the device with the given files and config.
        ------



        If ldrom_file is not specified, the LDROM will not be updated.
        If config is not specified, the default config for the given aprom and ldrom files will be used.
        If ldrom_override is False, the chosen configuration will not be overridden.


        """
        self._fail_if_not_init()
        try:
            wf = open(write_file, "rb")
        except OSError as e:
            eprint("Could not open %s for reading." % write_file)
            raise e

        lf = None
        ldrom_data = None
        if _no_ldrom:
            ldrom_data = bytes()
        else:
            if ldrom_file:
                try:
                    lf = open(ldrom_file, "rb")
                except OSError as e:
                    eprint("Could not open %s for reading." % ldrom_file)
                    raise e

            if lf:
                ldrom_data = lf.read()
                lf.close()

        aprom_data = wf.read()
        wf.close()

        return self.program_data(aprom_data, ldrom_data, config, ldrom_override, _lock=_lock)

    def verify_flash(self, data, report_unmatched_bytes=False, addr=APROM_ADDR, rom_size=FLASH_SIZE) -> bool:
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
        read_data = self.dump_flash()
        if read_data == None:
            return False
        read_data = read_data[addr:rom_size]

        if len(read_data) > len(data):
            return False
        result = True
        byte_errors = 0
        for i in range(len(read_data)):
            if read_data[i] != data[i]:
                if not report_unmatched_bytes:
                    return False
                result = False
                byte_errors += 1
        if not result:
            eprint("Verification failed. %d byte errors." % byte_errors)
        return result


def print_usage():
    print("nuvoispy, an ISP flasher for the Nuvoton N76E003")
    print("written by Steve Markgraf <steve@steve-m.de>\n")
    print("Usage:")
    print("\t[-h, --help:                       print this help]")
    print("\t[-p, --port=<port>                 serial port to use (default: /dev/ttyACM0 on *nix, COM1 on windows)]")
    print("\t[-b, --baud=<baudrate>             baudrate to use (default: 115200)]")
    print("\t[-u, --status:                     print the connected device info and configuration and exit.]")
    print("\t[-r, --read=<filename>             read entire flash to file]")
    print("\t[-w, --write=<filename>            write file to APROM")
    print("\t[-l, --ldrom=<filename>            write file to LDROM (if supported by ISP programmer)]")
    print("\t[-n, --no-ldrom                    Overwrite LDROM space with full-size APROM (if supported by ISP programmer)]")
    print("\t[-k, --lock                        lock the chip after programming (default: False)]")
    print("\t[-c, --config <filename>           use config file for writing (overrides --lock)]")
    print("\t[-s, --silent                      silence all output except for errors]")


def main() -> int:
    argv = sys.argv[1:]
    try:
        opts, _ = getopt.getopt(argv, "hp:b:ur:w:l:sc:nk", [
                                "help", "port=", "baud=", "status", "read=", "write=", "ldrom=", "silent", "config=", "no-ldrom", "lock"])
    except getopt.GetoptError:
        eprint("Invalid command line arguments. Please refer to the usage documentation.")
        print_usage()
        return 2

    port = "/dev/ttyACM0"
    if (platform.system() == "Windows"):
        port = "COM1"
    baud = DEFAULT_SER_BAUD
    config_dump_cmd = False
    read = False
    read_file = ""
    write = False
    write_file = ""
    ldrom_file = None
    config_file = ""
    lock_chip = False
    silent = False
    no_ldrom = False

    brown_out_voltage: float = 2.2
    if len(opts) == 0:
        print_usage()
        return 1
    for opt, arg in opts:
        if opt == "-h" or opt == "--help":
            print_usage()
            return 0
        elif opt == "-p" or opt == "--port":
            port = arg
        elif opt == "-b" or opt == "--baud":
            baud = int(arg)
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
        elif opt == "-s" or opt == "--silent":
            silent = True
        elif opt == "-n" or opt == "--no-ldrom":
            no_ldrom = True
        elif opt == "-k" or opt == "--lock":
            lock_chip = True
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

    # check to see if the files exist before we start the ISP
    for filename in [write_file, ldrom_file, config_file]:
        if filename and not os.path.isfile(filename):
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
    if ldrom_file:
        try:
            # check the length of the ldrom file
            ldrom_size = os.path.getsize(ldrom_file)
            if not NuvoISP.check_ldrom_size(ldrom_size):
                eprint("Error: LDROM file invalid.")
                return 1
        except:
            eprint("Error: Could not read LDROM file")
            return 2

    # setup write config
    write_config = None
    if write and config_file != "":
        write_config = ConfigFlags.from_json_file(config_file)
        if write_config == None:
            eprint("Error: Could not read config file")
            return 1
    try:
        with NuvoISP(serial_port=port, serial_rate=baud, open_wait=1, silent=silent) as nuvo:

            devinfo = nuvo.get_device_info()

            if devinfo.device_id != N76E003_DEVID:
                if devinfo.device_id == 0:
                    eprint("ERROR: Device not found, please check your connections.\n\n")
                    return 2
                eprint(
                    "ERROR: Unsupported device ID: 0x%04X (chip may be locked)\n\n" % devinfo.device_id)
                return 2
            read_config = nuvo.read_config()
            if not read_config:
                eprint("Config read failed!!")
                return 1
            # process commands
            if config_dump_cmd:
                print(devinfo)
                read_config.print_config()
                return 0
            elif read:
                print(devinfo)
                read_config.print_config()
                print()
                if devinfo.cid == 0xFF or read_config.is_locked():
                    eprint("Error: Chip is locked, cannot read flash")
                    return 1
                nuvo.dump_flash_to_file(read_file)
                # remove extension from read_file
                config_file = read_file.rsplit(".", 1)[0] + "-config.json"
                read_config.to_json_file(config_file)
            elif write:
                if not nuvo.program(write_file, ldrom_file, write_config, _no_ldrom=no_ldrom, _lock=lock_chip):
                    eprint("Programming failed!!")
                    return 1
    except KeyboardInterrupt:
        eprint("Cancelled by user!")
        return 3
    except Exception as e:
        raise e

    return 0


try:
    if __name__ == "__main__":
        sys.exit(main())
except Exception as e:
    eprint(e)
    eprint("Exiting...")
    sys.exit(2)
