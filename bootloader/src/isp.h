#define CMD_UPDATE_APROM    0xa0
#define CMD_UPDATE_CONFIG   0xa1
#define CMD_READ_CONFIG     0xa2
#define CMD_ERASE_ALL       0xa3
#define CMD_SYNC_PACKNO     0xa4
#define CMD_GET_FWVER       0xa6
#define CMD_RUN_APROM       0xab
#define CMD_CONNECT         0xae
#define CMD_GET_DEVICEID    0xb1

#define CMD_RESET            0xad  // not implemented in default N76E003 ISP rom
#define CMD_GET_FLASHMODE    0xCA  // not implemented in default N76E003 ISP rom
#define CMD_RUN_LDROM        0xac   // not implemented in default N76E003 ISP rom

#define CMD_READ_ROM        0xa5 // non-official
#define CMD_DUMP_ROM        0xaa // non-official
#define CMD_GET_UID         0xb2 // non-official
#define CMD_GET_CID         0xb3 // non-official
#define CMD_GET_UCID        0xb4 // non-official

#define CMD_ISP_PAGE_ERASE      0xD5 // non-official

// probably won't implement these
#define CMD_WRITE_CHECKSUM   0xC9  // not implemented in default N76E003 ISP rom
#define CMD_RESEND_PACKET    0xFF  // not implemented in default N76E003 ISP rom

// Arduino ISP-to-ICP bridge only
#define CMD_UPDATE_DATAFLASH    0xC3  // not implemented in default N76E003 ISP rom
#define CMD_ISP_MASS_ERASE      0xD6 // non-official


#define APMODE 1
#define LDMODE 2
