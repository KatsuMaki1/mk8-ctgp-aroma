/* Reject an incomplete UI picture before GX2SetPixelTexture receives NULL.
 * Keep diagnostics so the missing layout/asset can be identified and repaired. */
typedef unsigned int u32;
#ifndef W
#define W(p,o) (*(volatile u32 *)((__UINTPTR_TYPE__)(p)+(o)))
#define B(p,o) (*(volatile unsigned char *)((__UINTPTR_TYPE__)(p)+(o)))
#endif
extern void original_ui_picture_draw(u32,u32);
const char ui_texture_guard_marker[]="MK8_UI_NULL_TEXTURE_GUARD_V1";
volatile u32 ui_texture_missing_count;
struct MissingPicture {u32 picture,material,map,index;char name[24];};
volatile struct MissingPicture ui_texture_missing[8];
void ui_picture_draw(u32 picture,u32 draw){
 u32 material=W(picture,0xa4);
 if(material){
  u32 count=W(material,0xc)>>30,maps=W(material,0x10);
  for(u32 i=0;i<count;i++)if(!maps||!W(maps,i*0x1c+0x18)){
   volatile struct MissingPicture *entry=&ui_texture_missing[ui_texture_missing_count&7];
   entry->picture=picture;entry->material=material;entry->map=maps;entry->index=i;
   for(u32 j=0;j<23;j++)entry->name[j]=(char)B(picture,0x80+j);
   entry->name[23]=0;ui_texture_missing_count++;
   return;
  }
 }
 original_ui_picture_draw(picture,draw);
}
