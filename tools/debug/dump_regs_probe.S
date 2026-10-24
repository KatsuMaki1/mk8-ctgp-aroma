# Debug probe: dump regs + memory around r28 + blob data slots onto the stack, then crash (IP=0) so Cemu's crash log prints them.
    .text
    .globl _start
_start:
    stmw    r3, 0x40(r1)          # r3..r31 at +0x40 .. +0xB4
    mflr    r0
    stw     r0, 0x3C(r1)
    lwz     r4, 0(r28)            # first 8 words of what r28 points to -> +0xC0
    stw     r4, 0xC0(r1)
    lwz     r4, 4(r28)
    stw     r4, 0xC4(r1)
    lwz     r4, 8(r28)
    stw     r4, 0xC8(r1)
    lwz     r4, 12(r28)
    stw     r4, 0xCC(r1)
    lwz     r4, 16(r28)
    stw     r4, 0xD0(r1)
    lwz     r4, 20(r28)
    stw     r4, 0xD4(r1)
    lwz     r4, 24(r28)
    stw     r4, 0xD8(r1)
    lwz     r4, 28(r28)
    stw     r4, 0xDC(r1)
    lis     r5, 0x1030            # blob data base (D-0x20 = 0x10300000)
    lwz     r4, 0x28BC(r5)        # heap/alloc slot
    stw     r4, 0xE0(r1)
    lwz     r4, 0x28C4(r5)
    stw     r4, 0xE4(r1)
    lwz     r4, 0x2318(r5)
    stw     r4, 0xE8(r1)
    lwz     r4, 0x2344(r5)
    stw     r4, 0xEC(r1)
    lwz     r6, 0x28BC(r5)        # *(*slot) = the function the blob calls to allocate
    lwz     r4, 0(r6)
    stw     r4, 0xF0(r1)
    lwz     r4, 0x28C0(r5)
    stw     r4, 0xF4(r1)
    li      r0, 0
    mtlr    r0
    blr
