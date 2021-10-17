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


import sys
import serial
import time

SER_TIMEOUT			= 0.05		# 50ms
PACKSIZE			= 64
N76E003_DEVID		= 0x3650

CMD_UPDATE_APROM	= 0xa0
CMD_UPDATE_CONFIG	= 0xa1
CMD_READ_CONFIG		= 0xa2
CMD_ERASE_ALL		= 0xa3
CMD_SYNC_PACKNO		= 0xa4
CMD_GET_FWVER		= 0xa6
CMD_RUN_APROM		= 0xab
CMD_CONNECT			= 0xae
CMD_GET_DEVICEID	= 0xb1

APROM_ADDR			= 0
LDROM_ADDR			= 16 * 1024

seq_num = 0
ser = 0

def progress_bar(text, value, endvalue, bar_length=54):
	percent = float(value) / endvalue
	arrow = '-' * int(round(percent * bar_length)-1) + '>'
	spaces = ' ' * (bar_length - len(arrow))

	print("\r{0}: [{1}] {2}%".format(text, arrow + spaces, int(round(percent * 100))), end='\r')

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

def send_cmd(tx):
	# todo: only have 5 retries
	ser.write(tx)
	tries = 0

	while True:
		time.sleep(SER_TIMEOUT)
		nbytes = ser.inWaiting()

		if (nbytes < PACKSIZE):
			tries = tries + 1
			if (tries > 5):
#				print("Re-sending packet!")
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

def connect_req():
	connected = False
	# todo: timeout

	while not connected:
		cmd = cmd_packet(CMD_CONNECT)
		ser.write(cmd)
		time.sleep(SER_TIMEOUT)

		nbytes = ser.inWaiting()
		rx = ser.read(nbytes)

		if (nbytes != PACKSIZE):
			continue

		if verify_chksum(cmd, rx):
				print("Got valid reply")
				connected = True

def get_deviceid():
	rx = send_cmd(cmd_packet(CMD_GET_DEVICEID))
	return (rx[9] << 8) + rx[8]

def boot_ldrom():
	global seq_num
	seq_num = seq_num + 1
	config = bytes([ 0x7f, 0xfd, 0xff, 0xff, 0xff ])
	pkt = bytes([CMD_UPDATE_CONFIG]) + bytes(3) + bytes([seq_num & 0xff, (seq_num >> 8) & 0xff]) + bytes(2) + config + config + bytes(PACKSIZE-18)
	send_cmd(pkt)

def update_flash(addr, filename):
	f = open(filename, "rb") #nuvoton_n76e003_sdcc/main.bin
	data = bytes(f.read())
	flen = f.tell()
	ipos = 0

	cmd = bytes([CMD_UPDATE_APROM]) + bytes(7) + bytes([addr & 0xff, (addr >> 8) & 0xff]) + bytes(2) + bytes([flen & 0xff, (flen >> 8) & 0xff]) + bytes(2) + bytes(data[0:48])

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

def main():
	global ser

	if (len(sys.argv) < 2):
		print("Usage: ./nuvoispy.py filename.bin [/dev/ttyUSBx]")
		exit()

	if (len(sys.argv) < 3):
		port = "/dev/ttyUSB0"
	else:
		port = sys.argv[2]

	ser = serial.Serial(port, 115200, timeout=SER_TIMEOUT)

	if (not ser.isOpen()):
		return

	print("Trying to connect to MCU, please press reset button")
	connect_req()
	send_cmd(cmd_packet(CMD_SYNC_PACKNO))
	if (get_deviceid() == N76E003_DEVID):
		print('Found N76E003')
	else:
		raise NoDevice

	if True:
		send_cmd(cmd_packet(CMD_ERASE_ALL))
		boot_ldrom()
		update_flash(LDROM_ADDR, sys.argv[1])
	else:
		update_flash(APROM_ADDR, sys.argv[1])
	send_cmd(cmd_packet(CMD_RUN_APROM))
	print("\nDone.")

	ser.close()

if __name__ == '__main__':
	try:
		main()

	except NoDevice:
		print("Incorrect device found")

	ser.close()

