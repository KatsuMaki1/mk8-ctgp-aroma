#include <assert.h>
#include <string.h>
#define WIIMOTE_CUPS_HOST
#include "../tools/native/wiimote_cups.c"
static u32 words[0x1000],ui_global,calls,seen_pressed,seen_repeated,seen_player;
u32 *wiimote_cups_word(u32 a){
 if(a==0x1018a18c)return &ui_global;
 assert(a<sizeof(words)&&!(a&3));return &words[a/4];
}
void original_wiikey(u32 key,u32 player){
 (void)key;calls++;seen_player=player;u32 pad=W(0x300,(player<4?player:0)*4);
 seen_pressed=W(pad,0x54);seen_repeated=W(pad,0x58);W(pad,4)=0x01010000;
}
static void setup(u32 page,u32 required,u32 player,u32 device,u32 pressed,u32 repeated){
 memset(words,0,sizeof(words));calls=0;ui_global=0x200;W(0x200,0x14)=0x300;
 W(0x100,0)=0x180;W(0x180,4)=page;W(0x100,0x14)=required;
 for(u32 i=0;i<4;i++)W(0x300,i*4)=0x400+i*0x100;
 u32 pad=W(0x300,(player<4?player:0)*4);W(pad,0x60)=device;W(pad,0x54)=pressed;W(pad,0x58)=repeated;
}
int main(void){
 u32 pages[]={0x2b,0x2c,0x3f};
 for(u32 i=0;i<3;i++)for(u32 device=2;device<=4;device++)for(u32 player=0;player<5;player++){
  setup(pages[i],0x800,player,device,0x10,0x8);
  wiimote_cup_poll(0x100,player);u32 pad=W(0x300,(player<4?player:0)*4);
  assert(calls==1&&seen_player==player&&seen_pressed==0x800&&seen_repeated==0x1000);
  assert(W(pad,0x54)==0x10&&W(pad,0x58)==0x8&&W(pad,4)==0x01010000);
 }
 setup(0x2b,0x1000,0,1,0x8,0x10);wiimote_cup_poll(0x100,0);assert(seen_pressed==0x8&&seen_repeated==0x10);
 setup(0x2b,0x1000,0,5,0x8,0x10);wiimote_cup_poll(0x100,0);assert(seen_pressed==0x8&&seen_repeated==0x10);
 setup(0x2a,0x800,0,2,0x10,0);wiimote_cup_poll(0x100,0);assert(seen_pressed==0x10);
 setup(0x2b,1,0,2,0x10,0);wiimote_cup_poll(0x100,0);assert(seen_pressed==0x10);
 return 0;
}
