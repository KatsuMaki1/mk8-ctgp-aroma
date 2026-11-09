#include <assert.h>
#include <stdio.h>
#include <string.h>
typedef unsigned u32;typedef unsigned char u8;
static u32 class_value=3,choosing=1;static u8 colors[10][16];
static u32 value(u32 p,u32 off){
 if(p==0x1030c010u)return choosing;if(p==0x1030c000u)return class_value;
 if(p==1){if(off==4)return 46;if(off==0x20)return 10;if(off==0x28)return 2;}
 if(p==2&&off<40)return 100+off/4;
 if(p>=200&&p<210&&off==8)return 300;
 if(p==300&&off==0x44)return 0x2696054;
 return 0;
}
#define W(p,o) value((p),(o))
#define B(p,o) colors[(p)-200][(o)-0xa8]
static void set_vertex(u32 p,u32 index,u32 val){assert(index<16);colors[p-200][index]=(u8)val;}
#define FN(a,t) set_vertex
static u32 pane(u32 control,const char *name){return !strcmp(name,"P_GhostVolume_00")&&control>=100&&control<110?control+100:0;}
static void visible(u32 c,const char *name,u32 v){(void)c;(void)name;(void)v;}
void original_tt_background_calc(u32 p){(void)p;}
void previous_tt_background_class_calc(u32 p){(void)p;}
#include "../tools/native/tt_background.h"
int main(void){
 u8 original[10][16];
 for(u32 i=0;i<10;i++)for(u32 v=0;v<4;v++){colors[i][v*4]=i;colors[i][v*4+1]=40;colors[i][v*4+2]=180;colors[i][v*4+3]=(u8)(120+i+v);}
 memcpy(original,colors,sizeof(colors));tt_background_allowed=1;tt_graph_update(1);assert(tt_graph_bars==10);
 for(u32 i=0;i<10;i++)for(u32 v=0;v<4;v++){assert(colors[i][v*4]==180&&colors[i][v*4+1]==0&&colors[i][v*4+2]==40);assert(colors[i][v*4+3]==original[i][v*4+3]);}
 tt_graph_update(1);class_value=2;tt_graph_update(1);assert(!memcmp(original,colors,sizeof(colors)));
 class_value=3;choosing=0;tt_graph_update(1);assert(!memcmp(original,colors,sizeof(colors)));
 puts("All ten TT bars turn red only in 200cc; original RGB and alpha restored/preserved");
}
