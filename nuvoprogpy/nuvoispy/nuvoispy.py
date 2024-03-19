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
import math

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

# Standard commands
CMD_UPDATE_APROM      =  0xa0
CMD_UPDATE_CONFIG     =  0xa1
CMD_READ_CONFIG       =  0xa2
CMD_ERASE_ALL         =  0xa3
CMD_SYNC_PACKNO       =  0xa4
CMD_GET_FWVER         =  0xa6
CMD_RUN_APROM         =  0xab
CMD_CONNECT           =  0xae
CMD_GET_DEVICEID      =  0xb1
CMD_RESET             =  0xad  # not implemented in default N76E003 ISP rom
CMD_GET_FLASHMODE     =  0xCA  # not implemented in default N76E003 ISP rom
CMD_RUN_LDROM         =  0xac  # not implemented in default N76E003 ISP rom

# Not implemented yet
CMD_RESEND_PACKET     =  0xFF  # not implemented in default N76E003 ISP rom

# Extended commands
CMD_READ_ROM          =  0xa5 # non-official
CMD_GET_UID           =  0xb2 # non-official
CMD_GET_CID           =  0xb3 # non-official
CMD_GET_UCID          =  0xb4 # non-official
CMD_GET_BANDGAP       =  0xb5 # non-official
CMD_ISP_PAGE_ERASE    =  0xD5 # non-official

# Arduino ISP-to-ICP bridge only
CMD_UPDATE_WHOLE_ROM  =  0xE1 # non-official
CMD_ISP_MASS_ERASE    =  0xD6 # non-official

# ** Unsupported by N76E003 **
# Dataflash commands (when a chip has the ability to deliniate between data and program flash)
CMD_UPDATE_DATAFLASH  =  0xC3
# SPI flash commands
CMD_ERASE_SPIFLASH    =  0xD0
CMD_UPDATE_SPIFLASH   =  0xD1
# CAN commands
CAN_CMD_READ_CONFIG   =  0xA2000000
CAN_CMD_RUN_APROM     =  0xAB000000
CAN_CMD_GET_DEVICEID  =  0xB1000000

CMD_FORMAT2_CONTINUATION = 0 # update and dump require this

# Deprecated, no ISP programmer uses these
CMD_READ_CHECKSUM     =  0xC8
CMD_WRITE_CHECKSUM    =  0xC9
CMD_SET_INTERFACE     =  0xBA

# The modes returned by CMD_GET_FLASHMODE
APMODE = 1
LDMODE = 2

CHECK_SEQUENCE_NO = False # turn this on when we know it's working

EXTENDED_CMDS_FW_VER = 0xD0
ICP_BRIDGE_FW_VER = 0xE0

PKT_CMD_START = 0
PKT_CMD_SIZE = 4
PKT_SEQ_START = 4
PKT_SEQ_SIZE = 4
PKT_HEADER_END = 8
PACKSIZE = 64
SEQ_UPDATE_PKT_SIZE = 56

DUMP_PKT_CHECKSUM_START = PKT_HEADER_END
DUMP_PKT_CHECKSUM_SIZE = 0  # disabled for now
DUMP_DATA_START = (DUMP_PKT_CHECKSUM_START + DUMP_PKT_CHECKSUM_SIZE)
DUMP_DATA_SIZE = (PACKSIZE - DUMP_DATA_START)

DEFAULT_SER_BAUD = 115200
DEFAULT_SER_TIMEOUT = 0.01  # 10ms

DEFAULT_UNIX_PORT = "/dev/ttyAMA0"
DEFAULT_WIN_PORT = "COM1"

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

