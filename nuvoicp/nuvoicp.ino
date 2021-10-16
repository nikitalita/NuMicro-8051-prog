#define _DEBUG

#include "icp.h"

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
#define CMD_RESET           0xad

#define DISCONNECTED_STATE  0
#define COMMAND_STATE       1
#define UPDATING_STATE      2
int state;


void setup()
{
  Serial.begin(115200);
  pinMode(BUILTIN_LED, OUTPUT);
  digitalWrite(BUILTIN_LED, HIGH);
  delay(300);

  state = DISCONNECTED_STATE;

#ifdef _DEBUG
  Serial1.begin(115200);
  while (!Serial1); // wait for serial port to connect. Needed for native USB port only
  Serial1.println("online");
#endif

  Serial1.printf("DEVICEID\t\t\t0x%02x\n", icp_read_device_id());
  Serial1.printf("CID\t\t\t0x%02x\n", icp_read_cid());
  Serial1.printf("UID\t\t\t0x%06x\n", icp_read_uid());
  Serial1.printf("UCID\t\t\t0x%08x\n", icp_read_ucid());

  uint8_t cfg[CFG_FLASH_LEN];
  icp_read_flash(CFG_FLASH_ADDR, CFG_FLASH_LEN, cfg);
  int ldrom_size = (7 - (cfg[1] & 0x7)) * 1024;
  Serial1.printf("CONFIG:\t ");
  for (int i=0; i < CFG_FLASH_LEN; i++)
    Serial1.printf("%02x ", cfg[i]);
  Serial1.printf("\n");
  Serial1.printf("MCU Boot select:\t%s\n", cfg[0] & 0x80 ? "APROM" : "LDROM");
  Serial1.printf("LDROM size:\t\t%d Bytes\n", ldrom_size);
  Serial1.printf("APROM size:\t\t%d Bytes\n", FLASH_SIZE - ldrom_size);

  uint8_t buf[16];
  uint16_t addr = 0;
  while (addr < 256) {
    icp_read_flash(addr, sizeof(buf), buf);
    Serial1.printf("%04x: ", addr);
    for (int i = 0; i < sizeof(buf); i++)
      Serial1.printf("%02x ", buf[i]);
    Serial1.printf("\n");
    addr += sizeof(buf);
  }
}


unsigned char pkt[64];
int pktsize = 0;

void tx_pkt()
{
#ifdef _DEBUG
  Serial1.printf("sending packet\n");
  for (int i = 0; i < 64; i++)
    Serial1.printf(" %02x", pkt[i]);
  Serial1.printf("\n");
#endif
  int pktsize = 0;
  while (pktsize < 64)
    Serial.write(pkt[pktsize++]);
#ifdef _DEBUG
  Serial1.printf("done sending packet\n");
#endif
}

int update_addr = 0x0000;
int update_size = 0;

void update(unsigned char* pkt, int len)
{
  int n = len > update_size ? update_size : len;
#ifdef _DEBUG
  Serial1.printf("writing %d bytes to flash at addr 0x%04x\n", n, update_addr);
#endif
  update_addr = icp_write_flash(update_addr, n, pkt);
  update_size -= n;
}

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
    
    if (pktsize < 64)
      return;

#ifdef _DEBUGxx
  Serial1.printf("received packet: ");
  for (int i = 0; i < 64; i++)
    Serial1.printf(" %02x", pkt[i]);
  Serial1.printf("\n");
#endif

    pktsize = 0;

    int cmd = pkt[0];
    int seqno = (pkt[5] << 8) | pkt[4];

    unsigned short checksum = 0;
    for (int i = 0; i < 64; i++)
      checksum += pkt[i];

#ifdef _DEBUG
    Serial1.printf("received 64-byte packet, command 0x%02x, seqno 0x%04x, checksum 0x%04x\n", cmd, seqno, checksum);
#endif

    pkt[0] = checksum & 0xff;
    pkt[1] = (checksum >> 8) & 0xff;

    if (state == UPDATING_STATE) {
      update(&pkt[8], 56);
      if (update_size == 0)
        state = COMMAND_STATE;
      tx_pkt();
      return;
    }

    switch (cmd) {
      case CMD_CONNECT:
        icp_init();
        tx_pkt();
        digitalWrite(BUILTIN_LED, LOW);
        break;
      case CMD_SYNC_PACKNO:
        tx_pkt();
        break;
      case CMD_GET_DEVICEID:
        {
        int id = icp_read_device_id();
#ifdef _DEBUG
        Serial1.printf("received device id of 0x%04x\n", id);
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
        icp_write_flash(CFG_FLASH_ADDR, CFG_FLASH_LEN, &pkt[13]);
        tx_pkt();
        break;
      case CMD_ERASE_ALL:
        icp_mass_erase();
        tx_pkt();
        break;
      case CMD_RUN_APROM:
#ifdef _DEBUG
        Serial1.printf("running aprom\n");
#endif
        icp_exit();
        tx_pkt();
        break;
      case CMD_UPDATE_APROM:
        update_addr = (pkt[9] << 8) | pkt[8];
        update_size = (pkt[13] << 8) | pkt[12];
#ifdef _DEBUG
        Serial1.printf("flashing %d bytes\n", update_size);
#endif
        update(&pkt[16], 48);
        if (update_size > 0)
          state = UPDATING_STATE;
        tx_pkt();
    }
  }
}
