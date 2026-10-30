/* EUR81 secondary-controller/UI mapping, verified from 0250CF08 and 024CB508.
 * UI + = bit 3, - = bit 4; X/Y use bits 9/10, not the old header aliases.
 * Device 2/3 = Remote/MotionPlus, 4 = Remote + Nunchuk; 1 = GamePad. */
static unsigned int wiimote_cup_keys(unsigned int keys,unsigned int device,
                                   unsigned int page,unsigned int required) {
    if((device!=2 && device!=3 && device!=4) ||
       (page!=0x2b && page!=0x2c && page!=0x3f) ||
       (required!=0x800 && required!=0x1000))return keys;
    unsigned int pair=keys&0x18;
    if(pair==0x18)return keys; /* Simultaneous +/- does not choose a direction. */
    if(pair==0x10)return (keys&~0x10u)|0x800;
    if(pair==0x08)return (keys&~0x08u)|0x1000;
    return keys;
}
