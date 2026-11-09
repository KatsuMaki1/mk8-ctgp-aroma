#pragma once
#include <cstdint>
extern bool g_customFsReady;
extern char g_customFsLast[180];
extern char g_customFsFailed[180];
extern char g_customFsCourse[180];
extern char g_customFsTicketGate[180];
extern uint32_t g_customFsRedirects;
extern int32_t g_customFsStatus;
void resetCustomFs();
