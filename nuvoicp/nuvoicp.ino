//#define _DEBUG

#include "icp.h"
#include "config.h"

#define FW_VERSION          0xE0  // Our own special firmware version to tell our ISP tool we can use our custom commands

#define CMD_UPDATE_APROM    0xa0
#define CMD_UPDATE_CONFIG   0xa1
#define CMD_READ_CONFIG     0xa2
#define CMD_ERASE_ALL       0xa3
#define CMD_SYNC_PACKNO     0xa4
#define CMD_GET_FWVER       0xa6
#define CMD_RUN_APROM       0xab
#define CMD_RUN_LDROM       0xac
#define CMD_CONNECT         0xae

#define CMD_GET_DEVICEID    0xb1

#define CMD_RESET           0xad   // not implemented in default N76E003 ISP rom

#define CMD_GET_FLASHMODE    0xCA  // not implemented in default N76E003 ISP rom
#define CMD_UPDATE_DATAFLASH 0xC3  // not implemented in default N76E003 ISP rom
#define CMD_WRITE_CHECKSUM   0xC9  // not implemented in default N76E003 ISP rom
#define CMD_RESEND_PACKET    0xFF  // not implemented in default N76E003 ISP rom

#define CMD_READ_ROM        0xa5 // non-official
#define CMD_DUMP_ROM        0xaa // non-official
#define CMD_GET_UID         0xb2 // non-official
#define CMD_GET_CID         0xb3 // non-official
#define CMD_GET_UCID        0xb4 // non-official


#ifndef BUILTIN_LED
#define BUILTIN_LED LED_BUILTIN
#endif

#define DISCONNECTED_STATE  0
#define COMMAND_STATE       1
#define UPDATING_STATE      2
#define DUMPING_STATE       3

#define PACKSIZE           64
#define UPDATE_PKT_SIZE    56
#define DUMP_PKT_SIZE      56


#define APMODE 1
#define LDMODE 2
int state;


void setup()
{
  Serial.begin(115200);
  pinMode(BUILTIN_LED, OUTPUT);
  digitalWrite(BUILTIN_LED, HIGH);
  state = DISCONNECTED_STATE;

#ifdef _DEBUG
  delay(100);
  Serial1.begin(115200);
  while (!Serial1); // wait for serial port to connect. Needed for native USB port only
  Serial1.println("online");

  icp_outputf("DEVICEID\t\t\t0x%02x\n", icp_read_device_id());
  icp_outputf("CID\t\t\t0x%02x\n", icp_read_cid());
  icp_outputf("UID\t\t\t0x%06x\n", icp_read_uid());
  icp_outputf("UCID\t\t\t0x%08x\n", icp_read_ucid());
#ifdef PRINT_CONFIG_EN
  icp_dump_config();
#endif
  uint8_t buf[16];
  uint16_t addr = 0;
  while (addr < 256) {
    icp_read_flash(addr, sizeof(buf), buf);
    icp_outputf("%04x: ", addr);
    for (int i = 0; i < sizeof(buf); i++)
      icp_outputf("%02x ", buf[i]);
    icp_outputf("\n");
    addr += sizeof(buf);
  }
#endif
}


unsigned char pkt[PACKSIZE];
int pktsize = 0;

void tx_pkt()
{
#ifdef _DEBUG
  icp_outputf("sending packet\n");
  for (int i = 0; i < PACKSIZE; i++)
    icp_outputf(" %02x", pkt[i]);
  icp_outputf("\n");
#endif
  int pktsize = 0;
  while (pktsize < PACKSIZE)
    Serial.write(pkt[pktsize++]);
#ifdef _DEBUG
  icp_outputf("done sending packet\n");
#endif
}

int update_addr = 0x0000;
int update_size = 0;

void update(unsigned char* pkt, int len)
{
  int n = len > update_size ? update_size : len;
#ifdef _DEBUG
  icp_outputf("writing %d bytes to flash at addr 0x%04x\n", n, update_addr);
#endif
  update_addr = icp_write_flash(update_addr, n, pkt);
  update_size -= n;
}

// TODO: Remove this for MCUs with smaller RAMs
#ifndef ARDUINO_AVR_MEGA2560
#define CACHED_ROM_READ 1
#endif
#ifdef CACHED_ROM_READ
byte read_buff[FLASH_SIZE];
bool read_buff_valid = false;
#endif

int dump_addr = 0x0000;
int dump_size = 0;

void dump(unsigned char* pkt, int len)
{
  int n = len > dump_size ? dump_size : len;

#ifdef CACHED_ROM_READ
  // hack to make reads faster
  if (!read_buff_valid) {
    // we're going to read the entire thing into memory
    int read_addr = 0;
    // dump x bytes at a time
#define READ_CHUNK FLASH_SIZE
    for (read_addr = 0; read_addr < FLASH_SIZE; read_addr += READ_CHUNK){
      icp_read_flash(read_addr, READ_CHUNK, &read_buff[read_addr]);
      delayMicroseconds(1);
    }
    read_buff_valid = true;
  }
  memcpy(pkt, &read_buff[dump_addr], n);
  dump_addr += n;
#else
  dump_addr = icp_read_flash(dump_addr, n, pkt);
#endif
  dump_size -= n;
}

