#!/usr/bin/python3
import sys,os,os.path,argparse,subprocess,shutil,collections,re

##########################################################################
##########################################################################

g_verbose=False

def pv(msg):
    if g_verbose: sys.stderr.write(msg)

##########################################################################
##########################################################################

def fatal(msg):
    sys.stderr.write('FATAL: %s\n'%msg)
    sys.exit(1)

##########################################################################
##########################################################################

RunResult=collections.namedtuple('RunResult','returncode stdout stderr')

##########################################################################
##########################################################################

def get_windows_command(argv):
    s=''
    for arg in argv:
        if len(s)>0: s+=' '
        arg=arg.replace('%','%%')
        if ' ' in arg: s+='"%s"'%arg
        else: s+=arg
    return s

##########################################################################
##########################################################################

# '%' is a bit annoying to enter at the Windows command prompt, so
# accept $ as well.
def get_ffmpeg_pattern(pattern): return pattern.replace('$','%')

##########################################################################
##########################################################################

def find_files_matching_ffmpeg_pattern(pattern,description):
    num_arguments=None
    try:
        pattern%0           # error if 0 or 2+ arguments
        num_arguments=1     # must be 1 argument
    except TypeError:
        try:                # error if 2+ arguments
            pattern%()
            num_arguments=0 # must be 0 arguments
        except TypeError: num_arguments=2 # must be 2+

    if num_arguments>=2: fatal('%s must have max 1 argument'%description)

    if num_arguments==0: paths=[pattern]
    else:
        paths=[]
        i=0
        while True:
            path=pattern%i
            if not os.path.isfile(path): break
            paths.append(path)
            i+=1

    return paths

##########################################################################
##########################################################################

