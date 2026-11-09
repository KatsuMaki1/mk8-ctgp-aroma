/* Worldwide roulette -> CTGP courses.
 * The vote carries native course ids only. When the roulette has a winner, replace that id's entry in the game's current course-directory table
 * (0x101AB678, the same table the private-room module patches) with the matching CTGP directory from ww_ct_table.h. Every CTGP client carries the
 * same table, so everyone loads the same CT. Entries are restored as soon as the online session is gone. Vote cards keep their native names. */
typedef unsigned int u32;
typedef unsigned char u8;
#include "ww_ct_table.h"
#define W(p,o) (*(volatile u32 *)((__UINTPTR_TYPE__)(p)+(o)))
#define B(p,o) (*(volatile u8 *)((__UINTPTR_TYPE__)(p)+(o)))
#ifndef WW_CT_ENABLED_DEFAULT
#define WW_CT_ENABLED_DEFAULT 1
#endif
#define COURSE_DIR_TABLE 0x101ab678u
const char ww_ct_marker[]="CTGP_WW_CT_VOTE_V1";
volatile u32 ww_ct_applied,ww_ct_restored,ww_ct_ticks,ww_ct_last_course,ww_ct_last_dir,ww_ct_enabled=WW_CT_ENABLED_DEFAULT;
static u32 saved_dir[WW_CT_COUNT];
static u8 changed[WW_CT_COUNT];

static u32 native_menu(void){
 u32 net=((u32(*)(void))(__UINTPTR_TYPE__)0x023d44f0u)();
 return net?W(net,0x12c):0;
}
static u32 menu_data(u32 menu){
 if(!menu||!W(menu,0))return 0;
 return ((u32(*)(u32))(__UINTPTR_TYPE__)W(W(menu,0),0x15c))(menu);
}
/* The vote record of the player named by the winner section (data+0x90); 12 records of 12 bytes; 0xFD marks an empty record. */
static u32 winning_course(u32 data,u32 *course){
 if(!data||W(data,0x90)==0xfdu)return 0;
 for(u32 i=0;i<12;i++){
  u32 vote=data+12*i;
  if(W(vote,0)==0xfdu)continue;
  u32 same=1;for(u32 k=0;k<6;k++)if(B(vote,k)!=B(data,0x90+k))same=0;
  if(same){*course=B(vote,8)>>1;return 1;}
 }
 return 0;
}
static void restore_all(void){
 for(u32 i=0;i<WW_CT_COUNT;i++)if(changed[i]){W(COURSE_DIR_TABLE,4*(WW_CT_FIRST+i))=saved_dir[i];changed[i]=0;ww_ct_restored++;}
}

/* ---- Vote cards: picture, name and tag of the CT instead of the native course ------------------------------------------------------------
 * Picture: the texture lookup 0255C8B8(table,&courseId) is hooked; inside a session it returns the CT's own texture (cup-page record +0x44+4*slot).
 * Name: see ww_ct_name. The 'GCN/N64' tag is not handled yet. */
