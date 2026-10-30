#ifdef CTGP_DIAGNOSTIC_ONLY
#include <wups.h>
#include <wups/config/WUPSConfigItemStub.h>
#include <coreinit/filesystem.h>
#include <coreinit/title.h>
#include <coreinit/memorymap.h>
#include <coreinit/dynload.h>
#include <content_redirection/redirection.h>
#include <notifications/notifications.h>
#include <cstdio>
#include <cstring>

WUPS_PLUGIN_NAME("CTGP-Cafe Loader");
WUPS_PLUGIN_DESCRIPTION("Diagnostic only: no code injection or content redirection");
WUPS_PLUGIN_VERSION("v0.12-diagnostic");
WUPS_PLUGIN_AUTHOR("KatsuMaki1");
WUPS_PLUGIN_LICENSE("MIT");
// Deliberately no WUT filesystem devoptab or stdio file operations.
// Test the native coreinit FS API independently of the v0.5 changes.

alignas(64) static FSClient client;
alignas(64) static FSCmdBlock command;
alignas(64) static FSStat statBuffer;
alignas(64) static char report[1024];
alignas(64) static uint8_t verifyBytes[65536];
static char memoryLine[200]="Memory probe not run";
static char bytesLine[200]="Byte comparison not run";
static char destinationLine[200]="Destination probe not run";
static uint32_t read32(const uint8_t *p) {
    return (uint32_t(p[0])<<24)|(uint32_t(p[1])<<16)|(uint32_t(p[2])<<8)|p[3];
}
// Check every page before reading. This does not establish ownership or permit writes.
static bool mappedRange(uint32_t at,uint32_t len) {
    if(!len || at>UINT32_MAX-(len-1))return false;
    uint32_t last=at+len-1;
    if(!OSEffectiveToPhysical(at) || !OSEffectiveToPhysical(last))return false;
    for(uint32_t page=(at&~0xFFFu);page<(last&~0xFFFu);) {
        page+=0x1000;
        if(!OSEffectiveToPhysical(page))return false;
    }
    return true;
}
static void probeDestinations() {
    FSFileHandle handle;
    FSInitCmdBlock(&command);
    auto status=FSOpenFile(&client,&command,"/vol/external01/cafeloader/000500001010ED00/Addr.bin","r",&handle,FS_ERROR_FLAG_ALL);
    if(status<0) {snprintf(destinationLine,sizeof destinationLine,"Addr open=%d",int(status));return;}
    FSInitCmdBlock(&command);
    auto bytes=FSReadFile(&client,&command,verifyBytes,1,64,handle,0,FS_ERROR_FLAG_ALL);
    FSInitCmdBlock(&command);FSCloseFile(&client,&command,handle,FS_ERROR_FLAG_ALL);
    if(bytes!=8) {snprintf(destinationLine,sizeof destinationLine,"Addr size=%d (expected 8)",int(bytes));return;}
    uint32_t code=read32(verifyBytes),data=read32(verifyBytes+4);
    snprintf(destinationLine,sizeof destinationLine,"Dest code=%08X phys=%08X data=%08X phys=%08X",code,OSEffectiveToPhysical(code),data,OSEffectiveToPhysical(data));
}
// Read-only byte comparison; never install patches or content layers.
static void probePack() {
    FSFileHandle handle;
    FSInitCmdBlock(&command);
    auto status=FSOpenFile(&client,&command,"/vol/external01/cafeloader/000500001010ED00/Verify.hax","r",&handle,FS_ERROR_FLAG_ALL);
    if(status<0) {snprintf(memoryLine,sizeof memoryLine,"Verify read open=%d",int(status));return;}
    FSInitCmdBlock(&command);
    auto bytes=FSReadFile(&client,&command,verifyBytes,1,sizeof verifyBytes,handle,0,FS_ERROR_FLAG_ALL);
    FSInitCmdBlock(&command);FSCloseFile(&client,&command,handle,FS_ERROR_FLAG_ALL);
    if(bytes<2 || bytes==sizeof verifyBytes) {snprintf(memoryLine,sizeof memoryLine,"Invalid Verify size=%d",int(bytes));return;}
    uint32_t count=(verifyBytes[0]<<8)|verifyBytes[1],pos=2,mapped=0,originalMapped=0,first=0;
    uint32_t matches=0,firstBad=0,actual=0,expected=0;
    for(uint32_t i=0;i<count;i++) {
        if(pos+6>uint32_t(bytes)) {snprintf(memoryLine,sizeof memoryLine,"Truncated Verify entry %u",i);return;}
        uint32_t len=(verifyBytes[pos]<<8)|verifyBytes[pos+1],at=read32(verifyBytes+pos+2);pos+=6;
        if(!len || pos+len>uint32_t(bytes) || at>UINT32_MAX-(len-1)) {snprintf(memoryLine,sizeof memoryLine,"Invalid Verify entry %u",i);return;}
        if(!i)first=at;
        if(mappedRange(at,len)) {
            mapped++;
            bool equal=true;
            auto memory=reinterpret_cast<volatile const uint8_t*>(at);
            for(uint32_t j=0;j<len;j++) {
                uint8_t value=memory[j];
                if(value!=verifyBytes[pos+j]) {
                    equal=false;
                    if(!firstBad) {firstBad=at+j;actual=value;expected=verifyBytes[pos+j];}
                    break;
                }
            }
            if(equal)matches++;
        }
        if(at>=0x0E180000 && at<0x0ED80000) {
            uint32_t original=at-0x0C180000;
            if(OSEffectiveToPhysical(original) && OSEffectiveToPhysical(original+len-1))originalMapped++;
        }
        pos+=len;
    }
    if(pos!=uint32_t(bytes)) {snprintf(memoryLine,sizeof memoryLine,"Trailing Verify bytes: %u",uint32_t(bytes)-pos);return;}
    snprintf(memoryLine,sizeof memoryLine,"Verify %u: mapped=%u RPX=%u first=%08X",count,mapped,originalMapped,first);
    snprintf(bytesLine,sizeof bytesLine,"Bytes match=%u/%u bad=%08X got=%02X expected=%02X",matches,count,firstBad,actual,expected);
}
static char titleLine[80]="MK8 not launched yet";
static char resultLine[200]="Diagnostic ready; no patches are applied";
static bool notifications;
static bool redirectionReady;
static char moduleLine[200]="Content module not tested";
static char kernelLine[200]="Kernel export not tested; never called";