def main2(options):
    global g_verbose;g_verbose=options.verbose

    pad_colour='red' if options.debug else 'black'

    if options.video_input_pattern!='-' and options.framerate is None:
        fatal('must specify frame rate when video files supplied')

    audio_list_path=None
    if options.audio_input_pattern!='-':
        # has to be handled specially, as ffmpeg doesn't support
        # automatically concatenating input audio files.
        #
        # wav files suffer from a 4 GByte limit, so use flac as the
        # temp output file.

        audio_paths=find_files_matching_ffmpeg_pattern(get_ffmpeg_pattern(options.audio_input_pattern),
                                                       'audio pattern')

        audio_list_path=options.output_path+'.audio_list.txt'
        with open(audio_list_path,'wt') as f:
            for audio_path in audio_paths:
                audio_path=os.path.abspath(audio_path)
                f.write("file '%s'\n"%(audio_path.replace('\\','/')))

    if options.video_input_pattern!='-':
        # at least do a quick sanity check.
        video_paths=find_files_matching_ffmpeg_pattern(get_ffmpeg_pattern(options.video_input_pattern),
                                                       'video pattern')
        if len(video_paths)==0: fatal('no video files matching pattern: %s'%options.video_input_pattern)

    vf_crop=None
    if options.crop and len(options.video_input_pattern)>0:
        argv=[]
        argv+=[options.ffmpeg_path]
        argv+=['-i',get_ffmpeg_pattern(options.video_input_pattern)]
        argv+=['-progress','pipe:1']
        argv+=['-vf','cropdetect=mode=black:limit=0']
        argv+=['-f','null','-']
        proc=subprocess.Popen(argv,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        stdout_bytes=bytearray()
        stderr_bytes=bytearray()
        while proc.poll() is None:
            try:
                stdout,stderr=proc.communicate(timeout=0.5)
                stdout_bytes+=stdout
                stderr_bytes+=stderr
                sys.stdout.buffer.write(stdout_bytes)
            except subprocess.TimeoutExpired:
                # not actually a problem. it just printed nothing for
                # 0.5 seconds. carry on.
                pass
        stderr_lines=stderr_bytes.decode('utf8').splitlines()

        # no need to decode it... the crop= output is suitable as the
        # spec for the filter.
        crop_re=re.compile('(crop=[0-9]+:[0-9]+:[0-9]+)')
        for stderr_line in reversed(stderr_lines):
            m=crop_re.search(stderr_line)
            if m is not None:
                vf_crop=m.group(1)
                break

        if vf_crop is None: fatal('failed to get crop details')
    
    vfs=[]

    if vf_crop is not None: vfs.append(vf_crop)

    if options.b2: vfs.append('scale=iw*0.96:ih')

    def add_scale_vfs(w,h):
        vfs.append('scale=%d:%d:force_original_aspect_ratio=1'%(w,h))
        vfs.append('pad=width=%d:height=%d:x=(out_w-in_w)/2:y=(out_h-in_h)/2:color=%s'%(w,h,pad_colour))

    if options.res_720p: add_scale_vfs(1280,720)
    elif options.res_1080p: add_scale_vfs(1920,1080)

    video_input_index=None
    audio_input_index=None
    next_input_index=0

    def get_next_input_index():
        nonlocal next_input_index
        next_input_index+=1
        return next_input_index-1
    
    argv=[]
    argv+=[options.ffmpeg_path]
    argv+=['-y']           # overwrite output file
    if options.video_input_pattern!='-':
        if options.framerate is not None:
            argv+=['-framerate',str(options.framerate)]

        argv+=['-i',get_ffmpeg_pattern(options.video_input_pattern)]

        video_input_index=get_next_input_index()

    if audio_list_path is not None:
        argv+=['-f','concat']   # concatenate audio inputs
        argv+=['-safe','0']     # allow any path in list file
        argv+=['-i',audio_list_path]

        audio_input_index=get_next_input_index()

    if video_input_index is not None:
        argv+=['-map','%d:v:0'%video_input_index]

    if audio_input_index is not None:
        argv+=['-map','%d:a:0'%audio_input_index]

    if len(vfs)>0: argv+=['-vf',','.join(vfs)]

    if options.flac: argv+=['-acodec','flac']

    argv+=[options.output_path]
    pv('ffmpeg command: %s\n'%get_windows_command(argv))

    result=subprocess.run(argv)

    if not options.keep:
        os.unlink(audio_list_path)
    
    if result.returncode!=0: fatal('ffmpeg failed')

##########################################################################
##########################################################################

def main(argv):
    parser=argparse.ArgumentParser()

    # Attempt to find ffmpeg...
    ffmpeg_path=shutil.which('ffmpeg')

    def auto_int(x): return int(x,0)

    parser.add_argument('-v','--verbose',action='store_true',help='be more verbose')
    parser.add_argument('--debug',action='store_true',help='''some debug stuff''')
    parser.add_argument('-f','--framerate',metavar='HZ',default=None,type=auto_int,help='''treat video as %(metavar)s frame/second''')
    parser.add_argument('video_input_pattern',metavar='VIDEO-PATTERN',help='''read video file(s) from %(metavar)s, or - if none''')
    parser.add_argument('audio_input_pattern',metavar='AUDIO-PATTERN',help='''read audio file(s) from %(metavar)s, or - if none''')
    parser.add_argument('output_path',metavar='OUTPUT-PATH',help='''write output to %(metavar)s''')
    parser.add_argument('--flac',action='store_true',help='''write FLAC audio''')
    parser.add_argument('--crop',action='store_true',help='''crop to visible area''')
    parser.add_argument('--b2',action='store_true',help='''output is 1:1 BBC Micro video from b2, so correct its aspect ratio''')
    parser.add_argument('--720p',dest='res_720p',action='store_true',help='''produce 720p output''')
    parser.add_argument('--1080p',dest='res_1080p',action='store_true',help='''produce 1080p output''')
    parser.add_argument('--ffmpeg',dest='ffmpeg_path',metavar='PATH',default=ffmpeg_path,required=ffmpeg_path is None,help='''treat %(metavar)s as path to ffmpeg.'''+('''Default: %s'''%ffmpeg_path if ffmpeg_path is not None else ''))
    parser.add_argument('--keep',action='store_true',help='''keep temp files rather than deleting them''')

    main2(parser.parse_args(argv))

if __name__=='__main__': main(sys.argv[1:])
