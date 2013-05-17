#!/usr/bin/python
import sys,argparse,wave,chunk,struct,shlex,os,os.path,subprocess,tempfile

##########################################################################
##########################################################################

# produce gaplessly-loopable MP3

# see http://www.compuphase.com/mp3/mp3loops.htm

##########################################################################
##########################################################################

g_verbose=False

##########################################################################
##########################################################################

def fatal(str):
    sys.stderr.write("FATAL: %s"%str)
    sys.exit(1)

##########################################################################
##########################################################################

def get4s(s,i):
    return s[i:i+4]

##########################################################################
##########################################################################

def getnu(s,i,n):
    value=0

    for j in range(n):
        value|=ord(s[i+j])<<(j*8)

    return value

##########################################################################
##########################################################################
    
def get2u(s,i):
    return getnu(s,i,2)

##########################################################################
##########################################################################
    
def get4u(s,i):
    return getnu(s,i,4)

##########################################################################
##########################################################################

def commas(x):
    return "{:,}".format(x)

##########################################################################
##########################################################################

def v(str):
    global g_verbose
    
    if g_verbose:
        sys.stdout.write(str)

##########################################################################
##########################################################################

def load_wav_chunks(wav_file_name):
    """Load WAV file and return WAV chunks data - map of string, chunk ID, to string, chunk data."""
    f=open(wav_file_name,
           "rb")
    wav_data=f.read()
    f.close()
    del f

    if len(wav_data)<12 or get4s(wav_data,0)!="RIFF" or get4s(wav_data,8)!="WAVE":
        fatal("%s: not a WAV file.\n"%wav_file_name)

    v("%s: %s bytes.\n"%(wav_file_name,commas(len(wav_data))))

    chunks={}

    riff_size=get4u(wav_data,4)

    if riff_size<=len(wav_data)-8:
        chunk_offset=12
        good=1

        while chunk_offset<riff_size:
            chunk_name=get4s(wav_data,chunk_offset+0)
            chunk_size=get4u(wav_data,chunk_offset+4)

            if chunks.has_key(chunk_name):
                fatal("%s: multiple '%s' chunks.\n"%(wav_file_name,chunk_name))

            chunks[chunk_name]=wav_data[chunk_offset+8:chunk_offset+8+chunk_size]
            v("    '%s': %s bytes\n"%(chunk_name,commas(chunk_size)))

            chunk_offset+=8+chunk_size

            if chunk_size%2!=0:
                chunk_offset+=1

        assert chunk_offset==riff_size+8

    return chunks

##########################################################################
##########################################################################

def remove_unwanted_chunks(wav_chunks,file_name):
    """Remove unnecessary chunks from the WAV chunk data."""
    for key in wav_chunks.keys():
        if key=="fmt " or key=="data":
            continue

        v("Removing '%s' chunk.\n"%key)
        del wav_chunks[key]
    
##########################################################################
##########################################################################

class Format:
    def __init__(self,
                 fmt):
        self.wFormatTag=get2u(fmt,0)
        self.nChannels=get2u(fmt,2)
        self.nSamplesPerSec=get4u(fmt,4)
        self.nAvgBytesPerSec=get4u(fmt,8)
        self.nBlockAlign=get2u(fmt,12)
        self.wBitsPerSample=get2u(fmt,14)

    def get_bytes_per_sample(self):
        return self.wBitsPerSample/8*self.nChannels

##########################################################################
##########################################################################

def get_wav_fmt(wav_chunks):
    fmt=Format(wav_chunks["fmt "])

    if fmt.wFormatTag!=1:
        fatal("%s: not WAVE_FORMAT_PCM.\n"%file_name)

    return fmt
        
##########################################################################
##########################################################################
        
# def get_bytes_per_sample(wav_chunks,dump=False):
#     fmt=wav_chunks["fmt "]
    
#     if len(fmt)<16:
#         fatal("%s: bad 'fmt ' chunk.\n"%file_name)

#     wFormatTag=get2u(fmt,0)
#     nChannels=get2u(fmt,2)
#     nSamplesPerSec=get4u(fmt,4)
#     nAvgBytesPerSec=get4u(fmt,8)
#     nBlockAlign=get2u(fmt,12)
#     wBitsPerSample=get2u(fmt,14)

#     if dump:
#         v("Format:\n")
#         v("    wFormatTag=%d (0x%X)\n"%(wFormatTag,wFormatTag))
#         v("    nChannels=%d (0x%X)\n"%(nChannels,nChannels))
#         v("    nSamplesPerSec=%d (0x%X)\n"%(nSamplesPerSec,nSamplesPerSec))
#         v("    nAvgBytesPerSec=%d (0x%X)\n"%(nAvgBytesPerSec,nAvgBytesPerSec))
#         v("    nBlockAlign=%d (0x%X)\n"%(nBlockAlign,nBlockAlign))
#         v("    wBitsPerSample=%d (0x%X)\n"%(wBitsPerSample,wBitsPerSample))
    
#     if wFormatTag!=1:
#         fatal("%s: not WAVE_FORMAT_PCM.\n"%file_name)

