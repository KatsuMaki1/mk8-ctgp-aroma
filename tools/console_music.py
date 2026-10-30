"""Normalize a supplied BFSTM to the donor's channels/rate, retaining its loop.

Requires numpy and a user-local VGAudioCli executable. Uses the clean primary
stereo pair on every donor layer so layer changes cannot select empty channels.
"""
import argparse,json,math,struct,subprocess,tempfile,wave
from pathlib import Path
import numpy as np

def resample(samples,source_rate,target_rate):
    """Band-limited Fourier resampling, including the source Nyquist bin."""
    count=round(len(samples)*target_rate/source_rate)
    spectrum=np.fft.rfft(samples,axis=0)
    wanted=count//2+1
    if wanted>len(spectrum):
        original=len(spectrum)
        spectrum=np.pad(spectrum,((0,wanted-original),(0,0)))
        if len(samples)%2==0:spectrum[original-1]*=.5
    else:
        spectrum=spectrum[:wanted].copy()
        if count%2==0 and count<len(samples):spectrum[-1]*=2
    return np.fft.irfft(spectrum,n=count,axis=0)*(count/len(samples))

def metadata(data):
    if data[:4]!=b'FSTM' or data[4:6]!=b'\xfe\xff':raise ValueError('Expected big endian BFSTM')
    refs={struct.unpack_from('>H',data,20+12*i)[0]:struct.unpack_from('>II',data,24+12*i) for i in range(struct.unpack_from('>H',data,16)[0])}
    info=refs[0x4000][0];offset=info+8+struct.unpack_from('>I',data,info+12)[0]
    codec,loop,channels=struct.unpack_from('>BBB',data,offset)
    rate,start,end=struct.unpack_from('>III',data,offset+4)
    return {'codec':codec,'loop':loop,'channels':channels,'rate':rate,'start':start,'end':end,'seconds':end/rate}

def normalize(source,dest,encoder,channels=4,rate=32000):
    source,dest,encoder=map(Path,(source,dest,encoder));before=metadata(source.read_bytes())
    if channels%2 or channels<2:raise ValueError('Expected stereo channel pairs')
    with tempfile.TemporaryDirectory() as tmp:
        decoded=Path(tmp)/'decoded.wav';converted=Path(tmp)/'converted.wav'
        subprocess.run([str(encoder.resolve()),str(source.resolve()),str(decoded)],check=True,capture_output=True)
        with wave.open(str(decoded),'rb') as w:
            if w.getsampwidth()!=2:raise ValueError('Expected PCM16 decode')
            actual_rate=w.getframerate();original=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').reshape(-1,w.getnchannels())
        samples=original[:,:2].astype(np.float64)
        # Band-limit through Fourier truncation before downsampling; no aliasing
        # from a simple nearest/linear sample-rate conversion.
        count=round(len(samples)*rate/actual_rate)
        stereo=resample(samples,actual_rate,rate)*.7
        output=np.tile(np.clip(np.rint(stereo),-32768,32767).astype('<i2'),(1,channels//2))
        with wave.open(str(converted),'wb') as w:
            w.setnchannels(channels);w.setsampwidth(2);w.setframerate(rate);w.writeframes(output.tobytes())
        start=round(before['start']*rate/before['rate']);end=min(count,round(before['end']*rate/before['rate']))
        if before['loop'] and not 0<=start<end:raise ValueError('Invalid converted loop')
        cmd=[str(encoder.resolve()),str(converted),str(dest.resolve()),'-f','gcadpcm','--big-endian']
        cmd+=['-l',str(start)+'-'+str(end)] if before['loop'] else ['--no-loop']
        subprocess.run(cmd,check=True,capture_output=True)
        after=metadata(dest.read_bytes())
        if after['channels']!=channels or after['rate']!=rate or after['codec']!=2:raise ValueError('Output stream format mismatch')
        if before['loop'] and (not after['loop'] or abs(after['start']/rate-before['start']/before['rate'])>.5):raise ValueError('Loop changed unexpectedly')
        # Decode the new stream as an independent container/ADPCM validation.
        verify=Path(tmp)/'verified.wav';subprocess.run([str(encoder.resolve()),str(dest.resolve()),str(verify)],check=True,capture_output=True)
        with wave.open(str(verify),'rb') as w:
            a=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').reshape(-1,w.getnchannels()).astype(np.float64)/32768
        rms=np.sqrt(np.mean(a*a,axis=0))
        if np.min(rms)<.005:raise ValueError('A normalized channel is silent')
        return {'source':before,'output':after,'source_bytes':source.stat().st_size,'output_bytes':dest.stat().st_size,'channel_rms':rms.tolist(),'primary_stereo_repeated':True}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source');p.add_argument('output');p.add_argument('--encoder',required=True);p.add_argument('--channels',type=int,default=4);a=p.parse_args()
    report=normalize(a.source,a.output,a.encoder,a.channels);Path(a.output+'.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
