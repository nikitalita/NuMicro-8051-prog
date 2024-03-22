# NUMicro-8051-prog

This derived from Gregory McGarry's work here: https://github.com/gmcgarry/nuvoprog

This currently only supports the N76E003, but it could be extended to other Nuvoton 8051 chips, like the MS51FB9AE ([see here](https://github.com/vladimir-dudnik/MS51FB9AE-pgm-rpi)).

This provides the following packages:

bootloader: custom ISP bootloader with extended ISP commands
nuvoicp: Custom ICP library and command-line tool
nuvoicpy: Python bindings and command-line tool for nuvoicp (for Raspberry Pi Only)
nuvoispy: Python library and command-line tool for ISP programming


### build requirements:
- sdcc
- make
- build-essential (or your distro's equivalent)
- pigpio
- libgpiod
- python3
- python3-pip
- Arduino IDE (if building nuvoicp for Arduino)

### Raspberry Pi 5 note

If you plan to use the ICP programmer with the Pi 5, ensure that `pcie_aspm=off` is added to `/boot/firmware/cmdline.txt`. This will increase power consumption if you are using an NVME drive, but this will ensure that there are no random delays added to GPIO ops which will result in a failed flash write.

## bootloader

### Build:
Just run `make` in the bootloader directory

## nuvoicp

This is designed for both the Raspberry Pi and Arduino targets.

Raspberry Pi can be compiled linked with either pigpio or libgpiod.
pigpio was added primarily because it has around 10x lower latency than libgpiod, which is useful for glitching attacks.
Note: pigpio only supports Pi 4 and lower, Pi 5 can only be used with libgpiod.

The Arduino version implements the ISP protocol, and acts like a regular ISP programmer with extended functionality. It can be used with `nuvoispy`.

### Build

#### Raspberry Pi:

For libgpiod:
```bash
make -f Makefile.rpi
```

For pigpio:
```bash
USE_PIGPIO=1 make -f Makefile.rpi
```

For Arduino, use the Arduino IDE and open the `nuvoicp.ino` file.

### nuvoicpy

These are python bindings for the Raspberry Pi compiled versions of `nuvoicp`. It also provides a command-line ICP programmer.
This could possibly be repurposed for other SBCs with the appropriate GPIO, but this requires implementing a device file for the GPIO in `nuvoicp` (look at `n51_pgm.h` for details). 

This is compatible with both pigpio and libgpiod, and can be changed at runtime by passing the library name in to the NuvoICP constructor.

NOTE: If you want to run nuvoprogpy with pigpio, you have to either run python as root, or set the following on your python binary:
```bash
sudo chgrp kmem $non_syslink_python_binary_path
sudo setcap cap_sys_rawio,cap_dac_override+eip $non_syslink_python_binary_path
```
and make sure that you are in the `kmem` group.


#### Install:

Just run `pip install -e .`

### nuvoispy

This is a python library and command-line tool for programming the APROM with the ISP protocol.

This is compatible with the official N76E003 ISP ROM, and is ALSO compatible with the Arduino-built versions of `nuvoicp`, which implement the ISP protocol.

NOTE: Right now, the two packages are joined together in the same package, which requires having both libgpiod and pigpiod installed regardless of whether or not you are going to use `nuvoicp`. Someone please tell me how to seperate these elegantly.

#### Install:

Just run `pip -e install .`