// Close each checkpoint before calling the module so a later crash cannot
// discard a userspace stdio buffer. The config line also reports FS failures.
static bool checkpoint(const char *text) {
    FSFileHandle file;
    FSInitCmdBlock(&command);
    auto status=FSOpenFile(&client,&command,"/vol/external01/ctgp-module-test.txt","a",&file,FS_ERROR_FLAG_ALL);
    if(status<0) {snprintf(moduleLine,sizeof moduleLine,"Checkpoint open=%d; module test skipped",int(status));return false;}
    snprintf(report,sizeof report,"%s\n",text);
    FSInitCmdBlock(&command);
    auto written=FSWriteFile(&client,&command,(uint8_t*)report,1,strlen(report),file,0,FS_ERROR_FLAG_ALL);
    FSInitCmdBlock(&command);
    auto closed=FSCloseFile(&client,&command,file,FS_ERROR_FLAG_ALL);
    if(written!=int(strlen(report)) || closed<0) {
        snprintf(moduleLine,sizeof moduleLine,"Checkpoint write=%d close=%d; module test skipped",int(written),int(closed));return false;
    }
    return true;
}

static WUPSConfigAPICallbackStatus opened(WUPSConfigCategoryHandle root) {
    auto a=WUPSConfigItemStub_AddToCategory(root,"v0.12 diagnostic - CTGP injection disabled");
    auto b=WUPSConfigItemStub_AddToCategory(root,titleLine);
    auto c=WUPSConfigItemStub_AddToCategory(root,resultLine);
    auto d=WUPSConfigItemStub_AddToCategory(root,memoryLine);
    auto e=WUPSConfigItemStub_AddToCategory(root,bytesLine);
    auto f=WUPSConfigItemStub_AddToCategory(root,destinationLine);
    auto g=WUPSConfigItemStub_AddToCategory(root,moduleLine);
    auto h=WUPSConfigItemStub_AddToCategory(root,kernelLine);
    return a==WUPSCONFIG_API_RESULT_SUCCESS && b==WUPSCONFIG_API_RESULT_SUCCESS && c==WUPSCONFIG_API_RESULT_SUCCESS && d==WUPSCONFIG_API_RESULT_SUCCESS && e==WUPSCONFIG_API_RESULT_SUCCESS && f==WUPSCONFIG_API_RESULT_SUCCESS && g==WUPSCONFIG_API_RESULT_SUCCESS && h==WUPSCONFIG_API_RESULT_SUCCESS
        ? WUPSCONFIG_API_CALLBACK_RESULT_SUCCESS:WUPSCONFIG_API_CALLBACK_RESULT_ERROR;
}
static void closed() {}

INITIALIZE_PLUGIN() {
    WUPSConfigAPIOptionsV1 options={.name="CTGP diagnostic v0.12"};
    WUPSConfigAPI_Init(options,opened,closed);
}

