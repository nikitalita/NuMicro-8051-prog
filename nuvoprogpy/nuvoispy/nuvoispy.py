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
from config import *

CMD_UPDATE_APROM = 0xa0
CMD_UPDATE_CONFIG = 0xa1
CMD_READ_CONFIG = 0xa2
CMD_ERASE_ALL = 0xa3
CMD_SYNC_PACKNO = 0xa4
CMD_READ_ROM = 0xa5
CMD_DUMP_ROM = 0xaa
CMD_GET_FWVER = 0xa6
CMD_RUN_APROM = 0xab
CMD_CONNECT = 0xae
CMD_DISCONNECT = 0xaf

CMD_GET_DEVICEID = 0xb1
CMD_GET_UID = 0xb2
CMD_GET_CID = 0xb3
CMD_GET_UCID = 0xb4

SER_BAUD = 115200
SER_TIMEOUT = 0.025  # 25ms
PACKSIZE = 64

seq_num = 0
ser: serial.Serial = 0


def progress_bar(text, value, endvalue, bar_length=54):
    percent = float(value) / endvalue
    arrow = '-' * int(round(percent * bar_length)-1) + '>'
    spaces = ' ' * (bar_length - len(arrow))

    print("\r{0}: [{1}] {2}%".format(text, arrow +
          spaces, int(round(percent * 100))), end='\r')


def verify_chksum(tx, rx):
    txsum = 0
    for i in range(len(tx)):
        txsum += tx[i]

    txsum &= 0xffff
    rxsum = (rx[1] << 8) + rx[0]

    return (rxsum == txsum)


def cmd_packet(cmd):
    global seq_num
    seq_num = seq_num + 1
    return bytes([cmd]) + bytes(3) + bytes([seq_num & 0xff, (seq_num >> 8) & 0xff]) + bytes(PACKSIZE-6)


def send_cmd(tx, timeout=SER_TIMEOUT):
    # todo: only have 5 retries
    sent = False
    retries = 0
    while not sent:
        try:
            ser.write(tx)
            sent = True
        except serial.SerialTimeoutException:
            print("Timeout sending packet, retrying...")
            retries = retries + 1
            if (retries > 5):
                print("Too many retries, aborting!")
                raise TimeoutError
            time.sleep(timeout)

    tries = 0

    while True:
        time.sleep(timeout)
        nbytes = ser.in_waiting

        if (nbytes < PACKSIZE):
            tries = tries + 1
            if (tries > 5):
                print("Re-sending packet!")
                ser.write(tx)
            continue

        rx = ser.read(PACKSIZE)

        if (len(rx) != PACKSIZE):
            continue
        else:
            if not verify_chksum(tx, rx):
                print("Invalid checksum received!")
                raise ChecksumError

            break

    return rx


class NoDevice(Exception):
    pass


class ChecksumError(Exception):
    pass


def reopen_serial(wait: float):
    ser.close()
    time.sleep(0.5)
    ser.open()
    print("Reconnecting...")
    time.sleep(wait)
    disconnect()  # in case the device does not reset on opening serial and we're still connected
    time.sleep(0.5)


def connect_req():
    connected = False

    time.sleep(SER_TIMEOUT)
    connect_retries = 0
    send_retries = 0
    while not connected:
        cmd = cmd_packet(CMD_CONNECT)
        ser.write(cmd)
        time.sleep(0.5)

        read_retries = 0

        while (ser.in_waiting != PACKSIZE):
            time.sleep(SER_TIMEOUT)
            read_retries += 1
            if read_retries * SER_TIMEOUT >= 0.5:
                break

        if ser.in_waiting != PACKSIZE:
            ser.read(ser.in_waiting)
            send_retries += 1
            if connect_retries == 3:
                raise NoDevice
            # the device likely reset on opening serial and we didn't wait long enough, try again
            if send_retries == 2:
                connect_retries += 1
                send_retries = 0
                reopen_serial(connect_retries * 2)
            continue

        rx = ser.read(ser.in_waiting)

        if verify_chksum(cmd, rx):
            print("Got valid reply")
            connected = True


def disconnect():
    cmd = cmd_packet(CMD_RUN_APROM)
    ser.write(cmd)
    time.sleep(SER_TIMEOUT)
    rx = ser.read(PACKSIZE)


def get_deviceid():
    rx = send_cmd(cmd_packet(CMD_GET_DEVICEID))
    return (rx[9] << 8) + rx[8]


def get_cid():
    rx = send_cmd(cmd_packet(CMD_GET_CID))
    return rx[8]


def get_uid():
    rx = send_cmd(cmd_packet(CMD_GET_UID))
    return (rx[10] << 16) + (rx[9] << 8) + rx[8]


def get_ucid():
    rx = send_cmd(cmd_packet(CMD_GET_UCID))
    return (rx[11] << 24) + (rx[10] << 16) + (rx[9] << 8) + rx[8]


