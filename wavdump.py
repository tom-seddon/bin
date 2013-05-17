#!/usr/bin/python
import sys,argparse

# http://www.sonicspot.com/guide/wavefiles.html

g_verbose=False

def fatal(str):
    sys.stderr.write("FATAL: %s"%str)
    sys.exit(1)

def v(str):
    global g_verbose
    
    if g_verbose:
        sys.stdout.write(str)

def get4s(s,i):
    return s[i:i+4]

def getnu(s,i,n):
    value=0

    for j in range(n):
        value|=ord(s[i+j])<<(j*8)

    return value

def get2u(s,i):
    return getnu(s,i,2)

def get4u(s,i):
    return getnu(s,i,4)

def commas(x):
    return "{:,}".format(x)

class Chunk:
    def __init__(self,
                 fourcc,
                 data):
        self.fourcc=fourcc
        self.data=data

def load_wav_chunks(wav_file_name):
    f=open(wav_file_name,
           "rb")
    wav_data=f.read()
    f.close()
    del f

    if len(wav_data)<12 or get4s(wav_data,0)!="RIFF" or get4s(wav_data,8)!="WAVE":
        fatal("%s: not a WAV file.\n"%wav_file_name)

    v("%s: %s bytes.\n"%(wav_file_name,commas(len(wav_data))))

    chunks=[]

    riff_size=get4u(wav_data,4)

    if riff_size<=len(wav_data)-8:
        chunk_offset=12
        good=1

        while chunk_offset<riff_size:
            chunk_name=get4s(wav_data,chunk_offset+0)
            chunk_size=get4u(wav_data,chunk_offset+4)

            # if chunks.has_key(chunk_name):
            #     fatal("%s: multiple '%s' chunks.\n"%(wav_file_name,chunk_name))

            chunk_data=wav_data[chunk_offset+8:chunk_offset+8+chunk_size]
            v("    '%s': %s bytes\n"%(chunk_name,commas(chunk_size)))

            chunks.append(Chunk(chunk_name,
                                chunk_data))

            chunk_offset+=8+chunk_size

            if chunk_size%2!=0:
                chunk_offset+=1

        assert chunk_offset==riff_size+8,(hex(chunk_offset),hex(riff_size))

    return chunks

##########################################################################
##########################################################################

