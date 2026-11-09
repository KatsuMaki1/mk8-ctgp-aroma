#include <wups.h>
#include <coreinit/filesystem.h>
#include <cstring>
#include "dlc_fs.h"
bool g_customFsReady;
char g_customFsLast[180],g_customFsFailed[180];
char g_customFsCourse[180],g_customFsTicketGate[180];
uint32_t g_customFsRedirects;
int32_t g_customFsStatus;
namespace {
using u32=uint32_t;
#include "dlc_asset_list.h"
bool customCourse,boosterCourse;
bool starts(const char *s,const char *p){if(!s)return false;while(*p)if(*s++!=*p++)return false;return true;}
const char *contentRelative(const char *p){
    // AOC content is normally inside a four-hex-digit content-index folder.
    for(unsigned i=0;i<4;i++)if(!p[i] || !((p[i]>='0' && p[i]<='9') || (p[i]>='a' && p[i]<='f') || (p[i]>='A' && p[i]<='F')))return p;
    return p[4]=='/'?p+5:p;
}
bool listed(const char *p){u32 h=2166136261u;for(const char *s=p;*s;s++)h=(h^(unsigned char)*s)*16777619u;for(const auto &e:bcp_assets)if(e.hash==h && !strcmp(e.path,p))return true;return false;}
void trace(char *to,const char *from){unsigned i=0;if(from)for(;i<179 && from[i];i++)to[i]=from[i];to[i]=0;}
const char *route(const char *path,char (&buffer)[512]) {
    if(!g_customFsReady || !path)return path;
    bool aoc=starts(path,"/vol/aoc0005000c1010ed00/") || starts(path,"/vol/aoc0005000c1010ec00/") || starts(path,"/vol/aoc0005000c1010eb00/");
    const char *rel=aoc?path+25:starts(path,"/vol/content/")?path+13:nullptr;
    if(!rel)return path;
    if(aoc)rel=contentRelative(rel);
    if(starts(rel,"course/")) {
        customCourse=listed(rel);
        // Use the final FS pathname as well as the older native formatters:
        // indexed DLC paths can otherwise leave their private overlay inactive.
        const char *c=rel+7;
        boosterCourse=customCourse && starts(c,"Gu_Bcp") && c[6]>='0' && c[6]<='4'
            && c[7]>='0' && c[7]<='9' && c[8]=='/'
            && ((c[6]-'0')*10+c[7]-'0')>=5;
    }
    if(starts(rel,"course/"))trace(g_customFsCourse,path);
    if(strstr(rel,"DL_TicketGate.bfres"))trace(g_customFsTicketGate,path);
    if(aoc || starts(rel,"course/") || starts(rel,"custom/"))trace(g_customFsLast,path);
    char privateRel[512];bool privateOverlay=false;
    if(boosterCourse && starts(rel,"mapobj/") && strlen(rel)+12<sizeof privateRel) {
        memcpy(privateRel,"custom/bcp/",11);strcpy(privateRel+11,rel);
        if(listed(privateRel)){rel=privateRel;privateOverlay=true;}
    }
    if((!aoc && !privateOverlay) || !listed(rel) || (!starts(rel,"course/") && !starts(rel,"custom/") && !customCourse))return path;
    auto n=strlen(rel);if(n+14>sizeof buffer)return path;
    memcpy(buffer,"/vol/content/",13);memcpy(buffer+13,rel,n+1);
    trace(g_customFsLast,buffer);
    if(starts(rel,"course/"))trace(g_customFsCourse,buffer);
    if(strstr(rel,"DL_TicketGate.bfres"))trace(g_customFsTicketGate,buffer);
    g_customFsRedirects++;return buffer;
}
void result(FSStatus status,const char *path){if(g_customFsReady && status<0 && path && (starts(path,"/vol/content/course/") || starts(path,"/vol/aoc") || starts(path,"/vol/content/custom/"))){g_customFsStatus=status;trace(g_customFsFailed,path);}}
}
void resetCustomFs(){g_customFsReady=false;customCourse=false;boosterCourse=false;g_customFsRedirects=0;g_customFsStatus=0;g_customFsLast[0]=0;g_customFsFailed[0]=0;g_customFsCourse[0]=0;g_customFsTicketGate[0]=0;}
#define ROUTE char buffer[512];const char *routed=route(path,buffer)
#define RETURN_STATUS(call) FSStatus status=(call);result(status,routed);return status
DECL_FUNCTION(FSStatus,FSOpenFile,FSClient *client,FSCmdBlock *block,const char *path,const char *mode,FSFileHandle *handle,FSErrorFlag mask){ROUTE;RETURN_STATUS(real_FSOpenFile(client,block,routed,mode,handle,mask));}
DECL_FUNCTION(FSStatus,FSOpenFileAsync,FSClient *client,FSCmdBlock *block,const char *path,const char *mode,FSFileHandle *handle,FSErrorFlag mask,FSAsyncData *async){ROUTE;RETURN_STATUS(real_FSOpenFileAsync(client,block,routed,mode,handle,mask,async));}
DECL_FUNCTION(FSStatus,FSGetStat,FSClient *client,FSCmdBlock *block,const char *path,FSStat *stat,FSErrorFlag mask){ROUTE;RETURN_STATUS(real_FSGetStat(client,block,routed,stat,mask));}
DECL_FUNCTION(FSStatus,FSGetStatAsync,FSClient *client,FSCmdBlock *block,const char *path,FSStat *stat,FSErrorFlag mask,FSAsyncData *async){ROUTE;RETURN_STATUS(real_FSGetStatAsync(client,block,routed,stat,mask,async));}
DECL_FUNCTION(FSStatus,FSOpenDir,FSClient *client,FSCmdBlock *block,const char *path,FSDirectoryHandle *handle,FSErrorFlag mask){ROUTE;RETURN_STATUS(real_FSOpenDir(client,block,routed,handle,mask));}
DECL_FUNCTION(FSStatus,FSOpenDirAsync,FSClient *client,FSCmdBlock *block,const char *path,FSDirectoryHandle *handle,FSErrorFlag mask,FSAsyncData *async){ROUTE;RETURN_STATUS(real_FSOpenDirAsync(client,block,routed,handle,mask,async));}
WUPS_MUST_REPLACE(FSOpenFile,WUPS_LOADER_LIBRARY_COREINIT,FSOpenFile);
WUPS_MUST_REPLACE(FSOpenFileAsync,WUPS_LOADER_LIBRARY_COREINIT,FSOpenFileAsync);
WUPS_MUST_REPLACE(FSGetStat,WUPS_LOADER_LIBRARY_COREINIT,FSGetStat);
WUPS_MUST_REPLACE(FSGetStatAsync,WUPS_LOADER_LIBRARY_COREINIT,FSGetStatAsync);
WUPS_MUST_REPLACE(FSOpenDir,WUPS_LOADER_LIBRARY_COREINIT,FSOpenDir);
WUPS_MUST_REPLACE(FSOpenDirAsync,WUPS_LOADER_LIBRARY_COREINIT,FSOpenDirAsync);
