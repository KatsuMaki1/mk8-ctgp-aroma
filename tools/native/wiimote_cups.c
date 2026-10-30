#include "wiimote_cups_logic.h"
typedef unsigned int u32;
#ifndef GD_SHIFT
#define GD_SHIFT 0
#endif
#ifdef WIIMOTE_CUPS_HOST
extern u32 *wiimote_cups_word(u32 address);
#define W(p,o) (*wiimote_cups_word((u32)(p)+(o)))
#else
#define W(p,o) (*(volatile u32*)((u32)(p)+(o)))
#endif
extern void original_wiikey(u32 key,u32 player);
const char wiimote_cups_marker[]="MK8_WIIMOTE_CUP_PAGES_V1";
void wiimote_cup_poll(u32 key,u32 player) {
    u32 page=key?W(key,0):0;
    u32 id=page?W(page,4):0,required=key?W(key,0x14):0;
    if(!page || (id!=0x2b && id!=0x2c && id!=0x3f) ||
       (required!=0x800 && required!=0x1000)) {
        original_wiikey(key,player);return;
    }
    u32 ui=W(0x1018a18c+GD_SHIFT,0);
    u32 list=ui?W(ui,0x14):0;
    u32 pad=list?W(list,player<4?player*4:0):0;
    if(!pad){original_wiikey(key,player);return;}
    u32 device=W(pad,0x60),pressed=W(pad,0x54),repeated=W(pad,0x58);
    u32 a=wiimote_cup_keys(pressed,device,id,required);
    u32 b=wiimote_cup_keys(repeated,device,id,required);
    if(a==pressed && b==repeated){original_wiikey(key,player);return;}
    /* Native key gating, focus/transition guards, sound and page wrap stay in
     * charge. Restore the pad before processing any other menu controls. */
    W(pad,0x54)=a;W(pad,0x58)=b;
    original_wiikey(key,player);
    W(pad,0x54)=pressed;W(pad,0x58)=repeated;
}
