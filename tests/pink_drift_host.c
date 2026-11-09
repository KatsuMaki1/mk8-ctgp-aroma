#include <assert.h>
#include <stdint.h>
#include <stdio.h>
static union { uint32_t align; unsigned char data[262144]; } ram;
#define W(p,o) (*(uint32_t *)(ram.data+(p)+(o)))
#define F(p,o) (*(float *)(ram.data+(p)+(o)))
#define B(p,o) (*(unsigned char *)(ram.data+(p)+(o)))
volatile unsigned int pink_enabled;
#define PINK_HOST
#include "../tools/native/pink_drift.c"
static float native_gain;static unsigned released;static int received_duration;static unsigned native_updates;
void original_drift(u32 d,u32 out,u32 in){(void)in;native_updates++;W(out,0x20)=released?2:0;if(released){W(d,8)=0;F(d,0x68)=0;}else F(d,0x68)+=native_gain;}
int original_dash(u32 d,u32 k,u32 s,int duration){(void)d;(void)k;(void)s;received_duration=duration;return 123;}
static void charge(float q){W(0x2000,8)=4;W(0x2000,0x6c)=2;F(0x2000,0x68)=q;}
int main(void){
 W(0x2000,4)=W(0x4000,4)=0x1000;W(0x1000,0x50)=0;B(0x1000,0x64)=1;W(0x4000,0x74)=90;
 released=1;charge(1000);pink_drift(0x2000,0x3000,0);pink_dash(0x4000,8,1,-1);assert(received_duration==-1&&pink_boosts==0);
 pink_enabled=1;charge(899);pink_drift(0x2000,0x3000,0);pink_dash(0x4000,8,1,-1);assert(received_duration==-1);
 charge(900);pink_drift(0x2000,0x3000,0);assert(pink_dash(0x4000,8,1,-1)==123&&received_duration==135&&pink_boosts==1);
 pink_dash(0x4000,8,1,-1);assert(received_duration==-1); /* one release, one extension */
 charge(901);pink_drift(0x2000,0x3000,0);pink_dash(0x4000,8,1,100);assert(received_duration==150);
 charge(1000);pink_drift(0x2000,0x3000,0);pink_enabled=0;pink_dash(0x4000,8,1,-1);assert(received_duration==-1);
 pink_enabled=1;pink_dash(0x4000,8,1,-1);assert(received_duration==-1);
 B(0x1000,0x66)=1;charge(1000);pink_drift(0x2000,0x3000,0);pink_dash(0x4000,8,1,-1);assert(received_duration==-1);B(0x1000,0x66)=0;
 W(0x1000,0x50)=12;charge(1000);pink_drift(0x2000,0x3000,0);pink_dash(0x4000,8,1,-1);assert(received_duration==-1);W(0x1000,0x50)=0;
 released=0;native_gain=5;charge(100);pink_enabled=0;pink_drift(0x2000,0x3000,0);assert(F(0x2000,0x68)==105);
 pink_enabled=1;charge(100);pink_drift(0x2000,0x3000,0);assert(F(0x2000,0x68)==107.5f);
 assert(native_updates==9);puts("Native effects build: faster charge, boost duration, OFF and player guards passed");return 0;
}
