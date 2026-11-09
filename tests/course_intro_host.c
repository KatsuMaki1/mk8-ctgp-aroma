#include <assert.h>
static unsigned memory[2048];
#define INTRO_HOST
#define W(p,o) memory[((p)+(o))/4]
#define STR(p) ((p)==0x4000?"Gu_Bcp31":"Gu_FirstCircuit")
#include "../tools/native/course_intro.c"
int main(void){
    W(0x100,4)=2;W(0x100,8)=0x200;
    W(0x200,0x34)=0x4001;W(0x200,0x14)=100;
    W(0x254,0x34+8)=0x4000;W(0x254,0x14+8)=0x3c0c;W(0x254,0x24+8)=0x3e64;
    assert(message(0x100,"Gu_Bcp31",99,0)==0x3c0c);
    assert(message(0x100,"Gu_Bcp31",99,1)==0x3e64);
    assert(message(0x100,"Gu_City",99,0)==99);
    assert(message(0,"Gu_Bcp31",99,0)==99);
    W(0x100,4)=300;assert(message(0x100,"Gu_Bcp31",99,0)==99);
}