def read_config():
    rx = send_cmd(cmd_packet(CMD_READ_CONFIG))
    return rx[13:18]


def update_config(config: ConfigFlags):
    global seq_num
    seq_num = seq_num + 1
    pkt = bytes([CMD_UPDATE_CONFIG]) + bytes(3) + bytes([seq_num & 0xff, (seq_num >> 8)
                                                         & 0xff]) + bytes(2) + config.to_bytes() + config.to_bytes() + bytes(PACKSIZE-18)
    send_cmd(pkt)


def read_flash(addr, size):
    cmd = bytes([CMD_READ_ROM]) + bytes(7) + bytes([addr & 0xff, (addr >> 8) & 0xff]) + \
        bytes(2) + bytes([0x00, 0x30]) + bytes(2) + \
        bytes([0x00, 0x30]) + bytes(PACKSIZE-18)
    return send_cmd(cmd)


def dump_flash(filename):
    f = open(filename, "wb")
    if (f == None):
        print("Error opening file!")
        return False
    addr = APROM_ADDR
    step_size = 56
    while (addr < FLASH_SIZE):
        progress_bar("Dumping APROM", addr, FLASH_SIZE)
        cmd = cmd_packet(CMD_DUMP_ROM)
        # Give initial cmd time to dump entire rom
        if addr == APROM_ADDR:
            rx = send_cmd(cmd, 1)
        else:
            rx = send_cmd(cmd)

        # debug print rx packet
        # print("rx: ", end='')
        # hex_string = ""
        # for i in range(len(rx)):
        # 	hex_string += ("%02x " % rx[i])
        # print(hex_string)
        min = PACKSIZE-step_size
        max = PACKSIZE if (addr + step_size <=
                           FLASH_SIZE) else FLASH_SIZE - addr + min
        f.write(rx[min:max])
        addr += step_size
    f.close()
    return True


def update_flash(addr, filename, size):
    f = open(filename, "rb")  # nuvoton_n76e003_sdcc/main.bin
    data = bytes(f.read())
    flen = size
    ipos = 0

    cmd = bytes([CMD_UPDATE_APROM]) + bytes(7) + bytes([addr & 0xff, (addr >> 8) & 0xff]) + \
        bytes(2) + bytes([flen & 0xff, (flen >> 8) & 0xff]) + \
        bytes(2) + bytes(data[0:48])

    # Program first block of 48 bytes
    send_cmd(cmd)
    ipos += 48
    while (ipos <= flen):
        progress_bar("Programming APROM", ipos, flen)
        # Program remaing blocks (56 byte)
        if ((ipos + 56) < flen):
            cmd = bytes(8) + bytes(data[ipos:ipos+56])
        else:
            # Last block
            cmd = bytes(8) + bytes(data[ipos:flen]) + bytes(56-(flen-ipos))
        send_cmd(cmd)
        ipos += 56
    progress_bar("Programming APROM", flen, flen)


def print_usage():
    print("nuvoisy, an ISP flasher for the Nuvoton N76E003")
    print("written by Steve Markgraf <steve@steve-m.de>\n")
    print("Usage:")
    print("\t[-h print this help]")
    print("\t[-p <port>       serial port to use (default: /dev/ttyUSB0 on *nix, COM1 on windows)]")
    print("\t[-c              print chip configuration and exit]")
    print("\t[-r <filename>   read entire flash to file]")
    print("\t[-w <filename>   write file to APROM/entire flash (if LDROM is disabled)]")
    print(
        "\t[-l <filename>   write file to LDROM, enable LDROM, enable boot from LDROM]")
    print("\t[-s              lock the chip after writing]")
    print(
        "\t[-a <secs> 		  wait <secs> seconds after opening serial port (default: 0)]")
    # print("\t[-b <voltage>    set brown-out voltage (default: 2.2V)]")


def parse_args():
    # parse args
    try:
        opts, args = getopt.getopt(
            sys.argv[1:], "hp:cr:l:w:sa:", ["help", "port="])
    except getopt.GetoptError as err:
        print(err)
        print_usage()
        sys.exit(2)

    filename = ""
    read = False
    write = False
    ldrom_file = ""
    lock = False
    config = False
    port = None
    wait = 0
    for o, a in opts:
        if o == "-h":
            print_usage()
            sys.exit()
        elif o == "-c":
            config = True
        elif o == "-r":
            read = True
            filename = a
        elif o == "-w":
            write = True
            filename = a
        elif o == "-l":
            ldrom_file = a
        elif o == "-s":
            lock = True
        elif o == "-p":
            port = a
        elif o == "-a":
            wait = int(a)
        else:
            assert False, "unhandled option"

    if (not config and not read and not write):
        if ldrom_file != "":
            print("Error: -l requires -w")
        else:
            print("Error: no action specified")
        print_usage()
        sys.exit(2)
    if (read and write):
        print("Error: -r and -w are mutually exclusive")
        print_usage()
        sys.exit(2)

    return (config, read, write, ldrom_file, lock, filename, port, wait)


