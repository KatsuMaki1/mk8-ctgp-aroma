/* Shared vote identity and CUP0 slot lookup. No game pointers here. */
#ifndef MK8_ONLINE_RESOLVE_H
#define MK8_ONLINE_RESOLVE_H
typedef unsigned int online_u32;
typedef unsigned char online_u8;

/* UniqueID has six meaningful bytes, followed by two padding bytes. */
static int online_same_player(const online_u8 *a, const online_u8 *b) {
    for (unsigned i=0;i<6;i++) if(a[i]!=b[i]) return 0;
    return 1;
}

/* Native cup rows have eight 0x10-byte records; only four are race slots.
   Decode words explicitly so the same test runs on little-endian hosts. */
static online_u32 online_be32(const online_u8 *p) {
    return ((online_u32)p[0]<<24)|((online_u32)p[1]<<16)|
           ((online_u32)p[2]<<8)|p[3];
}
/* The winner section is an eight-byte UniqueID followed by readiness flags.
   Read its course from the matching player vote, never from byte 0x98. */
static const online_u8 *online_winning_vote(const online_u8 *menu) {
    if(!menu || online_be32(menu+0x90)==0xfd)return 0;
    for(online_u32 i=0;i<12;i++) {
        const online_u8 *vote=menu+12*i;
        if(online_be32(vote)!=0xfd && online_same_player(vote,menu+0x90))return vote;
    }
    return 0;
}
static int online_course_position(const online_u8 *cups, online_u32 course,
                                  online_u32 *cup, online_u32 *slot) {
    if(!cups || !cup || !slot) return 0;
    for(online_u32 c=0;c<12;c++) for(online_u32 s=0;s<4;s++) {
        if(online_be32(cups+c*0x80+s*0x10)==course) {
            *cup=c; *slot=s; return 1;
        }
    }
    return 0;
}
static const online_u8 *online_find_cup(const online_u8 *records,
        online_u32 count, online_u32 page, online_u32 cup) {
    if(!records || count>256 || cup>=12) return 0;
    for(online_u32 i=0;i<count;i++) {
        const online_u8 *r=records+i*0x54;
        if(online_be32(r)==page && online_be32(r+4)==cup) return r;
    }
    return 0;
}
#endif