#     return nChannels*wBitsPerSample/8
        
def resize_data_chunk(wav_chunks,file_name):
    """Alter the WAV chunk data's data chunk so that it is exactly
    1,152 samples in length.

    """
    data=wav_chunks["data"]
    fmt=get_wav_fmt(wav_chunks)

    bytes_per_sample=fmt.get_bytes_per_sample()
    num_samples=len(data)/bytes_per_sample
    v("%s samples total.\n"%commas(num_samples))
    
    if num_samples%1152==0:
        # OK.
        v("WAV is already of the right length.\n")
        return

    num_extra_samples=1152-num_samples%1152
    v("%s extra samples required.\n"%commas(num_extra_samples))

    new_data=""

    step=num_samples/num_extra_samples*bytes_per_sample

    for i in range(num_extra_samples):
        new_data+=data[i*step:i*step+step]

        # replicate last sample. this is very difficult to spot for
        # music.
        new_data+=new_data[-bytes_per_sample:]

    new_data+=data[num_extra_samples*step:]
    new_num_samples=len(new_data)/bytes_per_sample
    v("%s samples now.\n"%commas(new_num_samples))
    assert new_num_samples%1152==0
    
##########################################################################
##########################################################################

def get_wav_chunk_data(name,data):
    assert len(name)==4

    return name+struct.pack("<I",len(data))+data

def get_wav_data(wav_chunks):
    """Return a string, the contents of the WAV file containing the
    format and data chunks from the given WAV chunks data.

    """
    return get_wav_chunk_data("RIFF",
                              "WAVE"+get_wav_chunk_data("fmt ",wav_chunks["fmt "])+get_wav_chunk_data("data",wav_chunks["data"]))
    
# def save_wav_file(wav_chunks,
#                   wav_file_name):

#     v("Saving \"%s\" (%s bytes)...\n"%(wav_file_name,commas(len(wav_data))))

#     folder_name=os.path.dirname(wav_file_name)
#     if not os.path.isdir(folder_name):
#         os.makedirs(folder_name)
    
#     f=open(wav_file_name,
#            "wb")
#     f.write(wav_data)
#     f.close()
#     del f

##########################################################################
##########################################################################

def rearrange_data_chunk(chunks):
    """Prepend silence to data chunk, corresponding to encoder delay,
    and last 1,152 samples, to cater for frame overlap.

    """
    
    fmt=Format(chunks["fmt "])

    if fmt.wBitsPerSample==8:
        silence=chr(0x80)
    elif fmt.wBitsPerSample==16:
        silence=chr(0)+chr(0)

    silence*=fmt.nChannels
    
    chunks["data"]=576*silence+chunks["data"][-(1152*fmt.nChannels*fmt.wBitsPerSample/8):]+chunks["data"]

##########################################################################
##########################################################################

# this should realy use subprocess.Popen.communicate, but it didn't
# seem to work properly - the resulting MP3 was a frame or two
# short. Using temp files works fine. Should really figure out which
# component is to blame, but... time...
    
def get_mp3_data(wav_data,
                 lame_args):
    """Compress WAV to MP3, and return MP3 data."""
    wav_name=os.path.join(tempfile.gettempdir(),"looping_tmp.wav")
    mp3_name=os.path.join(tempfile.gettempdir(),"looping_tmp.mp3")
        
    f=open(wav_name,"wb")
    f.write(wav_data)
    f.close()
    del f
    
    lame=["lame"]
    lame+=lame_args
    lame.append("--nores")
    lame.append(wav_name)
    lame.append(mp3_name)

    print lame

    ret=subprocess.call(lame)

    if ret!=0:
        fatal("lame failed. (exit code=%d)\n"%ret)

    f=open(mp3_name,"rb")
    mp3_data=f.read()
    f.close()
    del f

    os.unlink(mp3_name)
    os.unlink(wav_name)

    return mp3_data

##########################################################################
##########################################################################

