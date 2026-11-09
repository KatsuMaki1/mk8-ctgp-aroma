#define TT200_HOST
#include <stdint.h>
#include <assert.h>
static unsigned char ram[65536];static unsigned hides,selects,forwarded,engine,last_focus;static unsigned visible[5];
static void hide(uint32_t p,uint32_t pane,uint32_t value){assert(p && (pane==p+0x2800 || pane==p+0x3000) && value<=1);visible[(p-0x4000)/0x100]=value;hides++;}
static void focus(uint32_t p,uint32_t a,uint32_t b,uint32_t c,uint32_t d){assert(p==0x5000 && a==0 && (b==2 || b==4) && c==0 && d==1);last_focus=b;selects++;}
static uintptr_t api(uint32_t p){return p==0x02531bdc?(uintptr_t)&hide:(uintptr_t)&focus;}
#define W(p,o) (*(uint32_t *)(ram+(p)+(o)))
#define B(p,o) (*(unsigned char *)(ram+(p)+(o)))
#define FN(a,t) ((t)api(a))
#include "../tools/native/tt200.c"
void original_tt_mode(uint32_t page,uint32_t event){(void)event;W(page,0xcc)=37;}
void original_tt_class_in(uint32_t page){(void)page;}
void original_tt_class_calc(uint32_t page){(void)page;}
void original_tt_class_event(uint32_t page,uint32_t event){(void)page;forwarded++;if(W(event,0x14)==2)engine=W(event,0xc)==4?3:2;}
void original_tt_race_copy(uint32_t destination,uint32_t source){W(destination,0x17c)=W(source,0x17c);W(destination,0x180)=2;}
int main(void){
 uint32_t page=0x1000,event=0x2000,buttons=0x3000;W(event,8)=1;W(event,0x14)=2;
 W(event,0xc)=0;tt200_mode(page,event);assert(W(page,0xcc)==37);
 W(event,0xc)=1;tt200_mode(page,event);assert(W(page,0xcc)==30);
 W(page,0x11c)=5;W(page,0x124)=buttons;W(page,0xac)=0x5000;
 for(unsigned i=0;i<5;i++){W(buttons,i*4)=0x4000+i*0x100;W(0x4000+i*0x100,0x50)=0x6000+i*0x100;W(0x6000+i*0x100,0xc)=0x6800+i*0x100;W(0x6800+i*0x100,0xc)=0x7000+i*0x100;}
 B(0x4200,0x18)=0;B(0x4400,0x18)=1;W(0x4400,0x38)=0x80000013;
 tt200_class_in(page);assert(hides==10 && selects==1 && B(0x4400,0x18)==0 && W(0x4400,0x38)==0x13);
 assert(!visible[0] && !visible[1] && visible[2] && !visible[3] && visible[4]);
 u32 y150=W(0x7200,0x20),y200=W(0x7400,0x20);
 tt200_class_calc(page);tt200_class_in(page);assert(W(0x7200,0x20)==y150 && W(0x7400,0x20)==y200);
 W(event,0x14)=0;W(event,0xc)=3;tt200_class_event(page,event);assert(last_focus==4);
 W(event,0xc)=4;tt200_class_event(page,event);W(event,0xc)=3;tt200_class_event(page,event);assert(last_focus==2);
 forwarded=0;W(event,0x14)=2;
 W(event,0xc)=4;tt200_class_event(page,event);assert(engine==3 && tt200_selected_class==3 && forwarded==1);
 W(event,0xc)=0;tt200_class_event(page,event);assert(forwarded==1);
 W(event,0xc)=2;tt200_class_event(page,event);assert(engine==2 && tt200_selected_class==2 && forwarded==2);
 W(event,0xc)=4;tt200_class_event(page,event);W(0x7000,0x17c)=1;
 tt200_race_copy(0x7400,0x7000);assert(W(0x7400,0x180)==3 && tt200_race_copy_count==1);
 W(0x7000,0x17c)=0;tt200_race_copy(0x7400,0x7000);assert(W(0x7400,0x180)==2);
 W(event,0xc)=0;tt200_mode(page,event);tt200_class_event(page,event);assert(forwarded==4);
 tt200_class_in(page);for(unsigned i=0;i<5;i++)assert(visible[i]);
 assert(W(0x7200,0x20)==0 && W(0x7400,0x20)==0);
 return 0;
}
