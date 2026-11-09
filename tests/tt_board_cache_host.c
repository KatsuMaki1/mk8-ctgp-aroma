#include <assert.h>
#include <stdio.h>
#include <stdint.h>
typedef uint32_t u32;typedef unsigned char u8;
#include "../tools/native/tt_board_cache.h"
int main(int argc,char **argv){
 assert(argc==2);FILE *file=fopen(argv[1],"rb");assert(file);u8 data[TT_BOARD_BYTES];assert(fread(data,1,sizeof data,file)==sizeof data);fclose(file);
 const char *id="ct.test",*revision="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
 assert(tt_board_valid(data,id,revision,200,1));
 assert(!tt_board_valid(data,id,revision,150,1));assert(!tt_board_valid(data,"ct.other",revision,200,1));assert(!tt_board_valid(data,id,revision,200,0));
 data[256+32]^=1;assert(!tt_board_valid(data,id,revision,200,1));
 puts("Python/server snapshot matches native cache ABI; category mismatch and corrupted data rejected");
}