def cmd_to_str(cmd):
    if cmd == CMD_UPDATE_APROM:
        return "CMD_UPDATE_APROM"
    elif cmd == CMD_UPDATE_CONFIG:
        return "CMD_UPDATE_CONFIG"
    elif cmd == CMD_READ_CONFIG:
        return "CMD_READ_CONFIG"
    elif cmd == CMD_ERASE_ALL:
        return "CMD_ERASE_ALL"
    elif cmd == CMD_SYNC_PACKNO:
        return "CMD_SYNC_PACKNO"
    elif cmd == CMD_GET_FWVER:
        return "CMD_GET_FWVER"
    elif cmd == CMD_RUN_APROM:
        return "CMD_RUN_APROM"
    elif cmd == CMD_CONNECT:
        return "CMD_CONNECT"
    elif cmd == CMD_GET_DEVICEID:
        return "CMD_GET_DEVICEID"
    elif cmd == CMD_RESET:
        return "CMD_RESET"
    elif cmd == CMD_GET_FLASHMODE:
        return "CMD_GET_FLASHMODE"
    elif cmd == CMD_RUN_LDROM:
        return "CMD_RUN_LDROM"
    elif cmd == CMD_RESEND_PACKET:
        return "CMD_RESEND_PACKET"
    elif cmd == CMD_READ_ROM:
        return "CMD_READ_ROM"
    elif cmd == CMD_GET_UID:
        return "CMD_GET_UID"
    elif cmd == CMD_GET_CID:
        return "CMD_GET_CID"
    elif cmd == CMD_GET_UCID:
        return "CMD_GET_UCID"
    elif cmd == CMD_GET_BANDGAP:
        return "CMD_GET_BANDGAP"
    elif cmd == CMD_ISP_PAGE_ERASE:
        return "CMD_ISP_PAGE_ERASE"
    elif cmd == CMD_UPDATE_WHOLE_ROM:
        return "CMD_UPDATE_WHOLE_ROM"
    elif cmd == CMD_ISP_MASS_ERASE:
        return "CMD_ISP_MASS_ERASE"
    elif cmd == CMD_UPDATE_DATAFLASH:
        return "CMD_UPDATE_DATAFLASH"
    elif cmd == CMD_ERASE_SPIFLASH:
        return "CMD_ERASE_SPIFLASH"
    elif cmd == CMD_UPDATE_SPIFLASH:
        return "CMD_UPDATE_SPIFLASH"
    elif cmd == CMD_READ_CHECKSUM:
        return "CMD_READ_CHECKSUM"
    elif cmd == CMD_WRITE_CHECKSUM:
        return "CMD_WRITE_CHECKSUM"
    elif cmd == CMD_SET_INTERFACE:
        return "CMD_SET_INTERFACE"
    elif cmd == CAN_CMD_READ_CONFIG:
        return "CAN_CMD_READ_CONFIG"
    elif cmd == CAN_CMD_RUN_APROM:
        return "CAN_CMD_RUN_APROM"
    elif cmd == CAN_CMD_GET_DEVICEID:
        return "CAN_CMD_GET_DEVICEID"
    else:
        return str(0)

def progress_bar(text, value, endvalue, bar_length=54):
    percent = float(value) / endvalue
    arrow = '-' * int(round(percent * bar_length)-1) + '>'
    spaces = ' ' * (bar_length - len(arrow))

    print("\r{0}: [{1}] {2}%".format(text, arrow +
          spaces, int(round(percent * 100))), end='\r')
    

def pack_u16(val):
    return bytes([val & 0xff, (val >> 8) & 0xff])
def pack_u32(val):
    return bytes([val & 0xff, (val >> 8) & 0xff, (val >> 16) & 0xff, (val >> 24) & 0xff])
def unpack_u16(data):
    return (data[0] & 0xff) + ((data[1] & 0xff) << 8)
def unpack_u32(data):
    return (data[0] & 0xff) + ((data[1] & 0xff) << 8) + ((data[2] & 0xff) << 16) + ((data[3] & 0xff) << 24)

def calc_checksum(data):
    txsum = 0
    for i in range(len(data)):
        txsum += data[i]
    return txsum & 0xffff

class ISPPacket:
    seq_num = 0
    _first = 0
    data = bytes()
    def __init__(self, cmd, seqnum=0, data=bytes()):
        self._first = cmd
        self.data = data
        self.seq_num = seqnum
    @staticmethod
    def _pad_packet(pkt_bytes):
        return pkt_bytes + bytes(PACKSIZE - len(pkt_bytes))
    @staticmethod
    def from_bytes(data):
        seq_num = unpack_u32(data[4:8])
        cmd = unpack_u32(data[0:4])
        return ISPPacket(cmd, seq_num, data[8:])
    def to_bytes(self):
        return self._pad_packet(pack_u32(self._first) + pack_u32(self.seq_num) + self.data)
    def _get_checksum(self):
        return calc_checksum(self.to_bytes())
    def _get_cmd(self):
        return self._first
    @property
    def cmd(self):
        return self._get_cmd()
    @property
    def checksum(self):
        return self._get_checksum()
    
class ACKPacket(ISPPacket):
    def _get_cmd(self):
        return 0
    def _get_checksum(self):
        return (self._first & 0xffff)
    @staticmethod
    def from_bytes(data):
        seq_num = unpack_u16(data[4:8])
        cmd = unpack_u16(data[0:2])
        return ACKPacket(cmd, seq_num, data[8:])





    
