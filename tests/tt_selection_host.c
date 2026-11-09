#include <assert.h>
#include <stdio.h>
#include <string.h>
typedef unsigned u32;typedef unsigned char u8;
static struct {u32 address,value;} words[256];static u32 word_count;
static u32 *word(u32 address){for(u32 i=0;i<word_count;i++)if(words[i].address==address)return &words[i].value;assert(word_count<256);words[word_count].address=address;return &words[word_count++].value;}
#define W(p,o) (*word((p)+(o)))
static const char *text(u32 address){switch(address){case 1:return "Gu_BcpParis";case 2:return "Gu_BcpToad";case 3:return "Gu_FirstCircuit";default:return "Gu_NotInstalled";}}
#define TT_CAPTURE_STRING(address) text(address)
static u32 pink_enabled;
#include "../tools/native/tt_selection.h"
static u32 forwarded,saw_valid;
void original_tt_course_event(u32 page,u32 event){(void)page;(void)event;forwarded++;saw_valid=tt_selected_valid;}
int main(void){
 u32 page=0x60000,event=0x61000,source=0x50000,data=0x20000;
 W(0x1018a18c,0)=0x10000;W(0x10000,0xc)=0x11000;W(0x11000,0)=4;W(0x11000,4)=0x12000;W(0x12000,12)=0x13000;W(0x13000,0x28)=data;
 W(data,0x1438)=1;W(0x1030c010,0)=1;W(0x1030c000,0)=2;
 W(page,4)=44;W(page,0x278)=source;W(page,0x37c)=2;W(source,0xf4)=20;W(event,8)=source;W(event,0x14)=2;
 W(data,2*0x80+0x10)=20;W(0x10302564,0)=0x30000;W(0x30000,4)=1;W(0x30000,8)=0x31000;W(0x31000,0)=2;W(0x31000,4)=2;W(0x31000,0x38)=1;
 tt_course_event(page,event);assert(forwarded==1&&saw_valid);assert(!strcmp(tt_selected_identity,"ct.gu_bcpparis"));assert(tt_selected_category.cc==150);assert(strstr(tt_selected_path,"/150/"));
 /* Same vanilla course/slot on a different page must become a different CT. */
 W(page,0x37c)=3;W(0x31000,0)=3;W(0x31000,0x38)=2;W(0x1030c000,0)=3;pink_enabled=1;
 tt_course_event(page,event);assert(saw_valid&&!strcmp(tt_selected_identity,"ct.gu_bcptoad"));assert(tt_selected_category.cc==200&&tt_selected_category.pink);assert(strstr(tt_selected_path,"/200/p1/"));
 /* Missing CT must clear the previous identity, never fall back to a donor. */
 W(0x31000,0x38)=99;tt_course_event(page,event);assert(!saw_valid&&tt_selected_status==7&&!tt_selected_identity[0]);
 W(page,0x37c)=0;W(0x103028e8,20*4)=3;tt_course_event(page,event);assert(saw_valid&&!strcmp(tt_selected_identity,"native.gu_firstcircuit"));
 u32 count=tt_selected_count;W(event,8)=0xdead;tt_course_event(page,event);assert(tt_selected_count==count);W(event,8)=source;W(event,0x14)=0;tt_course_event(page,event);assert(tt_selected_count==count);
 W(event,0x14)=2;W(data,0x1438)=2;tt_course_event(page,event);assert(!saw_valid&&tt_selected_status==2);
 puts("Accepted click captures CT before native transition; pages, cc, physics and missing donors isolated");
}
