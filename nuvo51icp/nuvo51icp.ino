//#define _DEBUG
#include <stdint.h>
#include "n51_icp.h"
#include "n51_pgm.h"
#include "config.h"
#include <Arduino.h>
#include <assert.h>
#include "common/isp_common.h"

#define FW_VERSION          0xE0  // Our own special firmware version to tell our ISP tool we can use our custom commands

// We refuse to set configs that have the reset pin disabled and the watchdog timer disabled
// It becomes very, very difficult to re-flash the device if the reset pin is disabled AND it doesn't reset on a periodic basis
#define NO_DANGEROUS_CONFIGS 1

// Change this setting if your target board doesn't have reset set to high by default
// 0: sets Reset pin to high-impedence (i.e. neutral) after programming
// 1: leaves Reset pin high after programming
#define LEAVE_RESET_HIGH 0

#ifdef ARDUINO_AVR_MEGA2560
#define CACHED_ROM_READ 0
#endif
// NOTE: If your sketch ends up being too big to fit on the device, you can try setting CACHED_ROM_READ to 0
#ifndef CACHED_ROM_READ
#define CACHED_ROM_READ 1
#endif
// connection timeout in milliseconds; 0 to disable
#define CONNECTION_TIMEOUT 0

#define DEBUG_VERBOSE 0

#ifndef USING_32BIT_PACKNO
#define USING_32BIT_PACKNO 1
#endif

#ifndef BUILTIN_LED
#define BUILTIN_LED LED_BUILTIN
#endif

#define PAGE_MASK 0xFF80

#define DISCONNECTED_STATE      0
#define CONNECTING_STATE        1
#define WAITING_FOR_CONNECT_CMD 2
#define WAITING_FOR_SYNCNO      3
#define COMMAND_STATE           4
#define UPDATING_STATE          5
#define DUMPING_STATE           6

uint8_t state;
unsigned char rx_buf[PACKSIZE];
unsigned char tx_buf[PACKSIZE];
int rx_bufhead = 0;
uint32_t g_packno = 0;
int update_addr = 0x0000;
uint32_t update_size = 0;
uint16_t g_update_checksum = 0;
int dump_addr = 0x0000;
uint32_t dump_size = 0;
uint8_t cid;
uint32_t saved_device_id;
uint8_t connected = 0;
uint8_t just_connected = 0;
unsigned long last_read_time = 0;
unsigned long curr_time = 0;

#if CACHED_ROM_READ
byte read_buff[FLASH_SIZE];
bool read_buff_valid = false;
uint8_t LDROM_BUF[LDROM_MAX_SIZE];
#define INVALIDATE_CACHE read_buff_valid = false
#else
#define INVALIDATE_CACHE
#endif

#define XSTR(x) STR(x)
#define STR(x) #x

#ifdef _DEBUG
#pragma message "DEBUG MODE!!!"
#define DEBUG_PRINT(...) N51ICP_outputf(__VA_ARGS__)
#define DEBUG_PRINT_BYTEARR(arr, len) \
  for (int i = 0; i < len; i++) \
    N51ICP_outputf(" %02x", (arr)[i]); \
  N51ICP_outputf("\n");


static unsigned long usstart_time = 0;
static unsigned long usend_time = 0;
#define TIMER_START usstart_time = N51PGM_get_time();
#define TIMER_END usend_time = N51PGM_get_time();
#define PRINT_TIME(funcname) N51ICP_outputf(#funcname " took %lu us\n", usend_time - usstart_time)
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
  N51PGM_print(buf);
}

