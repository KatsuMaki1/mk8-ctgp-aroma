/* Trace of the game's NEX protocol clients: every RMC message that reaches a protocol client's dispatcher is counted by
 * (protocol, method id). Dispatchers (each reads the method id with 02962EEC(message) and indexes a handler table):
 *   Ranking 029C3A44 (16 methods), DataStore 029AFBEC (42), MatchmakeExtension 029917D8 (40).
 * Read-only observation: the message is passed on unchanged. 64 distinct keys are kept, newest replace oldest. */
struct NexTrace {u32 protocol,method,hits,sequence;};
volatile struct NexTrace nex_trace[64];
volatile u32 nex_trace_next,nex_trace_total;
static void nex_note(u32 protocol,u32 message){
 u32 raw=FN(0x2962eec,u32(*)(u32))(message),i=0;
 for(;i<64;i++)if(nex_trace[i].hits&&nex_trace[i].protocol==protocol&&nex_trace[i].method==raw)break;
 if(i==64){i=nex_trace_next&63;nex_trace_next++;nex_trace[i].protocol=protocol;nex_trace[i].method=raw;nex_trace[i].hits=0;}
 nex_trace[i].hits++;nex_trace[i].sequence=++nex_trace_total;
}
/* Pass all argument registers through and return the original result: the dispatchers' real signature is unknown. */
extern u32 original_nex_ranking_dispatch(u32,u32,u32,u32,u32,u32);
extern u32 original_nex_datastore_dispatch(u32,u32,u32,u32,u32,u32);
extern u32 original_nex_matchmake_dispatch(u32,u32,u32,u32,u32,u32);
u32 nex_ranking_dispatch(u32 a,u32 b,u32 c,u32 d,u32 e,u32 f){nex_note(1,b);return original_nex_ranking_dispatch(a,b,c,d,e,f);}
u32 nex_datastore_dispatch(u32 a,u32 b,u32 c,u32 d,u32 e,u32 f){nex_note(2,b);return original_nex_datastore_dispatch(a,b,c,d,e,f);}
u32 nex_matchmake_dispatch(u32 a,u32 b,u32 c,u32 d,u32 e,u32 f){nex_note(3,b);return original_nex_matchmake_dispatch(a,b,c,d,e,f);}
