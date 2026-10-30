#include <assert.h>
#include "../tools/native/wiimote_cups_logic.h"
int main(void){
 unsigned int pages[]={0x2b,0x2c,0x3f};
 for(unsigned int i=0;i<3;i++)for(unsigned int device=2;device<=4;device++){
  assert(wiimote_cup_keys(0x10,device,pages[i],0x800)==0x800);
  assert(wiimote_cup_keys(0x8,device,pages[i],0x1000)==0x1000);
  assert(wiimote_cup_keys(0,device,pages[i],0x800)==0);
  assert(wiimote_cup_keys(0x18,device,pages[i],0x800)==0x18);
  assert(wiimote_cup_keys(0x200,device,pages[i],0x800)==0x200); /* X */
  assert(wiimote_cup_keys(0x400,device,pages[i],0x1000)==0x400); /* Y */
  assert(wiimote_cup_keys(0x800,device,pages[i],0x800)==0x800);
  assert(wiimote_cup_keys(0x1000,device,pages[i],0x1000)==0x1000);
  assert(wiimote_cup_keys(0x11,device,pages[i],0x800)==0x801); /* preserve A */
 }
 for(unsigned int device=0;device<12;device++)if(device<2||device>4){
  assert(wiimote_cup_keys(0x18,device,0x2b,0x800)==0x18);
  assert(wiimote_cup_keys(0x10,device,0x2b,0x800)==0x10);
  assert(wiimote_cup_keys(0x08,device,0x2c,0x1000)==0x08);
 }
 for(unsigned int page=0;page<0x80;page++)if(page!=0x2b&&page!=0x2c&&page!=0x3f)
  assert(wiimote_cup_keys(0x10,2,page,0x800)==0x10);
 assert(wiimote_cup_keys(0x10,2,0x2b,1)==0x10);
 return 0;
}
