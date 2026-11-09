import ghidra.app.script.GhidraScript;
import java.io.ByteArrayInputStream;
import java.nio.file.Files;
import java.nio.file.Paths;

// Read-only headless analysis helper: add the appended CTGP module to native text.
public class LoadTTModule extends GhidraScript {
 public void run() throws Exception {
  String[] args=getScriptArgs();
  if(currentProgram.getMemory().getBlock("tt_ctgp_text")==null){
   byte[] code=Files.readAllBytes(Paths.get(args[0]));
   currentProgram.getMemory().createInitializedBlock("tt_ctgp_text",toAddr(0x02b10000L),new ByteArrayInputStream(code),code.length,monitor,false).setExecute(true);
  }
  if(currentProgram.getMemory().getBlock("tt_ctgp_data")==null){
   byte[] data=Files.readAllBytes(Paths.get(args[1]));
   currentProgram.getMemory().createInitializedBlock("tt_ctgp_data",toAddr(0x10300000L),new ByteArrayInputStream(data),data.length,monitor,false);
  }
 }
}
