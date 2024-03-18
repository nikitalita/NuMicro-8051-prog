/**COMMANDS**/
// Standard commands
#define CMD_UPDATE_APROM         0xa0
#define CMD_UPDATE_CONFIG        0xa1
#define CMD_READ_CONFIG          0xa2
#define CMD_ERASE_ALL            0xa3
#define CMD_SYNC_PACKNO          0xa4
#define CMD_GET_FWVER            0xa6
#define CMD_RUN_APROM            0xab
#define CMD_CONNECT              0xae
#define CMD_GET_DEVICEID         0xb1
#define CMD_RESET                0xad  // not implemented in default N76E003 ISP rom
#define CMD_GET_FLASHMODE        0xCA  // not implemented in default N76E003 ISP rom
#define CMD_RUN_LDROM            0xac  // not implemented in default N76E003 ISP rom
#define CMD_FORMAT2_CONTINUATION 0x00 // not explicitly in the spec, but it's the command(s) sent after an initial CMD_UPDATE_APROM

// Not implemented yet
#define CMD_RESEND_PACKET        0xFF  // not implemented in default N76E003 ISP rom

// Extended commands
#define CMD_READ_ROM             0xa5 // non-official
#define CMD_GET_UID              0xb2 // non-official
#define CMD_GET_CID              0xb3 // non-official
#define CMD_GET_UCID             0xb4 // non-official
#define CMD_GET_BANDGAP          0xb5 // non-official
#define CMD_ISP_PAGE_ERASE       0xD5 // non-official

// Arduino ISP-to-ICP bridge only
#define CMD_UPDATE_WHOLE_ROM     0xE1 // non-official
#define CMD_ISP_MASS_ERASE       0xD6 // non-official

// ** Unsupported by N76E003 **
// Dataflash commands (when a chip has the ability to deliniate between data and program flash)
#define CMD_UPDATE_DATAFLASH     0xC3
// SPI flash commands
#define CMD_ERASE_SPIFLASH       0xD0
#define CMD_UPDATE_SPIFLASH      0xD1
// CAN commands
#define CAN_CMD_READ_CONFIG      0xA2000000
#define CAN_CMD_RUN_APROM        0xAB000000
#define CAN_CMD_GET_DEVICEID     0xB1000000

// Deprecated, no ISP programmer uses these
#define CMD_READ_CHECKSUM        0xC8
#define CMD_WRITE_CHECKSUM       0xC9
#define CMD_SET_INTERFACE        0xBA

// The modes returned by CMD_GET_FLASHMODE
#define APMODE 1
#define LDMODE 2


// N76E003 device constants
#define N76E003_DEVID	    0x3650
#define APROM_FLASH_ADDR	0x0
#define CFG_FLASH_ADDR		0x30000
#define CFG_FLASH_LEN		5
#define LDROM_MAX_SIZE      (4 * 1024)
#define PAGE_SIZE            128 // flash page size
#define FLASH_SIZE	        (18 * 1024)
#define FLASH_PAGE_COUNT FLASH_SIZE/PAGE_SIZE

// packet constants
#define PKT_CMD_START     0
#define PKT_CMD_SIZE      4
#define PKT_SEQ_START     4
#define PKT_SEQ_SIZE      4
#define PKT_HEADER_END    8

#define PACKSIZE           64

#define INITIAL_UPDATE_PKT_START 16 // PKT_HEADER_END + 8 bytes for addr and len
#define INITIAL_UPDATE_PKT_SIZE  48

#define SEQ_UPDATE_PKT_START   PKT_HEADER_END
#define SEQ_UPDATE_PKT_SIZE    56

#define DUMP_PKT_CHECKSUM_START  PKT_HEADER_END
#define DUMP_PKT_CHECKSUM_SIZE   0 // disabled for now
#define DUMP_DATA_START          PKT_HEADER_END //(DUMP_PKT_CHECKSUM_START + DUMP_PKT_CHECKSUM_SIZE)
#define DUMP_DATA_SIZE           56  //(PACKSIZE - DUMP_DATA_START)

#define CHECK_SEQUENCE_NO 0 // TODO: turn this on when we know the sequence number is working