def get_trimmed_mp3(mp3_data):
    """Remove chunks from MP3, partly to undo the data added by
    rearrange_data_chunk, and partly to get rid of some extra junk
    that LAME adds.

    """
    
    # f=open(mp3_file_name,"rb")
    # mp3_data=f.read()
    # f.close()
    # del f

    # bits	V1,L1	V1,L2	V1,L3	V2,L1	V2, L2 & L3
    # 0000	free	free	free	free	free
    # 0001	32	32	32	32	8
    # 0010	64	48	40	48	16
    # 0011	96	56	48	56	24
    # 0100	128	64	56	64	32
    # 0101	160	80	64	80	40
    # 0110	192	96	80	96	48
    # 0111	224	112	96	112	56
    # 1000	256	128	112	128	64
    # 1001	288	160	128	144	80
    # 1010	320	192	160	160	96
    # 1011	352	224	192	176	112
    # 1100	384	256	224	192	128
    # 1101	416	320	256	224	144
    # 1110	448	384	320	256	160
    # 1111	bad	bad	bad	bad	bad
    sample_rates=[None,32000,40000,48000,56000,64000,80000,96000,112000,128000,160000,192000,224000,256000,320000,None]
    sample_freqs=[44100,48000,32000,None]

    frames=[]#(begin,end)

    num_frames=0
    frame_start_index=0
    while frame_start_index<len(mp3_data):
        header=[ord(x) for x in mp3_data[frame_start_index:frame_start_index+4]]

        # AAAAAAAA AAABBCCD EEEEFFGH IIJJKLMM

        a=(header[0]<<3)|(header[1]>>5)
        b=(header[1]>>3)&3
        c=(header[1]>>1)&3
        #d=header[1]&1
        e=(header[2]>>4)&15
        f=(header[2]>>2)&3
        g=(header[2]>>1)&1
        #h=header[2]&1
        #i=(header[3]>>6)&3
        #j=(header[3]>>4)&3
        #k=(header[3]>>3)&1
        #l=(header[3]>>2)&1
        #m=header[3]&3

        if a!=2047:
            fatal("%s: +%d: bad frame sync.\n"%(mp3_file_name,frame_start_index))

        if b!=3:
            fatal("%s: +%d: not MPEG Version 1.\n"%(mp3_file_name,frame_start_index))

        if c!=1:
            fatal("%s: +%d: not Layer 3.\n"%(mp3_file_name,frame_start_index))

        rate=sample_rates[e]
        if rate is None:
            fatal("%s: +%d: bad sample rate.\n"%(mp3_file_name,frame_start_index))

        freq=sample_freqs[f]
        if freq is None:
            fatal("%s: +%d: bad sample frequency.\n"%(mp3_file_name,frame_start_index))

        #print rate,freq,g
        #sys.exit(1)

        len_bytes=144*rate/freq+g
        #print len_bytes,frame_start_index

        frames.append((frame_start_index,
                       frame_start_index+len_bytes))

        num_frames+=1
        frame_start_index+=len_bytes

    # remove first 3 frames - info junk, encoder delay + silence, loop prefix
    del frames[0]
    del frames[0]
    del frames[0]

    # remove last frame of silence
    del frames[-1]

    # rebuild mp3 data
    new_mp3_data=""
    for frame in frames:
        new_mp3_data+=mp3_data[frame[0]:frame[1]]

    return new_mp3_data

    # # save it...
    # f=open(mp3_file_name,"wb")
    # f.write(new_mp3_data)
    # f.close()
    # del f

##########################################################################
##########################################################################

def get_cues(wav_chunks):
    data=wav_chunks.get("cue ")
    if data is None:
        return None

    fmt=get_wav_fmt(wav_chunks)
    
    cues=[]
    n=get4u(data,0)

    for i in range(n):
        offset=4+i*24
        
        cue_id=get4u(data,offset+0)
        pos=get4u(data,offset+4)
        chunk_id=get4s(data,offset+8)
        chunk_start=get4u(data,offset+12)
        block_start=get4u(data,offset+16)
        sample_offset=get4u(data,offset+20)

        if chunk_id!="data" or chunk_start!=0 or block_start!=0:
            fatal("unsupported cue found")

        cues.append(pos/float(fmt.nSamplesPerSec))

    return cues
    
##########################################################################
##########################################################################
    
def main(args):
    global g_verbose
    g_verbose=args.verbose

    #print args.wav_file

    lame_args=[]
    if args.lame_args is not None:
        for lame_arg in args.lame_args:
            lame_args+=shlex.split(lame_arg)

    #print lame_args

    wav_chunks=load_wav_chunks(args.wav_file)

    cues=get_cues(wav_chunks)

    remove_unwanted_chunks(wav_chunks,
                           args.wav_file)
    
    resize_data_chunk(wav_chunks,
                      args.wav_file)

    rearrange_data_chunk(wav_chunks)

    mp3_data=get_trimmed_mp3(get_mp3_data(get_wav_data(wav_chunks),
                                          lame_args))

    if args.output:
        f=open(args.output,"wb")
        f.write(mp3_data)
        f.close()
        del f

        if cues is not None:
            f=open(os.path.splitext(args.output)[0]+".txt",
                   "wt")
            
            f.write("cues.n=%d\n"%len(cues))
            
            for i in range(len(cues)):
                f.write("cues[%d]=%f\n"%(i,cues[i]))
                
            f.close()
            del f

##########################################################################
##########################################################################

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="make perfectly-looping MP3 from WAV file.")

    parser.add_argument("-v",
                        "--verbose",
                        action="store_true",
                        default=False,
                        help="If specified, verbosity.")

    parser.add_argument("-a",
                        "--lame-arg",
                        metavar="ARGS",
                        dest="lame_args",
                        action="append",
                        help="Specify argument(s) for LAME.")

    parser.add_argument("-o",
                        "--output",
                        metavar="MP3-FILE",
                        default=None,
                        help="Specify output file.")

    parser.add_argument("wav_file",
                        metavar="WAV-FILE",
                        help="Path to WAV file to process.")

    result=parser.parse_args()
    main(result)
    