uint8_t saved_cid;
uint32_t saved_device_id;
void loop()
{
  if (Serial.available()) {

    pkt[pktsize] = Serial.read();

    if (state == DISCONNECTED_STATE) {
      if (pkt[0] != CMD_CONNECT)
        return;
      state = COMMAND_STATE;
    }
    
    pktsize++;
    
    if (pktsize < PACKSIZE)
      return;

#ifdef _DEBUGxx
  icp_outputf("received packet: ");
  for (int i = 0; i < PACKSIZE; i++)
    icp_outputf(" %02x", pkt[i]);
  icp_outputf("\n");
#endif

    pktsize = 0;

    int cmd = pkt[0];
    int seqno = (pkt[5] << 8) | pkt[4];
    int num_read = 0;
    unsigned short checksum = 0;
    for (int i = 0; i < PACKSIZE; i++)
      checksum += pkt[i];

#ifdef _DEBUG
    icp_outputf("received %d-byte packet, command 0x%02x, seqno 0x%04x, checksum 0x%04x\n", PACKSIZE, cmd, seqno, checksum);
#endif

    pkt[0] = checksum & 0xff;
    pkt[1] = (checksum >> 8) & 0xff;

    if (state == DUMPING_STATE) {
      dump(&pkt[8], DUMP_PKT_SIZE);
      if (dump_size == 0)
        state = COMMAND_STATE;
      tx_pkt();
      return;
    }
    if (state == UPDATING_STATE) {
      update(&pkt[8], UPDATE_PKT_SIZE);
      if (update_size == 0)
        state = COMMAND_STATE;
      tx_pkt();
      return;
    }
    switch (cmd) {
      case CMD_CONNECT:
        {
        icp_init(true);
        delayMicroseconds(10);
        saved_device_id = icp_read_device_id();
        saved_cid = icp_read_cid();
        tx_pkt();
        digitalWrite(BUILTIN_LED, LOW);
        }
        break;
      case CMD_GET_FWVER:
        pkt[8] = FW_VERSION;
        tx_pkt();
        break;
      case CMD_GET_FLASHMODE:
        config_flags flags;
        icp_read_flash(CFG_FLASH_ADDR, CFG_FLASH_LEN, (uint8_t *)&flags);
        if (flags.CBS == 1){
          pkt[8] = APMODE;
        } else {
          pkt[8] = LDMODE;
        }
        tx_pkt();
        break;
      case CMD_SYNC_PACKNO:
        tx_pkt();
        break;
      case CMD_GET_CID:
        {
        int id = icp_read_cid();
#ifdef _DEBUG
        icp_outputf("received device id of 0x%04x\n", id);
#endif
        pkt[8] = id & 0xff;
        tx_pkt();
        }
        break;
      case CMD_GET_UID:
        {
        int id = icp_read_uid();
#ifdef _DEBUG
        icp_outputf("received device id of 0x%04x\n", id);
#endif
        pkt[8] = id & 0xff;
        pkt[9] = (id >> 8) & 0xff;
        pkt[10] = (id >> 16) & 0xff;
        tx_pkt();
        }
        break;
      case CMD_GET_UCID:
        {
        int id = icp_read_ucid();
#ifdef _DEBUG
        icp_outputf("received device id of 0x%04x\n", id);
#endif
        pkt[8] = id & 0xff;
        pkt[9] = (id >> 8) & 0xff;
        pkt[10] = (id >> 16) & 0xff;
        pkt[11] = (id >> 24) & 0xff;
        tx_pkt();
        }
        break;
      case CMD_GET_DEVICEID:
        {
        int id = icp_read_device_id();
#ifdef _DEBUG
        icp_outputf("received device id of 0x%04x\n", id);
#endif
        pkt[8] = id & 0xff;
        pkt[9] = (id >> 8) & 0xff;
        tx_pkt();
        }
        break;
      case CMD_READ_CONFIG:
        icp_read_flash(CFG_FLASH_ADDR, CFG_FLASH_LEN, &pkt[13]);
        tx_pkt();
        break;
      case CMD_UPDATE_CONFIG:
        icp_page_erase(CFG_FLASH_ADDR);
        icp_write_flash(CFG_FLASH_ADDR, CFG_FLASH_LEN, &pkt[13]);
        tx_pkt();
        break;
      case CMD_ERASE_ALL:
      {
#ifdef CACHED_ROM_READ
        read_buff_valid = false;
#endif
        icp_mass_erase();
        tx_pkt();
      }
        break;
      case CMD_RUN_APROM:
      case CMD_RUN_LDROM:
      case CMD_RESET:
#ifdef _DEBUG
        icp_outputf("running aprom\n");
#endif
#ifdef CACHED_ROM_READ
        read_buff_valid = false;
#endif

        icp_exit();
        tx_pkt();
        digitalWrite(BUILTIN_LED, HIGH);
        state = DISCONNECTED_STATE;
        break;
      case CMD_DUMP_ROM:
        dump_addr = APROM_FLASH_ADDR;
        dump_size = FLASH_SIZE;
        state = DUMPING_STATE;
        dump(&pkt[8], DUMP_PKT_SIZE);
        tx_pkt();
        break;
      case CMD_READ_ROM:
        dump_addr = (pkt[9] << 8) | pkt[8];
        dump_size = (pkt[13] << 8) | pkt[12];
        num_read = icp_read_flash(update_addr, update_size, &pkt[16]);
        if (dump_size > 0)
          state = DUMPING_STATE;
        tx_pkt();
        break;
      case CMD_UPDATE_APROM:
        #ifdef CACHED_ROM_READ
        read_buff_valid = false;
        #endif

        update_addr = (pkt[9] << 8) | pkt[8];
        update_size = (pkt[13] << 8) | pkt[12];
#ifdef _DEBUG
        icp_outputf("flashing %d bytes\n", update_size);
#endif
        update(&pkt[16], 48);
        if (update_size > 0)
          state = UPDATING_STATE;
        tx_pkt();
    }
  }
}
