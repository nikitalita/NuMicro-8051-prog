#define TRUE       1
#define FALSE     0


// IAP commands: IAPCN values
// IAPB: 7:6
// FOEN: 5
// FOEN: 4
// FCTRL: 3:0
#define PAGE_ERASE_AP        0x22 // 00:1:0:0010
#define BYTE_READ_AP         0x00 // 00:0:0:0000
#define BYTE_PROGRAM_AP      0x21 // 00:1:0:0001
#define BYTE_READ_ID         0x0C // 00:0:0:1100
#define PAGE_ERASE_CONFIG    0xE2 
#define BYTE_READ_CONFIG     0xC0
#define BYTE_PROGRAM_CONFIG  0xE1
#define READ_UID             0x04
#define PAGE_ERASE_LD        0x62
#define BYTE_PROGRAM_LD      0x61
#define BYTE_READ_LD         0x40
#define READ_CID             0x0B // 00:0:0:1100
