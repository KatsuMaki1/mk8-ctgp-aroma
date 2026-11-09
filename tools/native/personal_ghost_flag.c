/* Personal ghost card: render a flag using the active Options country only
 * when the recorded Mii identity belongs to the current account. No writes to
 * the recording, ghost metadata, controller fields or ranking data. */
typedef unsigned int u32;typedef unsigned char u8;
#define W(p,o) (*(volatile u32*)((__UINTPTR_TYPE__)(p)+(o)))
#define B(p,o) (*(volatile u8*)((__UINTPTR_TYPE__)(p)+(o)))
#define FN(a,t) ((t)(__UINTPTR_TYPE__)(a))
extern void original_personal_flag_card(u32,u32,u32,u32);
extern u32 personal_flag_selected_country(void);
#include "personal_flag_identity.h"
const char personal_flag_marker[]="CTGP_PERSONAL_GHOST_FLAG_V1";
volatile u32 personal_flag_calls,personal_flag_draws,personal_flag_status;
volatile u32 personal_flag_control,personal_flag_record,personal_flag_country;
static int pointer(u32 p){return p>=0x10000000u&&p<0x60000000u;}
void personal_flag_card(u32 control,u32 index,u32 mode,u32 hidden){
 original_personal_flag_card(control,index,mode,hidden);
 personal_flag_calls++;personal_flag_status=1;personal_flag_control=control;
 if(!pointer(control)||!W(control,0x70)||hidden||!B(control,0x87))return;
 u32 country=personal_flag_selected_country();if(!country||country>254)return;
 u32 system=FN(0x024ce59cu,u32(*)(void))();if(!pointer(system))return;
 u32 manager=W(system,0x2c0),locale=W(system,0x2d0);
 if(!pointer(manager)||!pointer(locale))return;
 u32 account=W(locale,0x614);if(!pointer(account))return;
 int slot=FN(0x02441d48u,int(*)(u32))(index);
 if(slot<0||(u32)slot>=W(manager,0x34)||!pointer(W(manager,0x3c)))return;
 u32 record=W(W(manager,0x3c),(u32)slot*4);personal_flag_record=record;
 if(!pointer(record)){personal_flag_status=2;return;}
 if(!personal_flag_same_identity((const u8*)(__UINTPTR_TYPE__)(record+0xc4),(const u8*)(__UINTPTR_TYPE__)(account+0x14))){personal_flag_status=3;return;}
 u32 pane=W(control,0x5c),owner=W(control,0x6c);
 if(!pointer(pane)||!pointer(owner)){personal_flag_status=4;return;}
 u32 texture=FN(0x0255dee4u,u32(*)(u32,u32))(owner,country);
 if(!texture){personal_flag_status=5;return;}
 FN(0x02531c54u,void(*)(u32,u32,u32,u32))(control,pane,texture,0);
 FN(0x02531bdcu,void(*)(u32,u32,u32))(control,pane,1);
 /* The native card's first animation selects its name-with-flag placement. */
 u32 animations=W(control,0x20);
 if(pointer(animations)&&W(control,0x1c)){
  u32 animation=W(animations,0);if(pointer(animation))FN(0x02530ee0u,void(*)(double,u32,u32))(1.0,animation,0);
 }
 personal_flag_country=country;personal_flag_draws++;personal_flag_status=6;
}
