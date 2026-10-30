#include <assert.h>
#include <string.h>
#include "../tools/native/online_resolve.h"
static void put(online_u8 *p, online_u32 n) {
    p[0]=n>>24;p[1]=n>>16;p[2]=n>>8;p[3]=n;
}
int main(void) {
    online_u8 cups[12*0x80], records[2*0x54]={0};
    online_u32 c=99,s=99;
    memset(cups,0xff,sizeof cups);
    for(unsigned i=0;i<4;i++) put(cups+7*0x80+i*0x10,20+i);
    for(unsigned i=0;i<4;i++) {
        assert(online_course_position(cups,20+i,&c,&s));
        assert(c==7 && s==i);
    }
    assert(!online_course_position(cups,77,&c,&s));
    /* Extra native row entries must not be accepted as playable slots. */
    put(cups+7*0x80+4*0x10,77);
    assert(!online_course_position(cups,77,&c,&s));
    put(records,1);put(records+4,7);
    put(records+0x54,2);put(records+0x58,7);
    for(unsigned i=0;i<4;i++) put(records+0x54+0x34+i*4,100+i);
    const online_u8 *r=online_find_cup(records,2,2,7);
    assert(r==records+0x54);
    for(unsigned i=0;i<4;i++) assert(online_be32(r+0x34+4*i)==100+i);
    assert(!online_find_cup(records,2,3,7));
    assert(!online_find_cup(records,257,2,7));
    online_u8 a[8]={1,2,3,4,5,0,0,0},b[8]={1,2,3,4,5,1,0,0};
    assert(!online_same_player(a,b)); /* Two local players on one console. */
    b[5]=0;b[6]=42;b[7]=19;
    assert(online_same_player(a,b)); /* Ignore padding, not player index. */
    online_u8 menu[0x9c];memset(menu,0,sizeof menu);
    for(unsigned i=0;i<12;i++)put(menu+12*i,0xfd);
    put(menu+0x90,0xfd);
    assert(!online_winning_vote(menu));
    memcpy(menu+12*3,a,6);menu[12*3+8]=(27<<1)|1;
    memcpy(menu+0x90,a,6);
    menu[0x98]=0x74; /* Captured readiness flags wrongly decoded as course 58. */
    assert(online_winning_vote(menu)==menu+12*3);
    assert(online_winning_vote(menu)[8]>>1==27);
    menu[0x95]=1;assert(!online_winning_vote(menu));
    return 0;
}
