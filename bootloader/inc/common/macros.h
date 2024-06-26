/*****************************************************************************/
/*   general macros                                                          */
/*****************************************************************************/
#define _enable_TA TA=0xAA;TA=0x55 // Enable writes to a TA-protected register without disabling interrupts (ensure interrupts are disabled before writing to a TA-protected register)
#define _asgn_TAR(reg, val) _enable_TA;reg=val    // Assign (=) value to TA-protected register without disabling interrupts (ensure interrupts are disabled before using)
#define _anda_TAR(reg, val) _enable_TA;reg&=val   // And-assign (&=) value to TA-protected register without disabling interrupts (ensure interrupts are disabled before using)
#define _nanda_TAR(reg, val) _enable_TA;reg&=~val // Nand-assign (&=~) value to TA-protected register without disabling interrupts (ensure interrupts are disabled before using)
#define _ora_TAR(reg, val) _enable_TA;reg|=val    // Or-assign (|=) value to TA-protected register without disabling interrupts (ensure interrupts are disabled before using)
#define _xora_TAR(reg, val) _enable_TA;reg^=val   // Xor-assign (^=) value to TA-protected register without disabling interrupts (ensure interrupts are disabled before using)

#define asgn_TAR(reg, val) BIT_TMP=EA;EA=0;_asgn_TAR(reg, val);EA=BIT_TMP // Assign (=) value to TA-protected register
#define anda_TAR(reg, val) BIT_TMP=EA;EA=0;_anda_TAR(reg, val);EA=BIT_TMP // And-assign (&=) value to TA-protected register
#define nanda_TAR(reg, val) BIT_TMP=EA;EA=0;_nanda_TAR(reg, val);EA=BIT_TMP // Nand-assign (&=~) value to TA-protected register
#define ora_TAR(reg, val) BIT_TMP=EA;EA=0;_ora_TAR(reg, val);EA=BIT_TMP // Or-assign (|=) value to TA-protected register
#define xora_TAR(reg, val) BIT_TMP=EA;EA=0;_xora_TAR(reg, val);EA=BIT_TMP // Xor-assign (^=) value to TA-protected register

#define tmp_clr_EA(statement) BIT_TMP=EA;EA=0;statement;EA=BIT_TMP // Disable interrupts for the length of the statement, then enables them again if they were already enabled
