//#define _DEBUG

#include "icp.h"
#include "pgm.h"
#include "config.h"
#include <Arduino.h>
#include <assert.h>
#include "common/isp_common.h"

#define FW_VERSION          0xE0  // Our own special firmware version to tell our ISP tool we can use our custom commands

#ifndef BUILTIN_LED
#define BUILTIN_LED LED_BUILTIN
#endif


#ifdef ARDUINO_AVR_MEGA2560
#define CACHED_ROM_READ 0
#endif

// NOTE: If your sketch ends up being too big to fit on the device, you can try setting CACHED_ROM_READ to 0
#ifndef CACHED_ROM_READ
#define CACHED_ROM_READ 1
#else
#define CACHED_ROM_READ 0
#endif

#define DISCONNECTED_STATE  0
#define COMMAND_STATE       1
#define UPDATING_STATE      2
#define DUMPING_STATE       3

#define _DEBUG 1
int state;
#define XSTR(x) STR(x)
#define STR(x) #x

#ifdef _DEBUG
#pragma message "DEBUG MODE!!!"
#define DEBUG_PRINT(...) icp_outputf(__VA_ARGS__)
#define DEBUG_PRINT_BYTEARR(arr, len) \
  for (int i = 0; i < len; i++) \
    icp_outputf(" %02x", arr[i]); \
  icp_outputf("\n");