wave_format_tag_names={
    0x0000:"WAVE_FORMAT_UNKNOWN",0x0001:"WAVE_FORMAT_PCM",0x0002:"WAVE_FORMAT_ADPCM",0x0003:"WAVE_FORMAT_IEEE_FLOAT",0x0004:"WAVE_FORMAT_VSELP",0x0005:"WAVE_FORMAT_IBM_CVSD",0x0006:"WAVE_FORMAT_ALAW",0x0007:"WAVE_FORMAT_MULAW",0x0008:"WAVE_FORMAT_DTS",0x0009:"WAVE_FORMAT_DRM",0x000A:"WAVE_FORMAT_WMAVOICE9",0x000B:"WAVE_FORMAT_WMAVOICE10",0x0010:"WAVE_FORMAT_OKI_ADPCM",0x0011:"WAVE_FORMAT_DVI_ADPCM",0x0012:"WAVE_FORMAT_MEDIASPACE_ADPCM",0x0013:"WAVE_FORMAT_SIERRA_ADPCM",0x0014:"WAVE_FORMAT_G723_ADPCM",0x0015:"WAVE_FORMAT_DIGISTD",0x0016:"WAVE_FORMAT_DIGIFIX",0x0017:"WAVE_FORMAT_DIALOGIC_OKI_ADPCM",0x0018:"WAVE_FORMAT_MEDIAVISION_ADPCM",0x0019:"WAVE_FORMAT_CU_CODEC",0x0020:"WAVE_FORMAT_YAMAHA_ADPCM",0x0021:"WAVE_FORMAT_SONARC",0x0022:"WAVE_FORMAT_DSPGROUP_TRUESPEECH",0x0023:"WAVE_FORMAT_ECHOSC1",0x0024:"WAVE_FORMAT_AUDIOFILE_AF36",0x0025:"WAVE_FORMAT_APTX",0x0026:"WAVE_FORMAT_AUDIOFILE_AF10",0x0027:"WAVE_FORMAT_PROSODY_1612",0x0028:"WAVE_FORMAT_LRC",0x0030:"WAVE_FORMAT_DOLBY_AC2",0x0031:"WAVE_FORMAT_GSM610",0x0032:"WAVE_FORMAT_MSNAUDIO",0x0033:"WAVE_FORMAT_ANTEX_ADPCME",0x0034:"WAVE_FORMAT_CONTROL_RES_VQLPC",0x0035:"WAVE_FORMAT_DIGIREAL",0x0036:"WAVE_FORMAT_DIGIADPCM",0x0037:"WAVE_FORMAT_CONTROL_RES_CR10",0x0038:"WAVE_FORMAT_NMS_VBXADPCM",0x0039:"WAVE_FORMAT_CS_IMAADPCM",0x003A:"WAVE_FORMAT_ECHOSC3",0x003B:"WAVE_FORMAT_ROCKWELL_ADPCM",0x003C:"WAVE_FORMAT_ROCKWELL_DIGITALK",0x003D:"WAVE_FORMAT_XEBEC",0x0040:"WAVE_FORMAT_G721_ADPCM",0x0041:"WAVE_FORMAT_G728_CELP",0x0042:"WAVE_FORMAT_MSG723",0x0050:"WAVE_FORMAT_MPEG",0x0052:"WAVE_FORMAT_RT24",0x0053:"WAVE_FORMAT_PAC",0x0055:"WAVE_FORMAT_MPEGLAYER3",0x0059:"WAVE_FORMAT_LUCENT_G723",0x0060:"WAVE_FORMAT_CIRRUS",0x0061:"WAVE_FORMAT_ESPCM",0x0062:"WAVE_FORMAT_VOXWARE",0x0063:"WAVE_FORMAT_CANOPUS_ATRAC",0x0064:"WAVE_FORMAT_G726_ADPCM",0x0065:"WAVE_FORMAT_G722_ADPCM",0x0067:"WAVE_FORMAT_DSAT_DISPLAY",0x0069:"WAVE_FORMAT_VOXWARE_BYTE_ALIGNED",0x0070:"WAVE_FORMAT_VOXWARE_AC8",0x0071:"WAVE_FORMAT_VOXWARE_AC10",0x0072:"WAVE_FORMAT_VOXWARE_AC16",0x0073:"WAVE_FORMAT_VOXWARE_AC20",0x0074:"WAVE_FORMAT_VOXWARE_RT24",0x0075:"WAVE_FORMAT_VOXWARE_RT29",0x0076:"WAVE_FORMAT_VOXWARE_RT29HW",0x0077:"WAVE_FORMAT_VOXWARE_VR12",0x0078:"WAVE_FORMAT_VOXWARE_VR18",0x0079:"WAVE_FORMAT_VOXWARE_TQ40",0x0080:"WAVE_FORMAT_SOFTSOUND",0x0081:"WAVE_FORMAT_VOXWARE_TQ60",0x0082:"WAVE_FORMAT_MSRT24",0x0083:"WAVE_FORMAT_G729A",0x0084:"WAVE_FORMAT_MVI_MVI2",0x0085:"WAVE_FORMAT_DF_G726",0x0086:"WAVE_FORMAT_DF_GSM610",0x0088:"WAVE_FORMAT_ISIAUDIO",0x0089:"WAVE_FORMAT_ONLIVE",0x0091:"WAVE_FORMAT_SBC24",0x0092:"WAVE_FORMAT_DOLBY_AC3_SPDIF",0x0093:"WAVE_FORMAT_MEDIASONIC_G723",0x0094:"WAVE_FORMAT_PROSODY_8KBPS",0x0097:"WAVE_FORMAT_ZYXEL_ADPCM",0x0098:"WAVE_FORMAT_PHILIPS_LPCBB",0x0099:"WAVE_FORMAT_PACKED",0x00A0:"WAVE_FORMAT_MALDEN_PHONYTALK",0x00FF:"WAVE_FORMAT_RAW_AAC1",0x0100:"WAVE_FORMAT_RHETOREX_ADPCM",0x0101:"WAVE_FORMAT_IRAT",0x0111:"WAVE_FORMAT_VIVO_G723",0x0112:"WAVE_FORMAT_VIVO_SIREN",0x0123:"WAVE_FORMAT_DIGITAL_G723",0x0125:"WAVE_FORMAT_SANYO_LD_ADPCM",0x0130:"WAVE_FORMAT_SIPROLAB_ACEPLNET",0x0131:"WAVE_FORMAT_SIPROLAB_ACELP4800",0x0132:"WAVE_FORMAT_SIPROLAB_ACELP8V3",0x0133:"WAVE_FORMAT_SIPROLAB_G729",0x0134:"WAVE_FORMAT_SIPROLAB_G729A",0x0135:"WAVE_FORMAT_SIPROLAB_KELVIN",0x0140:"WAVE_FORMAT_G726ADPCM",0x0150:"WAVE_FORMAT_QUALCOMM_PUREVOICE",0x0151:"WAVE_FORMAT_QUALCOMM_HALFRATE",0x0155:"WAVE_FORMAT_TUBGSM",0x0160:"WAVE_FORMAT_MSAUDIO1",0x0161:"WAVE_FORMAT_WMAUDIO2",0x0162:"WAVE_FORMAT_WMAUDIO3",0x0163:"WAVE_FORMAT_WMAUDIO_LOSSLESS",0x0164:"WAVE_FORMAT_WMASPDIF",0x0170:"WAVE_FORMAT_UNISYS_NAP_ADPCM",0x0171:"WAVE_FORMAT_UNISYS_NAP_ULAW",0x0172:"WAVE_FORMAT_UNISYS_NAP_ALAW",0x0173:"WAVE_FORMAT_UNISYS_NAP_16K",0x0200:"WAVE_FORMAT_CREATIVE_ADPCM",0x0202:"WAVE_FORMAT_CREATIVE_FASTSPEECH8",0x0203:"WAVE_FORMAT_CREATIVE_FASTSPEECH10",0x0210:"WAVE_FORMAT_UHER_ADPCM",0x0220:"WAVE_FORMAT_QUARTERDECK",0x0230:"WAVE_FORMAT_ILINK_VC",0x0240:"WAVE_FORMAT_RAW_SPORT",0x0241:"WAVE_FORMAT_ESST_AC3",0x0249:"WAVE_FORMAT_GENERIC_PASSTHRU",0x0250:"WAVE_FORMAT_IPI_HSX",0x0251:"WAVE_FORMAT_IPI_RPELP",0x0260:"WAVE_FORMAT_CS2",0x0270:"WAVE_FORMAT_SONY_SCX",0x0300:"WAVE_FORMAT_FM_TOWNS_SND",0x0400:"WAVE_FORMAT_BTV_DIGITAL",0x0450:"WAVE_FORMAT_QDESIGN_MUSIC",0x0680:"WAVE_FORMAT_VME_VMPCM",0x0681:"WAVE_FORMAT_TPC",0x1000:"WAVE_FORMAT_OLIGSM",0x1001:"WAVE_FORMAT_OLIADPCM",0x1002:"WAVE_FORMAT_OLICELP",0x1003:"WAVE_FORMAT_OLISBC",0x1004:"WAVE_FORMAT_OLIOPR",0x1100:"WAVE_FORMAT_LH_CODEC",0x1400:"WAVE_FORMAT_NORRIS",0x1500:"WAVE_FORMAT_SOUNDSPACE_MUSICOMPRESS",0x1600:"WAVE_FORMAT_MPEG_ADTS_AAC",0x1601:"WAVE_FORMAT_MPEG_RAW_AAC",0x1602:"WAVE_FORMAT_MPEG_LOAS",0x1608:"WAVE_FORMAT_NOKIA_MPEG_ADTS_AAC",0x1609:"WAVE_FORMAT_NOKIA_MPEG_RAW_AAC",0x160A:"WAVE_FORMAT_VODAFONE_MPEG_ADTS_AAC",0x160B:"WAVE_FORMAT_VODAFONE_MPEG_RAW_AAC",0x1610:"WAVE_FORMAT_MPEG_HEAAC",0x2000:"WAVE_FORMAT_DVM",0x2001:"WAVE_FORMAT_DTS2",
    }
    