def erase_flash():
    send_cmd(cmd_packet(CMD_ERASE_ALL))
    # need to reentry after erase if the chip was previously locked
    if (get_cid() == 0xFF):
        disconnect()
        time.sleep(SER_TIMEOUT)
        connect_req()


def get_device_info():
    dev_id = get_deviceid()
    cid = get_cid()
    uid = get_uid()
    ucid = get_ucid()
    return (dev_id, cid, uid, ucid)


def print_device_info(dev_id, cid, uid, ucid):
    print("Device ID: 0x%02x" % dev_id)
    print("CID:       0x%02x" % cid)
    print("UID:       0x%02x" % uid)
    print("UCID:      0x%02x" % ucid)


def write_flash(filename, ldrom_file, lock: bool):
    config = ConfigFlags()

    if not os.path.isfile(filename):
        print("Error: File not found")
        sys.exit(2)
    aprom_size = os.path.getsize(filename)
    if (aprom_size > FLASH_SIZE):
        print("Error: APROM file too big")
        sys.exit(2)
    elif (aprom_size == 0):
        print("Error: APROM file could not be opened for reading")
        sys.exit(2)

    ldrom_size = 0
    if ldrom_file != "":
        # get file size of ldrom_file
        if not os.path.isfile(ldrom_file):
            print("Error: LDROM file not found")
            return False

        ldrom_size = os.path.getsize(ldrom_file)
        if (ldrom_size > LDROM_MAX_SIZE):
            print("Error: LDROM file too big")
            sys.exit(2)
        if (ldrom_size % 1024 != 0 or ldrom_size == 0):
            print("Error: LDROM file size must be multiple of 1024")
            return False

    erase_flash()
    dev_id, cid, uid, ucid = get_device_info()
    print_device_info(dev_id, cid, uid, ucid)
    if (dev_id != N76E003_DEVID):
        print("Error: Unsupported device ID, expected 0x%02x" % N76E003_DEVID)
        return False

    if ldrom_size > 0:
        config.enable_ldrom(int(ldrom_size / 1024))
        update_config(config)
        update_flash(FLASH_SIZE - ldrom_size, ldrom_file, ldrom_size)
    else:
        update_config(config)
    update_flash(APROM_ADDR, filename, FLASH_SIZE - ldrom_size)

    # todo: verify
    if lock:
        config.set_lock(True)  # lock chip
        update_config(config)
    config.print_config()
    return True


def main():
    global ser

    config_cmd, read_cmd, write_cmd, ldrom_file, lock, filename, port, wait = parse_args()

    if not port:
        if (platform.system() == "Windows"):
            port = "COM1"
        else:
            port = "/dev/ttyUSB0"

    ser = serial.Serial(port, SER_BAUD, timeout=SER_TIMEOUT)

    if (not ser.is_open):
        print("Error: Could not open Serial port")
        return

    print("Connected to serial port...")
    time.sleep(wait)
    print("Trying to connect to MCU, please press reset button")
    disconnect()
    time.sleep(SER_TIMEOUT)
    connect_req()
    send_cmd(cmd_packet(CMD_SYNC_PACKNO))
    print("Connected!")

    dev_id, cid, uid, ucid = get_device_info()
    config_bytes = read_config()
    config = ConfigFlags(config_bytes)

    if (get_deviceid() == N76E003_DEVID):
        print('Found N76E003')
    elif cid == 0xFF and write_cmd:
        print(
            "N76E003 not found (may be locked), do you want to attempt to mass erase? (y/N)")
        # get input from keyboard
        if (input().lower() != 'y'):
            print_device_info(dev_id, cid, uid, ucid)
            disconnect()
            ser.close()
            raise NoDevice
    else:
        print_device_info(dev_id, cid, uid, ucid)
        disconnect()
        ser.close()
        raise NoDevice

    error = False
    if not write_cmd:
        print_device_info(dev_id, cid, uid, ucid)
        config.print_config()
    if read_cmd and not config_cmd:
        if config.is_locked() or cid == 0xFF:
            print("Error: Chip is locked, cannot read")
            error = True
        else:
            print("Reading flash...")
            error = not dump_flash(filename)
    elif write_cmd and not config_cmd:
        print("Writing flash...")
        error = not write_flash(filename, ldrom_file, lock)
    disconnect()
    ser.close()

    if (error == True):
        sys.exit(2)
    print("\nDone.")


if __name__ == '__main__':
    try:
        main()
    except NoDevice:
        print("N76E003 not found (chip may be locked)")

    # ser.close()
