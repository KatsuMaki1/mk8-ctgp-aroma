#include <assert.h>
#define FORMATTER_HOST
#include "../tools/native/formatter_strings.c"
static unsigned calls;
void host_terminate(const struct SafeString *p){assert(p->vtable==0x12345678);calls++;}
int main(void){
    struct SafeString in={"mapobj/Sanbo/Sanbo.bfres",0x12345678},out;
    const struct SafeString *p=plain(&in,&out);
    assert(p==&out && p->text==in.text && p->vtable==0x100ffbccu);
    assert(calls==1 && in.vtable==0x12345678);
    assert(plain(0,&out)==0 && calls==1);
    in.text=0;assert(plain(&in,&out)==&in && calls==1);
}
