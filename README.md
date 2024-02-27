# nuvoprog

This is a port of Steve Markgraf's excellent N76 programming tools to the Arduino platform.  See Steve's original work here: https://github.com/steve-m/N76E003-playground

Tested on: Lolin(WeMOS) D1 mini @ 80MHz: 1 cycle = 12.5ns
	DAT:   D1
	CLK:   pinD2
	RST:   D3

NOTE: If you want to run nuvoprogpy with pigpio, you have to either run python as root, or set the following on your python binary

```bash
sudo chgrp kmem $non_syslink_python_binary_path
sudo setcap cap_sys_rawio,cap_dac_override+eip $non_syslink_python_binary_path
```