class NuvoISP(NuvoProg):
    def __init__(self, serial_rate=DEFAULT_SER_BAUD, serial_timeout=DEFAULT_SER_TIMEOUT, serial_port=(DEFAULT_WIN_PORT if platform.system() == "Windows" else DEFAULT_UNIX_PORT), open_wait: float = 0.2, silent=False):
        """
        NuvoISP constructor
        ------

        #### Keyword args:
            serial_rate (int): Serial baud rate
            serial_timeout (float): Serial timeout in seconds
            serial_port (str): Serial port to use (default = "COM1" on Windows, "/dev/serial0" on Linux)
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
            if self.is_serial_open():
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
            if self.is_serial_open():
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
            if self.is_serial_open():
                self.reopen_serial()
            else:
                self.ser.port = value

    def is_serial_open(self):
        return self.ser.is_open

    def get_serial_inwaiting(self):
        return self.ser.in_waiting

    def write_serial(self, data):
        self.ser.write(data)

    def read_serial(self, size=1):
        return self.ser.read(size)

    def close_serial(self):
        self.ser.close()

    def flush_serial(self):
        self.ser.flush()

    def reopen_serial(self):
        SERIAL_CLOSE_WAIT = 0.5
        if not self.ser:
            self.ser = serial.Serial(self.serial_port, self.serial_rate, timeout=self.serial_timeout)
        else:
            if self.is_serial_open():
                self.flush_serial()
                self.close_serial()
                time.sleep(SERIAL_CLOSE_WAIT)
            self.ser = serial.Serial(self.serial_port, self.serial_rate, timeout=self.serial_timeout)
            self.flush_serial()

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
        self.seq_num += 1
        self._send_cmd(cmd)
        # don't bother reading the response
        time.sleep(self.serial_timeout)
        self.flush_serial()
        self._connected = False

    def _cmd_packet(self, cmd, data=bytes()):
        return ISPPacket(cmd, 0, data)

    def _wait_for_packet(self, max_retries, timeout=None, size=PACKSIZE):
        if timeout is None:
            timeout = self.serial_timeout
        retries = 0
        while (self.get_serial_inwaiting() < size):
            if retries > max_retries:
                return False
            retries += 1
            time.sleep(timeout)
        return True

    def _connect_req(self, retry=True):
        time.sleep(self.serial_timeout)
        MAX_CONNECT_RETRIES = 3
        MAX_SEND_RETRIES = 200
        MAX_READ_RETRIES = 5
        connect_retries = 0
        send_retries = 0
        connected = False
        first_wait = self.open_wait if self.open_wait > 0 else 1
        reopen_wait = first_wait
        first_try = True
        while not connected:
            if send_retries > MAX_SEND_RETRIES:
                if not retry or connect_retries == MAX_CONNECT_RETRIES:
                    raise NoDevice("Device not found!")
                connect_retries += 1
                send_retries = 0
                reopen_wait = first_wait * connect_retries
                self.print_vb("Attempting to reconnect... (backoff = {}s)".format(reopen_wait))
                self.reopen_serial()
                time.sleep(reopen_wait)
                # self._disconnect()  # in case the device does not reset on opening serial and we're still connected
                # time.sleep(0.2)
                first_try = True
                self.print_vb("If not using the arduino ICP programmer, hit reset on the chip")
            self.flush_serial()
            self.seq_num = 0
            cmd = self._cmd_packet(CMD_CONNECT)
            send_retries += 1
            self._send_cmd(cmd)
            if first_try:
                first_try = False
                time.sleep(first_wait)
            else:
                time.sleep(self.serial_timeout)

            if not self._wait_for_packet(MAX_READ_RETRIES):
                continue

            if self.get_serial_inwaiting() < PACKSIZE:
                raise ConnectionError("Shouldn't get here")
            rx = self.read_serial(PACKSIZE)
            # we sent too many connection packets or there's preceding garbage on the serial port
            if self.get_serial_inwaiting() > 0:
                read_packet_retry = 5 # in-case the chip is just spewing garbage on the serial port forever
                while self.get_serial_inwaiting():
                    rx += self.read_serial(self.get_serial_inwaiting())
                    read_packet_retry -= 1
                    if read_packet_retry == 0:
                        break
                # get the last 64 bytes
                rx = rx[len(rx)-PACKSIZE:]
            # check all the received packets
            rx_pkt = ACKPacket.from_bytes(rx)
            if cmd.checksum == rx_pkt.checksum:
                # print("Got valid reply")
                connected = True
                # self.print_vb("Received sequence number: " + str(rx_pkt.seq_num))

    def _connect(self, retry=True):
        self._connect_req(retry)
        data = pack_u32(1)
        # ++seq_num when send_cmd is called, so we need to reset it here
        self.seq_num = 0
        success, rx_pkt = self.send_cmd(self._cmd_packet(CMD_SYNC_PACKNO, data))
        if not success or (CHECK_SEQUENCE_NO and rx_pkt.seq_num != 2): 
            raise Exception("Failed to sync sequence number")
        self.fw_ver = self.get_fwver()
        self._connected = True

    def _send_cmd(self, tx: ISPPacket, max_timeout=None):
        tx.seq_num = self.seq_num
        if max_timeout is None:
            max_timeout = self.serial_timeout
        # todo: only have 5 retries
        sent = False
        retries = 0
        MAX_SEND_TRIES = 5
        while not sent:
            try:
                self.write_serial(tx.to_bytes())
                sent = True
            except serial.SerialTimeoutException:
                retries = retries + 1
                if (retries > MAX_SEND_TRIES):
                    raise TimeoutError("Too many retries sending packet, aborting!")
                self.print_vb("Timeout sending packet, retrying...")
                time.sleep(max_timeout)

    def send_cmd(self, tx_pkt: ISPPacket, max_timeout=None, fail_on_checksum_error=True):
        # sequence number increments by 1 for every packet send and every packet receieved
        self.seq_num += 1
        tx_pkt.seq_num = self.seq_num
        # self.print_vb("Sending sequence number: {} ({})".format(tx_pkt.seq_num, cmd_to_str(tx_pkt.cmd)))
        if max_timeout is None:
            max_timeout = self.serial_timeout
        self._send_cmd(tx_pkt, max_timeout)
        tries = 0
        success = True

        # The idea here is that if we set a large max_timeout, we can wait for the entire packet to be received without sleeping for the entire max_timeout
        DEFAULT_MAX_TRIES = 5
        max_read_tries = DEFAULT_MAX_TRIES if (max_timeout <= self.serial_timeout) else (
            DEFAULT_MAX_TRIES * int(math.ceil(max_timeout / self.serial_timeout)))
        # if we have a smaller max timeout, then we sleep for that on every read attempt, otherwise we sleep for the default timeout
        read_timeout = self.serial_timeout if (max_timeout >= self.serial_timeout) else max_timeout
        rx = bytes()
        while True:
            time.sleep(read_timeout)
            nbytes = self.get_serial_inwaiting()

            if (nbytes < PACKSIZE):
                tries += 1
                if (tries > max_read_tries):
                    if CHECK_SEQUENCE_NO:
                        raise TimeoutError("Too many read retries, aborting!")
                    print("Re-sending packet!")
                    self.flush_serial()
                    self._send_cmd(tx_pkt, max_timeout)
                continue
            break
        rx = self.read_serial(PACKSIZE)
        if (len(rx) != PACKSIZE):
            raise Exception("FAILED TO READ FROM SERIAL PORT!")

        rx_pkt = ACKPacket.from_bytes(rx)
        # self.print_vb("Received sequence number: " + str(rx_pkt.seq_num))
        if tx_pkt.checksum != rx_pkt.checksum:
            if fail_on_checksum_error:
                raise ChecksumError("Invalid checksum received!")
            success = False
        elif CHECK_SEQUENCE_NO:
            rseq_num = (rx[4] & 0xff) + ((rx[5] & 0xff) << 8)
            if rseq_num != self.seq_num + 1:
                if fail_on_checksum_error:
                    raise ChecksumError("Invalid sequence number received!")
                success = False
        # sequence number increments by 1 for every packet send and every packet receieved
        self.seq_num += 1
        return success, rx_pkt

    def get_fwver(self):
        _, rx_pkt = self.send_cmd(self._cmd_packet(CMD_GET_FWVER))
        return rx_pkt.data[0]

    def init(self, retry=True, check_for_device=True):
        self.reopen_serial()
        time.sleep(self.open_wait)
        self.print_vb("Connecting on serial port {}...".format(self.serial_port))
        self.print_vb("If not using the arduino ICP programmer, hit reset on the chip")
        self._connect(retry)
        self.print_vb("Connected!")
        revision_string = ""
        if self.is_icp_bridge:
            revision_string = " (Arduino ISP-to-ICP bridge, supports extended commands)"
        elif self.supports_extended_cmds:
            revision_string = " (custom ISP LDROM, supports extended commands)"
        self.print_vb("ISP firmware version: " + hex(self.fw_ver) + revision_string)
        # check device id
        if check_for_device:
            dev_id = self.get_device_id()
            if dev_id == 0:
                raise NoDevice("Device not found, please check your connections!")
            if dev_id != N76E003_DEVID:
                raise NoDevice("Unsupported device ID: " + hex(dev_id))

    def close(self):
        if self.ser and self.is_serial_open():
            if self._connected:
                self._disconnect()
            self.close_serial()

    def reinit(self, retry=True, check_fw=True):
        self.close()
        self.init(retry=retry, check_fw=check_fw)

    def get_device_id(self) -> int:
        self._fail_if_not_init()
        _, rx_pkt = self.send_cmd(self._cmd_packet(CMD_GET_DEVICEID))
        return unpack_u32(rx_pkt.data)

    def get_cid(self) -> int:
        self._fail_if_not_init()
        self._fail_if_not_extended()
        _, rx_pkt = self.send_cmd(self._cmd_packet(CMD_GET_CID))
        return rx_pkt.data[0]

    def get_uid(self):
        self._fail_if_not_init()
        self._fail_if_not_extended()
        _, rx_pkt = self.send_cmd(self._cmd_packet(CMD_GET_UID))
        ret = rx_pkt.data[0:12]
        return ret

    def get_ucid_test(self):
        self._fail_if_not_init()
        self._fail_if_not_extended()
        _, rx_pkt = self.send_cmd(self._cmd_packet(CMD_GET_UCID))
        # return rx[8:44]
        return rx_pkt.data[0:36]

    def get_ucid(self):
        self._fail_if_not_init()
        self._fail_if_not_extended()
        _, rx_pkt = self.send_cmd(self._cmd_packet(CMD_GET_UCID))
        # return rx[8:24]
        return rx_pkt.data[0:16]

    def read_config(self):
        self._fail_if_not_init()
        _, rx_pkt = self.send_cmd(self._cmd_packet(CMD_READ_CONFIG))
        return ConfigFlags(rx_pkt.data[:5])

    def erase_aprom(self):
        self._fail_if_not_init()
        success, rx = self.send_cmd(self._cmd_packet(CMD_ERASE_ALL), 1)
        if not success:
            raise Exception("Erase failed!")

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
        self.send_cmd(self._cmd_packet(CMD_ISP_PAGE_ERASE, bytes([addr & 0xff, (addr >> 8) & 0xff])))

    def update_flash(self, addr, data, size, update_dataflash=False):
        self._fail_if_not_init()
        flen = size
        ipos = 0
        cmd_name = CMD_UPDATE_APROM
        if update_dataflash:
            self._fail_if_not_icp_bridge()
            cmd_name = CMD_UPDATE_WHOLE_ROM
        addr_pckd = pack_u32(addr)
        flen_pckd = pack_u32(flen)
        pkt = self._cmd_packet(cmd_name, addr_pckd + flen_pckd + bytes(data[0:48]))

        # Program first block of 48 bytes (8 second delay because it has to erase the flash first)
        _, rx_pkt = self.send_cmd(pkt, 8)
        ipos += 48
        while (ipos <= flen):
            self.update_progress_bar("Programming Rom", ipos, flen)
            # Program remaing blocks (56 byte)
            if ((ipos + 56) < flen):
                sdata = bytes(data[ipos:ipos+56])
            else:
                # Last block
                sdata = bytes(data[ipos:flen]) + bytes(56-(flen-ipos))
            _, rx_pkt = self.send_cmd(self._cmd_packet(CMD_FORMAT2_CONTINUATION, sdata))
            ipos += 56
        self.update_progress_bar("Programming Rom", flen, flen)
        # check the checksum
        update_checksum = unpack_u16(rx_pkt.data)
        our_checksum = calc_checksum(data)
        if update_checksum != our_checksum:
            # raise ChecksumError("Checksum mismatch: {} != {}".format(update_checksum, our_checksum))
            self.print_vb("WARNING: Checksum mismatch: {} != {}".format(update_checksum, our_checksum))
            return False
        return True

    def write_flash(self, addr, data) -> bool:
        self._fail_if_not_init()
        self.update_flash(addr, data, len(data), False)

    def update_progress_bar(self, name, step, total):
        self._fail_if_not_init()
        if not self.silent:
            progress_bar(name, step, total)

    def dump_flash(self, start_addr=APROM_ADDR, length=FLASH_SIZE) -> bytes:
        self._fail_if_not_init()
        self._fail_if_not_extended()
        step_size = DUMP_DATA_SIZE
        data = bytes()
        first_packet = self._cmd_packet(CMD_READ_ROM, bytes([start_addr & 0xff, (start_addr >> 8) & 0xff]) +
                                        bytes(2) + bytes([length & 0xff, (length >> 8) & 0xff]))
        addr = start_addr
        end_addr = start_addr + length
        while (addr < end_addr):
            self.update_progress_bar("Dumping...", addr, end_addr)
            # Give initial cmd time to dump entire rom
            if addr == start_addr:
                _, rx = self.send_cmd(first_packet, 1)
            else:
                _, rx = self.send_cmd(self._cmd_packet(CMD_FORMAT2_CONTINUATION))

            if (addr + step_size <= end_addr):
                max = len(rx.data) 
            else:
                max = end_addr - addr
            data += rx.data[:max]
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
        pkt = self._cmd_packet(CMD_UPDATE_CONFIG, config.to_bytes() + config.to_bytes())
        self.send_cmd(pkt)

    @staticmethod
    def check_ldrom_size(size) -> bool:
        if size > LDROM_MAX_SIZE:
            return False
        return True
    def _pad_if_necessary(self, data):
        if not data:
            return data
        if len(data) % 1024 != 0:
            data += bytes([0xFF]* (1024 - (len(data) % 1024)))
        return data
    def _check_ldrom_config(self, config: ConfigFlags, ldrom_size, ldrom_data=None, override=True) -> tuple[ConfigFlags, bytes]:
        if config.get_ldrom_size() != ldrom_size:
            self.print_vb("WARNING: LDROM size does not match config: %dB vs %dB" % (
                ldrom_size, config.get_ldrom_size()))
            if config.get_ldrom_size() - len(ldrom_data) < 1024:
                self.print_vb("LDROM will be padded with 0xFF.")
                ldrom_data = ldrom_data + bytes([0xFF] * (config.get_ldrom_size() - len(ldrom_data)))
            elif override:
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
        locked = read_config.is_locked() or cid == 0xFF
        if locked:
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
        # no need to erase, as the update commands will do it for us
        verified_success = self.update_flash(APROM_ADDR, combined_data, len(combined_data), update_flashrom)
        self.write_config(write_config)

        if not verified_success:
            eprint("Device reported incorrect checksum, verification failed!")
            # check if this is locked and the config unlocks it; if so, we should still write the config
            if locked and write_config.is_locked() == False:
                self.print_vb("Writing config anyway to ensure unlocked...")
                self.write_config(write_config)
            return False
        self.print_vb("ROM programmed.")
        if verify_flash is None: # vs. False
            verify_flash = self.supports_extended_cmds
        if verify_flash:
            self._fail_if_not_extended()
            self.print_vb("Verifying ROM data...")
            if not self.verify_flash(combined_data, report_unmatched_bytes=True, rom_size=len(combined_data)):
                self.print_vb("Verification failed.")
                return False
            self.print_vb("ROM data verified.")
            # check that the config was really written correctly (do this AFTER verifying the flash because the device may be locked after programming)
            # self._disconnect()
            # self._connect()
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
            verified_success = True

        self.print_vb("\nResulting Device info:")
        devinfo = self.get_device_info()
        self.print_vb(devinfo)
        self.print_vb()
        if not self.silent:
            write_config.print_config()
        if verified_success:
            self.print_vb("Verification succeeded!")
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

        return self.program_data(aprom_data, ldrom_data, config=config, verify_flash=None, ldrom_config_override=ldrom_override, _lock=_lock)

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
    print("\t[-p, --port=<port>                 serial port to use (default: {} on *nix, {} on windows)]".format(DEFAULT_UNIX_PORT, DEFAULT_WIN_PORT))
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

    port = DEFAULT_UNIX_PORT
    if (platform.system() == "Windows"):
        port = DEFAULT_WIN_PORT
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
            read_file = arg.strip()
        elif opt == "-w" or opt == "--write":
            write_file = arg.strip()
            write = True
        elif opt == "-l" or opt == "--ldrom":
            ldrom_file = arg.strip()
        elif opt == "-c" or opt == "--config":
            config_file = arg.strip()
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
                test = nuvo.get_ucid_test()
                # print as individual bytes
                print(" ".join(["%02X" % b for b in test]))
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