#define CUP_STATE 0x10302564u
extern u32 original_ww_picture(u32,u32);
volatile u32 ww_ct_pictures,ww_ct_names;
static u32 ct_found[WW_CT_COUNT],ct_row[WW_CT_COUNT],ct_slot[WW_CT_COUNT];
static u32 same_text(const char *a,const char *b){while(*a&&*a==*b){a++;b++;}return *a==*b;}
/* Find the cup-page record and slot whose directory equals the CT directory of mapped id index. */
static u32 find_ct(u32 index){
 if(ct_found[index])return 1;
 u32 manager=W(CUP_STATE,0);if(!manager)return 0;
 u32 count=W(manager,4),rows=W(manager,8);if(!rows||count>256)return 0;
 for(u32 i=0;i<count;i++){
  u32 row=rows+i*0x54;
  for(u32 s=0;s<4;s++){
   u32 text=W(row,0x34+4*s);
   if(text&&same_text((const char *)(__UINTPTR_TYPE__)text,ww_ct_dir[index])){ct_found[index]=1;ct_row[index]=row;ct_slot[index]=s;return 1;}
  }
 }
 return 0;
}
u32 ww_ct_picture(u32 table,u32 idptr){
 u32 result=original_ww_picture(table,idptr);
 if(!ww_ct_enabled||!idptr||!native_menu())return result;
 u32 id=W(idptr,0);
 if(id<WW_CT_FIRST||id>=WW_CT_FIRST+WW_CT_COUNT)return result;
 u32 index=id-WW_CT_FIRST;
 if(!find_ct(index))return result;
 u32 texture=W(ct_row[index],0x44+4*ct_slot[index]);
 if(!texture)return result;
 ww_ct_pictures++;
 return texture;
}
/* Name: the card name message id comes from 0255A668(table@model+0x198,&courseId,x). It is already redirected by the pack; chain it and substitute the CT's name message. */
u32 ww_ct_name(u32 table,u32 idptr,u32 other){
 u32 result=((u32(*)(u32,u32,u32))(__UINTPTR_TYPE__)WW_CT_PREVIOUS_NAME)(table,idptr,other);
 if(!ww_ct_enabled||!idptr||!native_menu())return result;
 u32 id=W(idptr,0);
 if(id<WW_CT_FIRST||id>=WW_CT_FIRST+WW_CT_COUNT)return result;
 u32 index=id-WW_CT_FIRST;
 if(!find_ct(index))return result;
 u32 message=W(ct_row[index],0x14+4*ct_slot[index]);
 if(!message||message==0xffffffffu)return result;
 ww_ct_names++;
 return message;
}
/* Vote card setCourse 0257E00C(card, info, x): info[0]=course id, info[1]=tag text label (0 = no tag), info[2]=record whose +0x64 is the name label.
 * For a mapped course, pass a copy of info carrying the CT's tag label (cup-page record +0x24+4*slot) and a record pointer such that +0x64 lands on
 * the CT's name label (record +0x14+4*slot). */
extern void original_ww_card(u32,u32,u32);
volatile u32 ww_ct_cards;
void ww_ct_card(u32 card,u32 info,u32 extra){
 if(ww_ct_enabled&&info&&native_menu()){
  u32 id=W(info,0);
  if(id>=WW_CT_FIRST&&id<WW_CT_FIRST+WW_CT_COUNT&&find_ct(id-WW_CT_FIRST)){
   u32 index=id-WW_CT_FIRST,name=W(ct_row[index],0x14+4*ct_slot[index]),tag=W(ct_row[index],0x24+4*ct_slot[index]);
   if(name&&name!=0xffffffffu){
    u32 copy[4];
    copy[0]=id;copy[1]=(tag&&tag!=0xffffffffu)?tag:0;copy[2]=name-0x64u;copy[3]=W(info,12);
    ww_ct_cards++;
    original_ww_card(card,(u32)(__UINTPTR_TYPE__)copy,extra);
    return;
   }
  }
 }
 original_ww_card(card,info,extra);
}
typedef void(*Update)(u32);
void ww_ct_update(u32 ui){
 ((Update)(__UINTPTR_TYPE__)WW_CT_PREVIOUS_UPDATE)(ui);
 ww_ct_ticks++;
 if(!ww_ct_enabled)return;
 u32 menu=native_menu();
 if(!menu){restore_all();return;}
 u32 course;
 if(!winning_course(menu_data(menu),&course))return;
 if(course<WW_CT_FIRST||course>=WW_CT_FIRST+WW_CT_COUNT)return;
 u32 index=course-WW_CT_FIRST,dir=(u32)(__UINTPTR_TYPE__)ww_ct_dir[index],slot=COURSE_DIR_TABLE+4*course;
 if(W(slot,0)==dir)return;
 if(!changed[index]){saved_dir[index]=W(slot,0);changed[index]=1;}
 W(slot,0)=dir;
 ww_ct_applied++;ww_ct_last_course=course;ww_ct_last_dir=dir;
}