// #define USLEEP(x) \
// 	TIMER_START; \
// 	if (x > 0) N51PGM_usleep(x);\
// 	TIMER_END; \
// 	DEBUG_PRINT("USLEEP(%lu) took %lu us\n", x, usend_time - usstart_time);
#define USLEEP(x) \
	if (x > 0) {\
		if (x < 500){\
			N51PGM_usleep(x);\
		}\
		else { \
			TIMER_START; \
			N51PGM_usleep(x);\
			TIMER_END; \
			N51ICP_outputf("USLEEP(%lu) took %lu us\n", x, usend_time - usstart_time);\
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

// implementation specific
void enable_connect_led(){
  digitalWrite(BUILTIN_LED, HIGH);
}

// implementation specific
void disable_connect_led(){
  digitalWrite(BUILTIN_LED, LOW);
}

// implementation specific
void setup()
{
  Serial.begin(115200);
  pinMode(BUILTIN_LED, OUTPUT);
  disable_connect_led();
  state = DISCONNECTED_STATE;
  memset(rx_buf, (uint8_t)0xFF, PACKSIZE);
  memset(tx_buf, (uint8_t)0xFF, PACKSIZE);

#ifdef _DEBUG
  delay(100);
  Serial2.begin(115200);
  while (!Serial2); // wait for serial port to connect. Needed for native USB port only
  Serial2.println("online");
#ifdef TEST_USLEEP
  test_usleep();
#endif
#ifdef DEBUG_START_PRINT
  N51ICP_init();
  DEBUG_PRINT("DEVICEID\t\t\t0x%02x\n", N51ICP_read_device_id());
  DEBUG_PRINT("CID\t\t\t0x%02x\n", N51ICP_read_cid());
  DEBUG_PRINT("UID\t\t\t0x%024x\n", N51ICP_read_uid());
  DEBUG_PRINT("UCID\t\t\t0x%032x\n", N51ICP_read_ucid());
  uint8_t buf[16];
  uint16_t addr = 0;
  while (addr < 256) {
    N51ICP_read_flash(addr, sizeof(buf), buf);
    DEBUG_PRINT("%04x: ", addr);
    for (int i = 0; i < sizeof(buf); i++)
      DEBUG_PRINT("%02x ", buf[i]);
    DEBUG_PRINT("\n");
    addr += sizeof(buf);
  }
  N51ICP_deinit();
#endif // DEBUG_START_PRINT
#endif // _DEBUG
}



void inc_g_packno(){
  g_packno++;
}

// implementation specific
void tx_pkt()
{
  DEBUG_PRINT("Sending packet...\n");
#if DEBUG_VERBOSE
  for (int i = 0; i < PACKSIZE; i++){
    DEBUG_PRINT(" %02x", tx_buf[i]);
  }
  DEBUG_PRINT("\n");
#endif
  uint8_t pktsize = 0;
  while (pktsize < PACKSIZE)
    Serial.write(tx_buf[pktsize++]);
  DEBUG_PRINT("done sending packet\n");
}

uint16_t get_checksum() {
  uint16_t checksum = 0;
  for (int i = 0; i < PACKSIZE; i++)
    checksum += rx_buf[i];
  return checksum;
}

uint16_t package_checksum() {
  uint16_t checksum = get_checksum();
  tx_buf[0] = checksum & 0xff;
  tx_buf[1] = (checksum >> 8) & 0xff;
  tx_buf[2] = 0;
  tx_buf[3] = 0;
  return checksum;
}

void prep_pkt() {
  // populate header
  package_checksum();
  inc_g_packno();
  tx_buf[4] = g_packno & 0xff;
  tx_buf[5] = (g_packno >> 8) & 0xff;
#ifdef USING_32BIT_PACKNO
  tx_buf[6] = (g_packno >> 16) & 0xff;
  tx_buf[7] = (g_packno >> 24) & 0xff;
#else
  tx_buf[6] = 0;
  tx_buf[7] = 0;
#endif
}

void send_pkt() {
  prep_pkt();
  tx_pkt();
}


void update(unsigned char* data, int len)
{
  int n = len > update_size ? update_size : len;
  DEBUG_PRINT("writing %d bytes to flash at addr 0x%04x\n", n, update_addr);
  update_addr = N51ICP_write_flash(update_addr, n, data);
  // update the checksum
  for (int i = 0; i < n; i++)
    g_update_checksum += data[i];
  update_size -= n;
}


void dump()
{
  unsigned char * data_buf = tx_buf + DUMP_DATA_START;
  int n = DUMP_DATA_SIZE > dump_size ? dump_size : DUMP_DATA_SIZE;

  // uint16_t checksum = 0;

#if CACHED_ROM_READ
  // hack to make reads faster
  if (!read_buff_valid) {
    DEBUG_PRINT("Caching rom...\n");
    // we're going to read the entire thing into memory
    int read_addr = 0;
    // dump x bytes at a time
#define READ_CHUNK FLASH_SIZE
    for (read_addr = 0; read_addr < FLASH_SIZE; read_addr += READ_CHUNK){
      N51ICP_read_flash(read_addr, READ_CHUNK, &read_buff[read_addr]);
      delayMicroseconds(1);
    }
    read_buff_valid = true;
  }
  memcpy(data_buf, &read_buff[dump_addr], n);
  dump_addr += n;
#else
  dump_addr = N51ICP_read_flash(dump_addr, n, data_buf);
#endif
  dump_size -= n;
}


#ifdef _DEBUG
const char * cmd_enum_to_string(int cmd)
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
  prep_pkt();
  tx_buf[0] = ~tx_buf[0];
  tx_buf[1] = ~tx_buf[1];
  tx_pkt();
}

bool mass_erase_checked(bool check_device_id = false){
  INVALIDATE_CACHE;
  uint8_t cid = N51ICP_read_cid();
  N51ICP_mass_erase();
  N51PGM_usleep(500000); // half a second
  if (cid == 0xFF || cid == 0x00){
    N51ICP_reentry(5000, 1000, 10);
  }
  if (check_device_id){
    uint32_t devid = N51ICP_read_device_id();
    if (devid != N76E003_DEVID){
      N51ICP_reentry(5000, 1000, 10);
      if (devid != N76E003_DEVID) {
        DEBUG_PRINT("Failed to find device after mass erase! failing...\n");
        fail_pkt();
        return false;
      }
    }
  }
  return true;
}


void read_config(config_flags *flags) {
  N51ICP_read_flash(CFG_FLASH_ADDR, CFG_FLASH_LEN, (uint8_t *)flags);
}
int get_ldrom_size(config_flags *flags){
  return (flags->LDS < 3 ? 4 : (7 - flags->LDS)) * 1024;
}

int read_ldrom_size() {
  config_flags flags;
  read_config(&flags);
  return get_ldrom_size(&flags);
}

void start_dump(int addr, int size){
  config_flags flags;
  read_config(&flags);
  uint8_t cid = N51ICP_read_cid();
  if (cid == 0xFF || cid == 0x00){
    // attempt reentry if lock bit is unlocked
    if (flags.LOCK == 1) {
      N51ICP_reentry(5000, 1000, 10);
      cid = N51ICP_read_cid(); 
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
  
  dump();
  if (dump_size > 0)
    state = DUMPING_STATE;
  send_pkt();
}

void reset_buf() {
  rx_bufhead = 0;
}
void reset_conn() {
  DEBUG_PRINT("Disconnecting...\n");
  if (state > WAITING_FOR_CONNECT_CMD) {
    disable_connect_led();
    N51ICP_exit_icp_mode();
    N51PGM_deinit(LEAVE_RESET_HIGH);
  }
  state = DISCONNECTED_STATE;
}


void add_g_total_checksum(){
  // Specification is unclear about how long the checksum is supposed to be; we assume 16-bit
  tx_buf[8] = g_update_checksum & 0xff;
  tx_buf[9] = (g_update_checksum >> 8) & 0xff;
  tx_buf[10] = 0;
  tx_buf[11] = 0;
}

bool check_packet_timeout(){
  return curr_time - last_read_time > 500;
}

void loop()
{
  curr_time = millis();
  if (Serial.available()) {
    int tmp = Serial.read();
    rx_buf[rx_bufhead++] = tmp;
    if (state == DISCONNECTED_STATE) {
      if (tmp != CMD_CONNECT){
        DEBUG_PRINT("NOCONN: %d\n", tmp);
        reset_buf();
        return;
      }
      state = CONNECTING_STATE;
    } else if (state == CONNECTING_STATE) {
      if (rx_bufhead < 5) {
        if (tmp != 0){
          DEBUG_PRINT("0NOT\n");
          state = DISCONNECTED_STATE;
          reset_buf();
          return;
        }
      } else {
        state = WAITING_FOR_CONNECT_CMD;
      }
    }

    if (rx_bufhead < PACKSIZE) {
      return;
    }
    DEBUG_PRINT("received packet\n");
    // full packet received
    last_read_time = millis();
    rx_bufhead = 0;
    inc_g_packno();
#if DEBUG_VERBOSE
    DEBUG_PRINT("received packet: ");
    for (int i = 0; i < PACKSIZE; i++)
      DEBUG_PRINT(" %02x", rx_buf[i]);
    DEBUG_PRINT("\n");
#endif
    
    uint8_t cid;
    uint32_t devid;
    uint8_t cmd = rx_buf[0];
    uint32_t seqno = (rx_buf[5] << 8) | rx_buf[4];
    int num_read = 0;
    int ldrom_size = 0;
    config_flags flags;

    DEBUG_PRINT("received %d-byte packet, %s (0x%02x), seqno 0x%04x, checksum 0x%04x\n", PACKSIZE, cmd_enum_to_string(cmd), cmd, seqno, get_checksum());

#if CHECK_SEQUENCE_NO
    if (g_packno != seqno && cmd != CMD_SYNC_PACKNO && cmd != CMD_CONNECT)
    {
      DEBUG_PRINT("seqno mismatch, expected 0x%04x, got 0x%04x, ignoring packet...\n", g_packno, seqno);
      state = COMMAND_STATE;
      send_pkt();
      return;
    }
#endif
    if (state == WAITING_FOR_SYNCNO && cmd != CMD_SYNC_PACKNO && cmd != CMD_CONNECT) {
      // No syncno command, just skip to command state
      state = COMMAND_STATE;
    } else if ((state == DUMPING_STATE || state == UPDATING_STATE) && cmd != CMD_FORMAT2_CONTINUATION) {
      state = COMMAND_STATE;
    } else if (state == DUMPING_STATE) {
      dump();
      if (dump_size == 0)
        state = COMMAND_STATE;
      send_pkt();
      return;
    } else if (state == UPDATING_STATE) {
      update(&rx_buf[8], SEQ_UPDATE_PKT_SIZE);
      if (update_size == 0) {
        state = COMMAND_STATE;
      }
      add_g_total_checksum();
      send_pkt();
      return;
    }
    switch (cmd) {
      case CMD_CONNECT:
        {
          g_packno = 0;
          DEBUG_PRINT("CMD_CONNECT\n");
          INVALIDATE_CACHE;
          if (state == WAITING_FOR_CONNECT_CMD) {
            state = WAITING_FOR_SYNCNO;
            N51ICP_init(true);
            enable_connect_led();
          } else if (state == WAITING_FOR_SYNCNO) {
            // Don't send back a packet if we just connected and are waiting for syncno
            // It means that we got multiple connect commands, we only need to respond to one of them
            break;
          }
          send_pkt();
          DEBUG_PRINT("Connected!\n");
        } break;
      case CMD_GET_FWVER:
        tx_buf[8] = FW_VERSION;
        tx_buf[9] = 0;
        tx_buf[10] = 0;
        tx_buf[11] = 0;
        send_pkt();
        break;
      case CMD_GET_FLASHMODE:
        DEBUG_PRINT("CMD_GET_FLASHMODE\n");
        read_config(&flags);
        if (flags.CBS == 1){
          tx_buf[8] = APMODE;
        } else {
          tx_buf[8] = LDMODE;
        }
        tx_buf[9] = 0;
        tx_buf[10] = 0;
        tx_buf[11] = 0;
        send_pkt();
        break;
      case CMD_SYNC_PACKNO:
      {
        DEBUG_PRINT("CMD_SYNC_PACKNO\n");
#if CHECK_SEQUENCE_NO
        int seqnoCopy = (rx_buf[9] << 8) | rx_buf[8];
        if (seqnoCopy != seqno)
        {
          DEBUG_PRINT("seqno mismatch, expected 0x%04x, got 0x%04x, ignoring packet...\n", seqno, seqnoCopy);
          g_packno = -1; // incremented by send_pkt
        }
        else
#endif
        {
          g_packno = seqno;
        }
        state = COMMAND_STATE;
        send_pkt();
      }
      break;
      case CMD_GET_CID:
        {
        DEBUG_PRINT("CMD_GET_CID\n");
        uint8_t id = N51ICP_read_cid();
        DEBUG_PRINT("received cid of 0x%02x\n", id);
        tx_buf[8] = id;
        tx_buf[9] = 0;
        tx_buf[10] = 0;
        tx_buf[11] = 0;
        send_pkt();
        } break;
      case CMD_GET_UID:
        {
        N51ICP_read_uid(&tx_buf[8]);
        DEBUG_PRINT("received uid of ");
        DEBUG_PRINT_BYTEARR(&tx_buf[8], 12);
        send_pkt();
        } break;
      case CMD_GET_UCID:
        {
        // __uint128_t id = N51ICP_read_ucid();
        // DEBUG_PRINT("received ucid of 0x%08x\n", id);
        // for (int i = 0; i < 16; i++)
        //   rx_buf[8 + i] = (id >> (i * 8)) & 0xff;
        N51ICP_read_ucid(&tx_buf[8]);
        DEBUG_PRINT("received ucid of ");
        DEBUG_PRINT_BYTEARR(&tx_buf[8], 16);
        send_pkt();
        } break;
      case CMD_GET_DEVICEID:
        {
        uint32_t id = N51ICP_read_device_id();
        DEBUG_PRINT("received device id of 0x%04x\n", id);
        tx_buf[8] = id & 0xff;
        tx_buf[9] = (id >> 8) & 0xff;
        tx_buf[10] = 0;
        tx_buf[11] = 0;
        send_pkt();
        } break;
      case CMD_READ_CONFIG:
        DEBUG_PRINT("CMD_READ_CONFIG\n");
        N51ICP_read_flash(CFG_FLASH_ADDR, CFG_FLASH_LEN, &tx_buf[8]);
        // set the rest of the packet to FF
        memset(&tx_buf[8 + CFG_FLASH_LEN], 0xFF, PACKSIZE - 8 - CFG_FLASH_LEN);
        send_pkt();
        break;
      case CMD_UPDATE_CONFIG: {
        DEBUG_PRINT("CMD_UPDATE_CONFIG\n");
        INVALIDATE_CACHE;
#if NO_DANGEROUS_CONFIGS
        config_flags * update_flags = (config_flags *)&rx_buf[8];
        if (update_flags->RPD == 0 && update_flags->WDTEN & 0x0F == 0xF) {
          DEBUG_PRINT("Refusing to set potentially-dangerous config with the reset pin disabled and watchdog timer disabled ...\n");
          fail_pkt();
          break;
        }
#endif
        N51ICP_page_erase(CFG_FLASH_ADDR);
        N51ICP_write_flash(CFG_FLASH_ADDR, CFG_FLASH_LEN, &rx_buf[8]);
        send_pkt();
      } break;
      case CMD_ERASE_ALL: // Erase all only erases the AP ROM, so we have to page erase the APROM area
      {
        DEBUG_PRINT("CMD_ERASE_ALL\n");
        INVALIDATE_CACHE;
        read_config(&flags);
        int ldrom_size = get_ldrom_size(&flags);
        DEBUG_PRINT("ldrom_size: %d\n", ldrom_size);
        DEBUG_PRINT("Erasing %d bytes of APROM\n", FLASH_SIZE - ldrom_size);
        for (int i = 0; i < FLASH_SIZE - ldrom_size; i += PAGE_SIZE) {
          N51ICP_page_erase(i);
        }
        send_pkt();
      } break;
      case CMD_ISP_MASS_ERASE:
        {
        DEBUG_PRINT("CMD_ISP_MASS_ERASE\n");

          INVALIDATE_CACHE;
          if (!mass_erase_checked(false)) break;
          send_pkt();
        }
        break;
      case CMD_ISP_PAGE_ERASE:
      {
        INVALIDATE_CACHE;
        int addr = (rx_buf[9] << 8) | rx_buf[8];
        DEBUG_PRINT("CMD_ISP_PAGE_ERASE (addr: %d)\n", addr);
        N51ICP_page_erase(addr & PAGE_MASK);
        send_pkt();
      } break;
      case CMD_RUN_APROM:
      case CMD_RUN_LDROM:
      case CMD_RESET:{
        DEBUG_PRINT("exiting from ICP and running aprom...\n");
        INVALIDATE_CACHE;
        send_pkt();
        reset_conn();
      } break;
      case CMD_READ_ROM:
        dump_addr = (rx_buf[9] << 8) | rx_buf[8];
        dump_size = (rx_buf[13] << 8) | rx_buf[12];
        DEBUG_PRINT("CMD_READ_ROM (addr: %d, size: %d) \n", dump_addr, dump_size);
        start_dump(dump_addr, dump_size);
        break;

      case CMD_UPDATE_WHOLE_ROM:
        g_update_checksum = 0;
        DEBUG_PRINT("CMD_UPDATE_WHOLE_ROM\n");
        INVALIDATE_CACHE;
        // preserved_ldrom_sz = 0;
        if (!mass_erase_checked(true)) break;
        update_addr = (rx_buf[9] << 8) | rx_buf[8];
        update_size = (rx_buf[13] << 8) | rx_buf[12];
        if (update_size == 0){
          fail_pkt();
          break;
        }
        DEBUG_PRINT("flashing %d bytes\n", update_size);
        update(&rx_buf[16], 48);
        add_g_total_checksum();
        if (update_size > 0)
          state = UPDATING_STATE;
        send_pkt();
        break;

      case CMD_UPDATE_APROM: {
        g_update_checksum = 0;
        update_addr = (rx_buf[9] << 8) | rx_buf[8];
        update_size = (rx_buf[13] << 8) | rx_buf[12];
        DEBUG_PRINT("CMD_UPDATE_APROM (addr: %d, size: %d)\n", update_addr, update_size);
        if (update_size == 0){
          fail_pkt();
          break;
        }
        read_config(&flags);
        
        cid = N51ICP_read_cid();
        int ldrom_size = get_ldrom_size(&flags);
        // Specification states that we need to erase the aprom when we receive this command
        if (flags.LOCK != 0 && cid != 0xFF) {
          // device is not locked, we need to erase only the areas we're going to write to
          uint16_t start_addr = update_addr & PAGE_MASK;
          uint16_t end_addr = (start_addr + update_size);
          for (uint16_t curr_addr = update_addr; curr_addr < end_addr; curr_addr += PAGE_SIZE){
            N51ICP_page_erase(curr_addr);
          }
        } else { // device is locked, we'll need to do a mass erase
          if (!mass_erase_checked(true)) break;
        }
        INVALIDATE_CACHE;
        read_config(&flags);
        DEBUG_PRINT("flashing %d bytes\n", update_size);
        update(&rx_buf[16], 48);
        add_g_total_checksum();
        if (update_size > 0)
          state = UPDATING_STATE;
        send_pkt();
      } break;
      default:
        DEBUG_PRINT("unknown command 0x%02x\n", cmd);
        fail_pkt();
        break;
    }
  } else if (rx_bufhead > 0 && rx_bufhead < PACKSIZE && check_packet_timeout()){
    DEBUG_PRINT("PCKSIZE_TIMEOUT\n");
    reset_buf(); // reset the buffer
  }
#if CONNECTION_TIMEOUT
  else { // serial has no characters
    if (state > WAITING_FOR_CONNECT_CMD && curr_time - last_read_time > CONNECTION_TIMEOUT) { // 10 seconds between packets
        DEBUG_PRINT("Connection timeout, resetting...\n");
        reset_conn();
        reset_buf();
    }
  }
#endif
}
