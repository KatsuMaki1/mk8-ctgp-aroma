#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
static uint32_t ram[4096],draws;
#define W(p,o) ram[((p)+(o))/4]
#define B(p,o) ((unsigned char*)ram)[(p)+(o)]
#include "../tools/native/ui_texture_guard.c"
void original_ui_picture_draw(u32 picture,u32 draw){(void)picture;(void)draw;draws++;}
int main(void){
 u32 pane=0x1000,material=0x2000,maps=0x3000;
 W(pane,0xa4)=material;strcpy((char*)&B(pane,0x80),"P_Test_00");
 ui_picture_draw(pane,0);assert(draws==1&&!ui_texture_missing_count); /* untextured material */
 W(material,0xc)=1u<<30;W(material,0x10)=maps;
 ui_picture_draw(pane,0);assert(draws==1&&ui_texture_missing_count==1);
 assert(!strcmp((const char*)ui_texture_missing[0].name,"P_Test_00"));
 W(maps,0x18)=0x4000;ui_picture_draw(pane,0);assert(draws==2);
 W(material,0xc)=2u<<30;ui_picture_draw(pane,0);assert(draws==2&&ui_texture_missing[1].index==1);
 W(maps,0x1c+0x18)=0x5000;ui_picture_draw(pane,0);assert(draws==3);
 puts("Only incomplete textured UI pictures are skipped; complete/untextured pictures preserve native draw");
}
