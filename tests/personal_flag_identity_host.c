#include <assert.h>
#include <string.h>
#include "../tools/native/personal_flag_identity.h"
int main(void){
 unsigned char recorded[96]={0},active[96]={0};
 assert(!personal_flag_same_identity(recorded,active));
 for(unsigned i=4;i<24;i++)recorded[i]=active[i]=(unsigned char)(i+1);
 active[28]='X';active[95]=123;
 assert(personal_flag_same_identity(recorded,active));
 active[12]^=1;
 assert(!personal_flag_same_identity(recorded,active));
 return 0;
}
