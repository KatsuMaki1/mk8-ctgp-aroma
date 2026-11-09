/* DrawBridge motion recovered from MK8DX 4.0.1, functions 0x7100213F40,
 * 0x7100214214 and 0x71002144D8. Pure calculation: not a game hook.
 * The caller must supply synchronized race frames, not wall-clock time.
 * Collision variant and the actor's transform must be applied together.
 */
#ifndef CTGP_DRAWBRIDGE_MOTION_H
#define CTGP_DRAWBRIDGE_MOTION_H
#include <math.h>
struct DrawbridgeConfig {
 float delay,angle,collision_before,hold_up,speed,cycles,hold_down,collision_after;
};
enum DrawbridgePhase { BRIDGE_UP,BRIDGE_STOP_UP,BRIDGE_DOWN,BRIDGE_STOP_DOWN };
struct DrawbridgePose { float radians;unsigned phase,collision; };
static int drawbridge_pose(const struct DrawbridgeConfig *c,float frames,
                          struct DrawbridgePose *out) {
 if(!c||!out||!isfinite(frames)||frames<0)return 0;
 const float *values=(const float *)c;
 for(unsigned i=0;i<8;i++)if(!isfinite(values[i])||values[i]<0)return 0;
 if(c->speed<=0||c->angle>180||c->cycles>65535)return 0;
 float travel=ceilf(c->angle/c->speed*60.0f);
 float top=truncf(c->hold_up*60.0f),bottom=truncf(c->hold_down*60.0f);
 float delay=truncf(c->delay*60.0f),period=2*travel+top+bottom;
 if(travel<1||travel>65535||period>65535||period<1||delay>65535)return 0;
 float angle=0;
 unsigned phase=BRIDGE_STOP_DOWN;
 /* DX starts raised when there is no top dwell; an odd finite cycle count
  * also ends raised. The normal London configuration has a top dwell.
  */
 unsigned limit=(unsigned)c->cycles;
 if(top==0||(limit&1))angle=c->angle;
 if(frames>delay){
  float elapsed=frames-delay,cycle=floorf(elapsed/period);
  float t=elapsed-cycle*period;
  unsigned stage=t<travel?0:(t<=2*travel+top?1:2);
  if((t<travel||top!=0)&&(limit==0||stage+cycle*2<limit)){
   if(t<travel){angle=c->angle*t/travel;phase=BRIDGE_UP;}
   else if(t<travel+top){angle=c->angle;phase=BRIDGE_STOP_UP;}
   else if(t<2*travel+top){angle=c->angle*(1-(t-travel-top)/travel);phase=BRIDGE_DOWN;}
   else {angle=0;phase=BRIDGE_STOP_DOWN;}
  }
 }
 out->radians=angle*0.01745329238474369f;
 out->phase=phase;
 out->collision=angle>=c->collision_before?(angle>=c->collision_after?3u:2u)
                                                    :(angle>=c->collision_after?1u:0u);
 return 1;
}
#endif
