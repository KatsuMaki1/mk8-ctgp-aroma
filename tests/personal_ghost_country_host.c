#include <assert.h>
#include "../tools/native/personal_ghost_country.c"
static u32 selected,args[6];
u32 personal_country_selected(void){return selected;}
void personal_country_native_set(u32 a,u32 b,u32 c,u32 d,u32 e,u32 f){args[0]=a;args[1]=b;args[2]=c;args[3]=d;args[4]=e;args[5]=f;}
int main(void){
 selected=219;personal_country_set(11,22,33,0,44,55);
 assert(args[0]==11&&args[1]==22&&args[2]==33&&args[3]==219&&args[4]==44&&args[5]==55);
 selected=0;personal_country_set(11,22,33,110,44,55);assert(args[3]==110);
 selected=255;personal_country_set(11,22,33,77,44,55);assert(args[3]==77);
 return 0;
}
