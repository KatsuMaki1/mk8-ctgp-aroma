#include <assert.h>
#include "../tools/native/drawbridge_motion.h"
static void close_to(float a,float b){assert(fabsf(a-b)<0.00001f);}
int main(void){
 struct DrawbridgeConfig c={0,20,12.5f,3,8,0,3,8};
 struct DrawbridgePose a,b;
 assert(drawbridge_pose(&c,0,&a));close_to(a.radians,0);assert(a.collision==0);
 assert(drawbridge_pose(&c,75,&a));close_to(a.radians,10*0.01745329238474369f);assert(a.phase==BRIDGE_UP&&a.collision==1);
 assert(drawbridge_pose(&c,150,&a));close_to(a.radians,20*0.01745329238474369f);assert(a.phase==BRIDGE_STOP_UP&&a.collision==3);
 assert(drawbridge_pose(&c,405,&a));close_to(a.radians,10*0.01745329238474369f);assert(a.phase==BRIDGE_DOWN&&a.collision==1);
 assert(drawbridge_pose(&c,500,&a));close_to(a.radians,0);assert(a.phase==BRIDGE_STOP_DOWN);
 assert(drawbridge_pose(&c,735,&a));assert(drawbridge_pose(&c,75,&b));close_to(a.radians,b.radians);
 /* Both halves receive the same race clock and remain synchronized. */
 for(unsigned f=0;f<4000;f++){assert(drawbridge_pose(&c,(float)f,&a));assert(drawbridge_pose(&c,(float)f,&b));assert(a.radians==b.radians&&a.collision==b.collision);}
 c.speed=0;assert(!drawbridge_pose(&c,20,&a));
 c.speed=8;assert(!drawbridge_pose(&c,NAN,&a));assert(!drawbridge_pose(&c,-1,&a));
 return 0;
}
