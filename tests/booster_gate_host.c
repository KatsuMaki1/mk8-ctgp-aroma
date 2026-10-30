#include <assert.h>
#include <stdint.h>
#include <string.h>
#define BOOSTER_HOST
#define CUP_STATE 0x100u
static union {uint32_t align;unsigned char b[65536];} memory;
#define W(p,o) (*(uint32_t *)(memory.b+(p)+(o)))
#define STR(p) ((const char *)(memory.b+(p)))
#include "../tools/native/booster_gate.c"
static unsigned original_calls;
u32 original_gate(u32 p,u32 x,u32 e) {(void)p;(void)x;(void)e;original_calls++;return 77;}
int main(void) {
    u32 page=0x1000,ext=0x2000,event=0x3000;
    W(CUP_STATE,0)=0x200;W(0x200,4)=2;W(0x200,8)=0x400;
    for(u32 i=0;i<2;i++) {
        u32 r=0x400+i*0x54;W(r,0)=1;W(r,4)=i;
        for(u32 s=0;s<4;s++)W(r,0x34+4*s)=i?0x5100:0x5000;
    }
    strcpy((char *)memory.b+0x5000,"Gu_BcpParis");
    strcpy((char *)memory.b+0x5100,"Ginvalid");
    for(u32 i=0;i<12;i++)W(page,0x244+4*i)=0x6000+i*4;
    for(u32 i=0;i<4;i++)W(page,0x274+4*i)=0x7000+i*4;
    W(ext,0x20)=1;W(event,8)=0x6000;
    assert(booster_gate(page,ext,event)==1);assert(original_calls==0);
    for(u32 i=0;i<4;i++) {W(event,8)=0x7000+i*4;assert(booster_gate(page,ext,event)==1);}
    W(event,8)=0x6004;assert(booster_gate(page,ext,event)==77);
    W(event,8)=0x7000;assert(booster_gate(page,ext,event)==77);
    W(event,8)=0x6000;W(0x400,0x34+12)=0x5100;
    assert(booster_gate(page,ext,event)==77); /* one unavailable slot blocks the cup */
    W(0x400,0x34+12)=0x5000;
    assert(booster_gate(page,ext,event)==1);
    W(ext,0x20)=0;assert(booster_gate(page,ext,event)==77);
    W(ext,0x20)=2;assert(booster_gate(page,ext,event)==77);
    W(ext,0x20)=1;W(event,8)=0;assert(booster_gate(page,ext,event)==77);
    return 0;
}
