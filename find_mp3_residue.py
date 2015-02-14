#!env python
import sys,argparse,os,os.path,subprocess,tempfile,struct,itertools
emacs=os.getenv("EMACS") is not None

##########################################################################
##########################################################################
#
# inspired by http://ryanmaguiremusic.com/theghostinthemp3.html
#
##########################################################################
##########################################################################

g_verbose=False

def v(str):
    global g_verbose
    
    if g_verbose: sys.stdout.write(str)

def fatal(str):
    sys.stderr.write("FATAL: %s"%str)
    
    if emacs: raise RuntimeError
    else: sys.exit(1)

##########################################################################
##########################################################################
    
def get4s(s,i): return s[i:i+4]

def getnu(s,i,n):
    value=0

    for j in range(n): value|=ord(s[i+j])<<(j*8)

    return value

def get2u(s,i): return getnu(s,i,2)

def get4u(s,i): return getnu(s,i,4)

def get2i(s,i):
    x=get2u(s,i)
    
    if x&0x8000: x=(x&0x7fff)-32768
    
    return x
    

##########################################################################
##########################################################################

class WAV:
    def __init__(self):
        # Samples. Shorts, interleaved.
        self.samples=[]

        # Can be used to get the original data chunk back using
        # struct.pack. N.B., may be rather large.
        self.pack_fmt=None

        # Entirety of fmt chunk.
        self.fmt_chunk=None

def load_wav(wav_fname):
    
    with open(wav_fname,"rb") as f: data=f.read()

    if len(data)<12 or get4s(data,0)!="RIFF" or get4s(data,8)!="WAVE":
        print "Not a WAV file"
        return None

    riff_size=get4u(data,4)
    if riff_size>len(data)-8:
        print "Bad RIFF size"
        return None

    offset=12
    good=True

    wav=WAV()
    
    while offset<riff_size:
        name=get4s(data,offset+0)
        size=get4u(data,offset+4)

        if name=="fmt ":
            wFormatTag=get2u(data,offset+8+0)
            if wFormatTag!=1:#WAVE_FORMAT_PCM
                print "Not WAVE_FORMAT_PCM"
                return None

            nChannels=get2u(data,offset+8+2)
            nSamplesPerSec=get4u(data,offset+8+4)
            wBitsPerSample=get2u(data,offset+8+14)

            if nChannels!=2 or nSamplesPerSec!=44100 or wBitsPerSample!=16:
                print "Not stereo 16-bit 44.1KHz"
                return None

            wav.fmt_chunk=data[offset:offset+8+size]
        elif name=="data":
            if wav.fmt_chunk is None:
                print "Found data chunk without fmt"
                return None

            if size%4!=0:
                print "Data size not a multiple of 4 bytes"
                return None

            num_samples=size/4
            wav.pack_fmt="<"+2*num_samples*"h" # 'h'=signed short
            wav.samples=list(struct.unpack(wav.pack_fmt,data[offset+8:offset+8+size]))

            return wav

        offset+=8+size

        if offset%2!=0: offset+=1

    print "Didn't find data chunk"
    return None
        

def do_target(f,target,lame_prefix,iwav_fname,mp3_fname):
    owav_fname=os.path.splitext(mp3_fname)[0]+".wav"
    
    print>>f,".PHONY:%s"%target
    print>>f,"%s:"%target
    print>>f,"\t@%s --silent \"%s\" \"%s\""%(lame_prefix,iwav_fname,mp3_fname)
    print>>f,"\t@mpg123 -q -w \"%s\" \"%s\""%(owav_fname,mp3_fname)
    print>>f,"\t@rm \"%s\""%mp3_fname

    return owav_fname

