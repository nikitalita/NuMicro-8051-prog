// memory_size, LDROM_size, RAM_size, DID, Flash_type
#pragma once
#include <stdint.h>

typedef struct _flash_info{
    uint32_t memory_size;
    uint32_t LDROM_size;
    uint32_t RAM_size;
    uint32_t DID;
    uint32_t Flash_type;
} flash_info_t;
#ifdef __cplusplus
extern "C" {
#endif

const flash_info_t *get_flash_info(uint32_t DID);
uint32_t flash_info_get_aprom_size(const flash_info_t *flash_info, uint32_t ldrom_size);
uint32_t flash_info_get_max_nvm_size(const flash_info_t *flash_info);
#ifdef __cplusplus
}
#endif