static unsigned long usstart_time = 0;
static unsigned long usend_time = 0;
#define TIMER_START usstart_time = pgm_get_time();
#define TIMER_END usend_time = pgm_get_time();
#define PRINT_TIME(funcname) icp_outputf(#funcname " took %lu us\n", usend_time - usstart_time)
#define TIME_FUNCTION(funcname, ...) \
		TIMER_START; \
		funcname(__VA_ARGS__); \
		TIMER_END; \
		DEBUG_PRINT(#funcname " took %lu us\n", usend_time - usstart_time);

// #define TEST_USLEEP 1
#ifdef TEST_USLEEP

void _debug_outputf(const char *s, ...)
{
  char buf[160];
  va_list ap;
  va_start(ap, s);
  vsnprintf(buf, 160, s, ap);
  va_end(ap);
  pgm_print(buf);
}

// #define USLEEP(x) \
// 	TIMER_START; \
// 	if (x > 0) pgm_usleep(x);\
// 	TIMER_END; \
// 	DEBUG_PRINT("USLEEP(%lu) took %lu us\n", x, usend_time - usstart_time);
#define USLEEP(x) \
	if (x > 0) {\
		if (x < 500){\
			pgm_usleep(x);\
		}\
		else { \
			TIMER_START; \
			pgm_usleep(x);\
			TIMER_END; \
			icp_outputf("USLEEP(%lu) took %lu us\n", x, usend_time - usstart_time);\
		}\
	};

void test_usleep() {
#pragma message "Testing usleep"
  for (uint32_t i = 0; i < 500; i+=10){

    USLEEP(i);
  }
  for (uint32_t usec = 1000; usec < 60000; usec+=1000){
    
    uint32_t lusec = usec % 1000;
    uint32_t msec = usec / 1000;
    uint32_t blurgh = 0;
    DEBUG_PRINT("!!!usleep(%u): ", usec);
    DEBUG_PRINT("delaying %u ms, ", msec); 
    DEBUG_PRINT("%u us\n", lusec);
    USLEEP(usec);
  }
}
#endif // TEST_USLEEP

#else // _DEBUG
#define DEBUG_PRINT(...)
#define DEBUG_PRINT_BYTEARR(arr, len)
#endif // _DEBUG


void setup()
{
  Serial.begin(115200);
  pinMode(BUILTIN_LED, OUTPUT);
  digitalWrite(BUILTIN_LED, HIGH);
  state = DISCONNECTED_STATE;

#ifdef _DEBUG
  delay(100);
  Serial2.begin(115200);
  while (!Serial2); // wait for serial port to connect. Needed for native USB port only
  Serial2.println("online");
#ifdef TEST_USLEEP
  test_usleep();
#endif
#ifdef DEBUG_START_PRINT
  icp_init();
  icp_outputf("DEVICEID\t\t\t0x%02x\n", icp_read_device_id());
  icp_outputf("CID\t\t\t0x%02x\n", icp_read_cid());
  icp_outputf("UID\t\t\t0x%024x\n", icp_read_uid());
  icp_outputf("UCID\t\t\t0x%032x\n", icp_read_ucid());
  icp_dump_config();
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
  icp_deinit();
#endif // DEBUG_START_PRINT
#endif // _DEBUG
}


unsigned char pkt[PACKSIZE];
int pktsize = 0;
int g_packno = 0;

void tx_pkt()
{
  g_packno += 1;
  pkt[4] = g_packno & 0xff;
  pkt[5] = (g_packno >> 8) & 0xff;
#ifdef _DEBUG
  icp_outputf("sending packet\n");
  for (int i = 0; i < PACKSIZE; i++)
    icp_outputf(" %02x", pkt[i]);
  icp_outputf("\n");
#endif
  int pktsize = 0;
  while (pktsize < PACKSIZE)
    Serial.write(pkt[pktsize++]);
  DEBUG_PRINT("done sending packet\n");
}

int update_addr = 0x0000;
int update_size = 0;
int preserved_ldrom_sz = 0;

void update(unsigned char* pkt, int len)
{
  int n = len > update_size ? update_size : len;
  DEBUG_PRINT("writing %d bytes to flash at addr 0x%04x\n", n, update_addr);
  update_addr = icp_write_flash(update_addr, n, pkt);
  update_size -= n;
}

#if CACHED_ROM_READ
byte read_buff[FLASH_SIZE];
bool read_buff_valid = false;
#define INVALIDATE_CACHE read_buff_valid = false
#else
#define INVALIDATE_CACHE
#endif

int dump_addr = 0x0000;
int dump_size = 0;

void dump(unsigned char* pkt)
{
  unsigned char * data_buf = pkt + DUMP_DATA_START;
  int n = DUMP_DATA_SIZE > dump_size ? dump_size : DUMP_DATA_SIZE;

  // uint16_t checksum = 0;

#if CACHED_ROM_READ
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
  memcpy(data_buf, &read_buff[dump_addr], n);
  dump_addr += n;
#else
  dump_addr = icp_read_flash(dump_addr, n, pkt);
#endif
  dump_size -= n;
}

uint8_t cid;
uint32_t saved_device_id;

#ifdef _DEBUG
char * cmd_enum_to_string(int cmd)
{
  switch (cmd) {
    case CMD_UPDATE_APROM: return "CMD_UPDATE_APROM";
    case CMD_UPDATE_CONFIG: return "CMD_UPDATE_CONFIG";
    case CMD_READ_CONFIG: return "CMD_READ_CONFIG";
    case CMD_ERASE_ALL: return "CMD_ERASE_ALL";
    case CMD_SYNC_PACKNO: return "CMD_SYNC_PACKNO";
    case CMD_GET_FWVER: return "CMD_GET_FWVER";
    case CMD_RUN_APROM: return "CMD_RUN_APROM";
    case CMD_RUN_LDROM: return "CMD_RUN_LDROM";
    case CMD_CONNECT: return "CMD_CONNECT";
    case CMD_GET_DEVICEID: return "CMD_GET_DEVICEID";
    case CMD_RESET: return "CMD_RESET";
    case CMD_GET_FLASHMODE: return "CMD_GET_FLASHMODE";
    case CMD_UPDATE_WHOLE_ROM: return "CMD_UPDATE_WHOLE_ROM";
    case CMD_WRITE_CHECKSUM: return "CMD_WRITE_CHECKSUM";
    case CMD_RESEND_PACKET: return "CMD_RESEND_PACKET";
    case CMD_READ_ROM: return "CMD_READ_ROM";
    case CMD_GET_UID: return "CMD_GET_UID";
    case CMD_GET_CID: return "CMD_GET_CID";
    case CMD_GET_UCID: return "CMD_GET_UCID";
    case CMD_ISP_PAGE_ERASE: return "CMD_ISP_PAGE_ERASE";
    case CMD_ISP_MASS_ERASE: return "CMD_ISP_MASS_ERASE";
    default: return "UNKNOWN";
  }
}

#endif

void fail_pkt(){
  DEBUG_PRINT("Sending fail packet\n");
  pkt[0] = ~pkt[0];
  pkt[1] = ~pkt[1];
  tx_pkt();
}

bool mass_erase_checked(bool check_device_id = false){
  INVALIDATE_CACHE;
  uint8_t cid = icp_read_cid();
  icp_mass_erase();
  if (cid == 0xFF || cid == 0x00){
    icp_reentry(5000, 1000, 10);
  }
  if (check_device_id){
    uint32_t devid = icp_read_device_id();
    if (devid != N76E003_DEVID){
      icp_reentry(5000, 1000, 10);
      if (devid != N76E003_DEVID) {
        DEBUG_PRINT("Failed to find device after mass erase! failing...\n");
        fail_pkt();
        return false;
      }
    }
  }
  return true;
}

uint8_t LDROM_BUF[LDROM_MAX_SIZE];

void read_config(config_flags *flags) {
  icp_read_flash(CFG_FLASH_ADDR, CFG_FLASH_LEN, (uint8_t *)flags);
}
int get_ldrom_size(config_flags *flags){
  return (flags->LDS < 3 ? 4 : (7 - flags->LDS)) * 1024;
}

int read_ldrom_size() {
  config_flags flags;
  read_config(&flags);
  return get_ldrom_size(&flags);
}

int preserve_ldrom(int update_addr, int update_size, int ldrom_size){
  int current_aprom_size = FLASH_SIZE - ldrom_size;
  int ldrom_addr = APROM_FLASH_ADDR + current_aprom_size;
  // if there's no ldrom or the update to be written will overwrite the ldrom, don't preserve
  if (ldrom_size == 0 || update_addr + update_size > ldrom_addr) {
    preserved_ldrom_sz = 0;
  } else {
    preserved_ldrom_sz = icp_read_flash(ldrom_addr, ldrom_size, LDROM_BUF);
    if (preserved_ldrom_sz != ldrom_size) {
      preserved_ldrom_sz = 0;
      return -1;
    }
  }
  return ldrom_size;
}

void start_dump(int addr, int size, unsigned char * pkt){
  config_flags flags;
  read_config(&flags);
  uint8_t cid = icp_read_cid();
  if (cid == 0xFF || cid == 0x00){
    // attempt reentry if lock bit is unlocked
    if (flags.LOCK == 1) {
      icp_reentry(5000, 1000, 10);
      cid = icp_read_cid(); 
    }
    if (cid == 0xFF || cid == 0x00) {
      DEBUG_PRINT("Device is locked, cannot dump\n");
      DEBUG_PRINT("CID is 0x%02x\n", cid);
      DEBUG_PRINT("LOCK bit = %d (%s)\n", flags.LOCK, flags.LOCK ? "unlocked" : "locked");
      fail_pkt();
      return;
    }
  }
  if (flags.LOCK == 0) {
    DEBUG_PRINT("WARNING: lock bit is locked, but cid indicates still in an unlocked state, attempting dump anyway...\n");
  }

  dump_addr = addr;
  dump_size = size;
  
  dump(pkt);
  if (dump_size > 0)
    state = DUMPING_STATE;
  tx_pkt();
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
    
    if (pktsize < PACKSIZE)
      return;

#ifdef _DEBUGxx
  icp_outputf("received packet: ");
  for (int i = 0; i < PACKSIZE; i++)
    icp_outputf(" %02x", pkt[i]);
  icp_outputf("\n");
#endif
    
    pktsize = 0;
    uint8_t cid;
    uint32_t devid;
    int cmd = pkt[0];
    int seqno = (pkt[5] << 8) | pkt[4];
    int num_read = 0;
    int ldrom_size = 0;
    unsigned short checksum = 0;
    config_flags flags;
    for (int i = 0; i < PACKSIZE; i++)
      checksum += pkt[i];

    DEBUG_PRINT("received %d-byte packet, %s (0x%02x), seqno 0x%04x, checksum 0x%04x\n", PACKSIZE, cmd_enum_to_string(cmd), cmd, seqno, checksum);

    g_packno++;
    pkt[0] = checksum & 0xff;
    pkt[1] = (checksum >> 8) & 0xff;
#if CHECK_SEQUENCE_NO
    if (g_packno != seqno)
    {
      DEBUG_PRINT("seqno mismatch, expected 0x%04x, got 0x%04x\n", g_packno, seqno);
      state = COMMAND_STATE;
      tx_pkt();
      return;
    }
#endif
    if (state == DUMPING_STATE)
    {
      dump(pkt);
      if (dump_size == 0)
        state = COMMAND_STATE;
      tx_pkt();
      return;
    }
    if (state == UPDATING_STATE) {
      update(&pkt[8], SEQ_UPDATE_PKT_SIZE);
      if (update_size == 0) {
        state = COMMAND_STATE;
        if (preserved_ldrom_sz > 0){
          icp_write_flash(APROM_FLASH_ADDR + FLASH_SIZE - preserved_ldrom_sz, preserved_ldrom_sz, LDROM_BUF);
          preserved_ldrom_sz = 0;
        }
      }
      tx_pkt();
      return;
    }
    switch (cmd) {
      case CMD_CONNECT:
        {
        DEBUG_PRINT("CMD_CONNECT\n");
        INVALIDATE_CACHE;
        icp_init(true);
        delayMicroseconds(10);
        tx_pkt();
        digitalWrite(BUILTIN_LED, LOW);
        icp_outputf("Connected!\n");
        } break;
      case CMD_GET_FWVER:
        pkt[8] = FW_VERSION;
        tx_pkt();
        break;
      case CMD_GET_FLASHMODE:
        DEBUG_PRINT("CMD_GET_FLASHMODE\n");
        read_config(&flags);
        if (flags.CBS == 1){
          pkt[8] = APMODE;
        } else {
          pkt[8] = LDMODE;
        }
        tx_pkt();
        break;
      case CMD_SYNC_PACKNO:
      {
        DEBUG_PRINT("CMD_SYNC_PACKNO\n");
#if CHECK_SEQUENCE_NO
        int seqnoCopy = (pkt[9] << 8) | pkt[8];
        if (seqnoCopy != seqno)
        {
          g_packno = -1; // incremented by tx_pkt
        }
        else
#endif
        {
          g_packno = seqno;
        }
        tx_pkt();
      }
      break;
      case CMD_GET_CID:
        {
        DEBUG_PRINT("CMD_GET_CID\n");
        uint8_t id = icp_read_cid();
        DEBUG_PRINT("received cid of 0x%02x\n", id);
        pkt[8] = id;
        tx_pkt();
        } break;
      case CMD_GET_UID:
        {
        icp_read_uid(&pkt[8]);
        DEBUG_PRINT("received uid of ");
        DEBUG_PRINT_BYTEARR(&pkt[8], 12);
        tx_pkt();
        } break;
      case CMD_GET_UCID:
        {
        // __uint128_t id = icp_read_ucid();
        // DEBUG_PRINT("received ucid of 0x%08x\n", id);
        // for (int i = 0; i < 16; i++)
        //   pkt[8 + i] = (id >> (i * 8)) & 0xff;
        icp_read_ucid(&pkt[8]);
        DEBUG_PRINT("received ucid of ");
        DEBUG_PRINT_BYTEARR(&pkt[8], 16);
        tx_pkt();
        } break;
      case CMD_GET_DEVICEID:
        {
        int id = icp_read_device_id();
        DEBUG_PRINT("received device id of 0x%04x\n", id);
        pkt[8] = id & 0xff;
        pkt[9] = (id >> 8) & 0xff;
        tx_pkt();
        } break;
      case CMD_READ_CONFIG:
        DEBUG_PRINT("CMD_READ_CONFIG\n");
        icp_read_flash(CFG_FLASH_ADDR, CFG_FLASH_LEN, &pkt[8]);
        tx_pkt();
        break;
      case CMD_UPDATE_CONFIG:
        DEBUG_PRINT("CMD_UPDATE_CONFIG\n");
        INVALIDATE_CACHE;
        icp_page_erase(CFG_FLASH_ADDR);
        icp_write_flash(CFG_FLASH_ADDR, CFG_FLASH_LEN, &pkt[8]);
        tx_pkt();
        break;
      case CMD_ERASE_ALL: // Erase all only erases the AP ROM, so we have to page erase the APROM area
      {
        DEBUG_PRINT("CMD_ERASE_ALL\n");
        INVALIDATE_CACHE;
        read_config(&flags);
        int ldrom_size = get_ldrom_size(&flags);
        DEBUG_PRINT("ldrom_size: %d\n", ldrom_size);
        DEBUG_PRINT("Erasing %d bytes of APROM\n", FLASH_SIZE - ldrom_size);
        for (int i = 0; i < FLASH_SIZE - ldrom_size; i += PAGE_SIZE){
          icp_page_erase(i);
        }
        tx_pkt();
      } break;
      case CMD_ISP_MASS_ERASE:
        {
        DEBUG_PRINT("CMD_ISP_MASS_ERASE\n");

          INVALIDATE_CACHE;
          if (!mass_erase_checked(false)) break;
          tx_pkt();
        }
        break;
      case CMD_ISP_PAGE_ERASE:
      {
        INVALIDATE_CACHE;
        int addr = (pkt[9] << 8) | pkt[8];
        DEBUG_PRINT("CMD_ISP_PAGE_ERASE (addr: %d)\n", addr);
        icp_page_erase(addr);
        tx_pkt();
      } break;
      case CMD_RUN_APROM:
      case CMD_RUN_LDROM:
      case CMD_RESET:{
        DEBUG_PRINT("exiting from ICP and running aprom...\n");
        INVALIDATE_CACHE;
        icp_exit();
        tx_pkt();
        digitalWrite(BUILTIN_LED, HIGH);
        state = DISCONNECTED_STATE;
      } break;
      case CMD_READ_ROM:
        dump_addr = (pkt[9] << 8) | pkt[8];
        dump_size = (pkt[13] << 8) | pkt[12];
        DEBUG_PRINT("CMD_READ_ROM (addr: %d, size: %d) \n", dump_addr, dump_size);
        start_dump(dump_addr, dump_size, pkt);
        break;

      case CMD_UPDATE_WHOLE_ROM:
        DEBUG_PRINT("CMD_UPDATE_WHOLE_ROM\n");
        INVALIDATE_CACHE;
        preserved_ldrom_sz = 0;
        if (!mass_erase_checked(true)) break;
        update_addr = (pkt[9] << 8) | pkt[8];
        update_size = (pkt[13] << 8) | pkt[12];
        DEBUG_PRINT("flashing %d bytes\n", update_size);
        update(&pkt[16], 48);
        if (update_size > 0)
          state = UPDATING_STATE;
        tx_pkt();
        break;

      case CMD_UPDATE_APROM:
        update_addr = (pkt[9] << 8) | pkt[8];
        update_size = (pkt[13] << 8) | pkt[12];
        DEBUG_PRINT("CMD_UPDATE_APROM (addr: %d, size: %d)\n", update_addr, update_size);
        read_config(&flags);
        cid = icp_read_cid();
        preserved_ldrom_sz = 0;
        // device is locked, we'll need to do a mass erase
        if (flags.LOCK == 0 || cid == 0xFF) {
          // If the update is not the full FLASH_SIZE, we should just fail here
          if (update_size != FLASH_SIZE) {
            DEBUG_PRINT("Device is locked and update size is not equal to the full APROM size, failing\n");
            fail_pkt();
            break;
          }
          if (!mass_erase_checked(true)) break;
        }
        INVALIDATE_CACHE;
        read_config(&flags);
        DEBUG_PRINT("flashing %d bytes\n", update_size);
        update(&pkt[16], 48);
        if (update_size > 0)
          state = UPDATING_STATE;
        tx_pkt();
        break;
      default:
        DEBUG_PRINT("unknown command 0x%02x\n", cmd);
        fail_pkt();
        break;
    }
  }
}