def main(options):
    global g_verbose
    g_verbose=options.verbose

    tmp_prefix=os.path.join(tempfile.gettempdir(),str(os.getpid()))

    # Ensure the dest dir exists.
    if not os.path.isdir(options.dir): os.makedirs(options.dir)
    
    # Get an original WAV file.
    file_ext=os.path.splitext(options.wav_fname)[1]
    if file_ext==".flac":
        iwav_fname=tmp_prefix+".original.wav"
        iwav_is_temp=True
        ret=subprocess.call(["flac","-o",iwav_fname,"-d",options.wav_fname])
        if ret!=0: fatal("flac failed with exit code: %d\n"%ret)
    elif file_ext==".wav":
        iwav_fname=options.wav_fname
        iwav_is_temp=False
    else: fatal("file is of unknown type: %s\n"%options.file)

    v("Input: WAV file: %s\n"%iwav_fname)
    v("       WAV file is temp: %s\n"%("yes" if iwav_is_temp else "no"))

    # Check the WAV.
    iwav=load_wav(iwav_fname)
    if iwav is None: fatal("Can't process this WAV: %s\n"%iwav_fname)

    v("       %d samples\n"%len(iwav.samples))

    fname_stem=os.path.join(options.dir,os.path.splitext(os.path.split(options.wav_fname)[1])[0])
    v("File stem: %s\n"%fname_stem)

    # Compress at a variety of different CBR bitrates and VBR quality
    # settings. Do this via a Makefile and make -j, to get some
    # parallelism going.
    makefile_fname=os.path.join(options.dir,"residue_makefile")
    owav_fnames=[]
    with open(makefile_fname,"wt") as f:
        targets=[]
        
        for cbr_bitrate in [128,160,192,224,256,320]:
            target="cbr%d"%cbr_bitrate
            targets.append(target)
            
            mp3_fname=os.path.join(options.dir,"%s.cbr_%d.mp3"%(fname_stem,cbr_bitrate))

            owav_fnames.append(do_target(f,target,"lame --cbr -b %d"%cbr_bitrate,iwav_fname,mp3_fname))

        # -V 8 produces 22KHz output! Don't do that...
        for vbr_quality in [0,2,4,6]:
            target="vbr%d"%vbr_quality
            targets.append(target)

            mp3_fname=os.path.join(options.dir,"%s.vbr_%d.mp3"%(fname_stem,vbr_quality))

            owav_fnames.append(do_target(f,target,"lame -V %d"%vbr_quality,iwav_fname,mp3_fname))

        print>>f,".PHONY:all"
        print>>f,"all:%s"%(" ".join(targets))

    v("Compressing...\n")
    ret=subprocess.call(["make","-j","-f",makefile_fname,"all"])
    if ret!=0: fatal("make (compress) failed with exit code: %d\n"%ret)

    # Compare each output WAV's data chunk with the input WAV's data
    # chunk.
    for owav_fname in owav_fnames:
        v("Loading: %s\n"%owav_fname)

        owav=load_wav(owav_fname)
        if owav is None: fatal("Can't process WAV: %s\n"%owav_fname)

        v("    %d samples\n"%len(owav.samples))

        src=iwav.samples
        dest=owav.samples

        # I don't think it likely the dest will ever become shorter...
        if len(src)<len(dest): src=src[:]+[0]*(len(dest)-len(src))

        samples=[max(-32768,min(32767,x[1]-x[0])) for x in itertools.izip(src,dest)]

        v("    Processed.\n")

        # Make up a new WAV file from that.

        # New data chunk.
        data=struct.pack(owav.pack_fmt,*samples)
        data_chunk="data"+struct.pack("<I",len(data))+data

        wave="WAVE"+owav.fmt_chunk+data_chunk

        riff_data="RIFF"+struct.pack("<I",len(wave))+wave

        owav2_fname=os.path.splitext(owav_fname)[0]+".diff.wav"
        with open(owav2_fname,"wb") as f:
            f.write(riff_data)

        v("    Saved: %s\n"%owav2_fname)

    if iwav_is_temp: os.unlink(iwav_fname)
    
##########################################################################
##########################################################################

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="find MP3 residue")

    parser.add_argument("-v",
                        "--verbose",
                        action="store_true",
                        default=False,
                        help="If specified, verbosity")

    parser.add_argument("-d",
                        dest="dir",
                        default=".",
                        help="Specify dir to write files to. Default: ``%(default)s''")

    parser.add_argument("wav_fname",
                        metavar="FILE",
                        help="Path to FLAC or WAV file to process")

    args=sys.argv[1:]
        
    options=parser.parse_args(args)
    main(options)