def dump_fmt(fmt):
    wFormatTag=get2u(fmt.data,0)
    
    sys.stdout.write("    wFormatTag=")

    if wave_format_tag_names.has_key(wFormatTag):
        sys.stdout.write("%s (%d, 0x%X)\n"%(wave_format_tag_names[wFormatTag],
                                            wFormatTag,
                                            wFormatTag))
    else:
        sys.stdout.write("%d, 0x%X\n"%(wFormatTag,
                                       wFormatTag))

    sys.stdout.write("    nChannels=%s\n"%(commas(get2u(fmt.data,2))))
    sys.stdout.write("    nSamplesPerSec=%s\n"%(commas(get4u(fmt.data,4))))
    sys.stdout.write("    nAvgBytesPerSec=%s\n"%(commas(get4u(fmt.data,8))))
    sys.stdout.write("    nBlockAlign=%s\n"%(commas(get2u(fmt.data,12))))
    sys.stdout.write("    wBitsPerSample=%s\n"%(commas(get2u(fmt.data,14))))

##########################################################################
##########################################################################

def dump_smpl(smpl):
    # http://www.sonicspot.com/guide/wavefiles.html#smpl

    manufacturer=get4u(smpl.data,0)
    product=get4u(smpl.data,4)
    sample_period=get4u(smpl.data,8)
    midi_unity_note=get4u(smpl.data,12)
    midi_pitch_fraction=get4u(smpl.data,16)
    smpte_format=get4u(smpl.data,20)
    smpte_offset=get4u(smpl.data,24)
    num_sample_loops=get4u(smpl.data,28)
    sampler_data=get4u(smpl.data,32)

    print "    manufacturer=%d"%manufacturer
    print "    product=%d"%product
    print "    sample_period=%d"%sample_period
    print "    midi_unity_note=%d"%midi_unity_note
    print "    midi_pitch_fraction=%d"%midi_pitch_fraction
    print "    smpte_format=%d"%smpte_format
    print "    smpte_offset=%d"%smpte_offset
    print "    num_sample_loops=%d"%num_sample_loops
    print "    sampler_data=%d"%sampler_data

    for loop in range(num_sample_loops):
        print "    loop %d/%d:"%(loop+1,num_sample_loops)

        cue_point_id=get4u(smpl.data,36+loop*24+0)
        type=get4u(smpl.data,36+loop*24+4)
        start=get4u(smpl.data,36+loop*24+8)
        end=get4u(smpl.data,36+loop*24+12)
        fraction=get4u(smpl.data,36+loop*24+16)
        play_count=get4u(smpl.data,36+loop*24+20)

        print "       cue_point_id=%d"%cue_point_id
        print "       type=%d"%type
        print "       start=%d"%start
        print "       end=%d"%end
        print "       fraction=%d"%fraction
        print "       play_count=%d"%play_count

