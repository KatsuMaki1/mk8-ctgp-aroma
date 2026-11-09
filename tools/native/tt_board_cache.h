/* Fixed-size local adapter snapshot. No pointers or executable content on disk. */
#define TT_BOARD_BYTES 4352u
static u32 tt_board_checksum(const u8 *data){u32 h=2166136261u;for(u32 i=0;i<TT_BOARD_BYTES;i++)if(i<24||i>=28)h=(h^data[i])*16777619u;return h;}
static u32 tt_board_word(const u8 *p){return ((u32)p[0]<<24)|((u32)p[1]<<16)|((u32)p[2]<<8)|p[3];}
static int tt_board_string(const u8 *field,u32 capacity,const char *text){for(u32 i=0;i<capacity;i++){if(field[i]!=(u8)text[i])return 0;if(!field[i])return 1;}return 0;}
static int tt_board_valid(const u8 *data,const char *id,const char *revision,u32 cc,u32 pink){
 if(tt_board_word(data)!=0x5454424cu||tt_board_word(data+4)!=1||tt_board_word(data+8)!=cc||tt_board_word(data+12)!=pink||tt_board_word(data+16)>16||tt_board_word(data+24)!=tt_board_checksum(data))return 0;
 if(!tt_board_string(data+32,96,id)||!tt_board_string(data+128,65,revision))return 0;
 for(u32 i=0;i<tt_board_word(data+16);i++){
  const u8 *row=data+256+i*256;u32 ms=tt_board_word(row+4);
  if(!tt_board_word(row)||!ms||ms>86400000u||row[72]||row[73])return 0;
 }
 return 1;
}