ON_APPLICATION_START() {
    uint64_t title=OSGetTitleID();
    snprintf(titleLine,sizeof titleLine,"Title: %016llX",(unsigned long long)title);
    if(title!=0x000500001010ED00ull && title!=0x000500001010EC00ull && title!=0x000500001010EB00ull) {
        snprintf(resultLine,sizeof resultLine,"Not a supported MK8 title; no SD access or patches");return;
    }
    notifications=NotificationModule_InitLibrary()==NOTIFICATION_MODULE_RESULT_SUCCESS;
    if(notifications)NotificationModule_AddInfoNotification("CTGP v0.12 diagnostic active - no patches");
    FSInit();
    FSStatus added=FSAddClient(&client,FS_ERROR_FLAG_ALL);
    if(added<0) {
        snprintf(resultLine,sizeof resultLine,"FSAddClient=%d; no patches",(int)added);
        if(notifications)NotificationModule_AddErrorNotification(resultLine);
        return;
    }
    FSInitCmdBlock(&command);
    FSStatus rootStatus=FSGetStat(&client,&command,"/vol/external01",&statBuffer,FS_ERROR_FLAG_ALL);
    FSInitCmdBlock(&command);
    FSStatus packStatus=FSGetStat(&client,&command,"/vol/external01/cafeloader/000500001010ED00/Verify.hax",&statBuffer,FS_ERROR_FLAG_ALL);
    FSInitCmdBlock(&command);
    FSStatus cupStatus=FSGetStat(&client,&command,"/vol/external01/cafeloader/vol/000500001010ED00/content/data.cup0",&statBuffer,FS_ERROR_FLAG_ALL);
    probePack();
    probeDestinations();
    FSFileHandle file;
    FSInitCmdBlock(&command);
    FSStatus openedFile=FSOpenFile(&client,&command,"/vol/external01/wiiu/mk8-ct/log.txt","a",&file,FS_ERROR_FLAG_ALL);
    if(openedFile<0) {
        FSInitCmdBlock(&command);
        openedFile=FSOpenFile(&client,&command,"/vol/external01/ctgp-diag.txt","a",&file,FS_ERROR_FLAG_ALL);
    }
    snprintf(resultLine,sizeof resultLine,"SD=%d Verify=%d Cups=%d LogOpen=%d; no patches",(int)rootStatus,(int)packStatus,(int)cupStatus,(int)openedFile);
    if(openedFile>=0) {
        snprintf(report,sizeof report,"CTGP v0.12 diagnostic only\n%s\n%s\n%s\n%s\n%s\nNo game code modified; no content layers.\n",titleLine,resultLine,memoryLine,bytesLine,destinationLine);
        FSInitCmdBlock(&command);
        FSStatus written=FSWriteFile(&client,&command,(uint8_t*)report,1,strlen(report),file,0,FS_ERROR_FLAG_ALL);
        FSInitCmdBlock(&command);FSCloseFile(&client,&command,file,FS_ERROR_FLAG_ALL);
        if(written<0)snprintf(resultLine,sizeof resultLine,"SD=%d Verify=%d Cups=%d LogWrite=%d; no patches",(int)rootStatus,(int)packStatus,(int)cupStatus,(int)written);
    }
    if(checkpoint("v0.12: BEFORE ContentRedirection_InitLibrary; no patches or layers")) {
        auto status=ContentRedirection_InitLibrary();
        redirectionReady=status==CONTENT_REDIRECTION_RESULT_SUCCESS;
        snprintf(moduleLine,sizeof moduleLine,"ContentRedirection init=%d; no patches/layers",int(status));
        checkpoint(moduleLine);
    }
    if(checkpoint("v0.12: BEFORE kernel module lookup; function will NOT be called")) {
        OSDynLoad_Module kernel=0;
        auto loaded=OSDynLoad_IsModuleLoaded("homebrew_kernel",&kernel);
        void *function=nullptr;
        if(loaded==OS_DYNLOAD_OK) {
            auto found=OSDynLoad_FindExport(kernel,OS_DYNLOAD_EXPORT_FUNC,"KernelCopyData",&function);
            snprintf(kernelLine,sizeof kernelLine,"Kernel loaded=%08X export=%08X ptr=%08X; NOT called",unsigned(loaded),unsigned(found),unsigned(uintptr_t(function)));
        } else {
            snprintf(kernelLine,sizeof kernelLine,"Kernel loaded=%08X; lookup stopped, NOT called",unsigned(loaded));
        }
        checkpoint(kernelLine);
    }
    FSDelClient(&client,FS_ERROR_FLAG_ALL);
    if(notifications)NotificationModule_AddInfoNotification(resultLine);
}

ON_APPLICATION_ENDS() {
    if(redirectionReady) {ContentRedirection_DeInitLibrary();redirectionReady=false;}
    if(notifications) {NotificationModule_DeInitLibrary();notifications=false;}
}
#endif