##########################################################################
##########################################################################

def dump_list(chunk):
    if get4s(chunk.data,0)!="adtl":
        fatal("LIST chunk doesn't start with adtl.")

##########################################################################
##########################################################################

def print_table_filler(widths,prefix):
    print prefix+"+-"+"-+-".join(["-"*width for width in widths])+"-+"
        
def print_table_row(columns,widths,prefix):
    print prefix+"| "+" | ".join(["%-*s"%(widths[i],columns[i]) for i in range(len(widths))])+" |"
        
##########################################################################
##########################################################################
        
def print_table(headers,
                rows,
                prefix):
    widths=[len(x) for x in headers]
    
    for row in rows:
        for i in range(len(widths)):
            widths[i]=max(widths[i],
                          len("%s"%row[i]))

    print_table_filler(widths,prefix)
    print_table_row(headers,widths,prefix)
    print_table_filler(widths,prefix)
    
    for row in rows:
        print_table_row(row,widths,prefix)

    print_table_filler(widths,prefix)

##########################################################################
##########################################################################
        
def dump_cue(chunk):
    n=get4u(chunk.data,0)

    rows=[]

    for i in range(n):
        offset=4+i*24

        rows.append([get4u(chunk.data,offset+0),
                     commas(get4u(chunk.data,offset+4)),
                     get4s(chunk.data,offset+8),
                     get4u(chunk.data,offset+12),
                     get4u(chunk.data,offset+16),
                     commas(get4u(chunk.data,offset+20))])

    print_table(["ID","Pos","Chunk","ChunkStart","BlockStart","SmpOffset"],
                rows,
                "    ")

##########################################################################
##########################################################################

def dump(data):
    for i in range(0,
                   len(data),
                   16):
        sys.stdout.write("    %04X:"%i)

        for j in range(16):
            sys.stdout.write(" %s"%(("%02X"%ord(data[i+j])) if i+j<len(data) else "  "))

        sys.stdout.write(" ")
            
        for j in range(16):
            if i+j<len(data):
                c=ord(data[i+j])

                if c>=32 and c<127:
                    sys.stdout.write("%c"%c)
                else:
                    sys.stdout.write(".")
            else:
                sys.stdout.write(" ")

        sys.stdout.write("\n")
        
        
##########################################################################
##########################################################################
    
def main(args):
    global g_verbose
    g_verbose=args.verbose

    chunks=load_wav_chunks(args.wav_file)

    for chunk_idx in range(len(chunks)):
        chunk=chunks[chunk_idx]
        
        sys.stdout.write("Chunk %d/%d: '%s', %s bytes\n"%(chunk_idx+1,
                                                          len(chunks),
                                                          chunk.fourcc,
                                                          commas(len(chunk.data))))

        f=globals().get("dump_"+chunk.fourcc.rstrip())
        if f is not None:
            f(chunk)
        else:
            if len(chunk.data)<100:
                dump(chunk.data)

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="dump WAV file stuff")

    parser.add_argument("-v",
                        "--verbose",
                        action="store_true",
                        default=False,
                        help="If specified, verbosity.")

    parser.add_argument("wav_file",
                        metavar="WAV",
                        help="Path to WAV file to process.")

    result=parser.parse_args()
    main(result)
    
