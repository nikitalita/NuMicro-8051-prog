
from nuvoprogpy.nuvo51icpy import Nuvo51ICP
from nuvoprogpy.config import *
from nuvoprogpy.nuvoispy.nuvoispy import NuvoISP

# with Nuvo51ICP() as nuvo:
with NuvoISP(serial_port="/dev/ttyAMA0", open_wait=1) as nuvo:
    # open testfiles/GPIO-new_dump_plus_LDROM.bin
    config = nuvo.read_config()
    ldrom_data = nuvo.dump_flash(16*1024, 2048)
    compare_file = open("bootloader/out/bootloader.bin", "rb")
    ldrom_compare_data = compare_file.read()
    compare_file.close()
    ldrom_compare_data = ldrom_compare_data + bytes([0xFF] * (config.get_ldrom_size() - len(ldrom_compare_data)))

    if len(ldrom_compare_data) != len(ldrom_data):
        raise Exception("File size mismatch")
    for i in range(len(ldrom_compare_data)):
        if ldrom_compare_data[i] != ldrom_data[i]:
            raise Exception("Data mismatch at %d" % i)

    rom_data = nuvo.dump_flash()
    compare_file = open("testfiles/doamp-icp.bin", "rb")
    compare_data = compare_file.read()
    compare_file.close()
    compare_data = compare_data + bytes([0xFF] * (config.get_ldrom_size() - len(compare_data)))

    if len(compare_data) != len(rom_data):
        raise Exception("File size mismatch")
    for i in range(len(compare_data)):
        if compare_data[i] != rom_data[i]:
            raise Exception("Data mismatch at %d" % i)
