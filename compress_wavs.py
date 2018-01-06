#!/usr/bin/python
import os,os.path,sys,argparse,fnmatch,tempfile,shutil,multiprocessing

emacs=0

##########################################################################
##########################################################################

def fatal(str):
    sys.stderr.write("FATAL: %s"%str)
    if str[-1]!='\n': sys.stderr.write("\n")
    
    if emacs: raise RuntimeError
    else: sys.exit(1)

##########################################################################
##########################################################################

g_verbose=False

def v(str):
    global g_verbose
    
    if g_verbose:
        sys.stderr.write(str)
        sys.stderr.flush()

##########################################################################
##########################################################################

def get_fnames(root,patterns):
    result=[]
    for dname,dnames,fnames in os.walk(root):
        for fname in fnames:
            if fname.startswith("._"): continue
            for pattern in patterns:
                if fnmatch.fnmatch(fname,pattern):
                    result.append(os.path.relpath(os.path.join(dname,fname),root))
                    break
                
    return result

# def get_wav_fnames(dname): return get_fnames(dname,["*.wav"])

# def get_full_input_fname(options,
#                          input_fname):
#     return os.path.join(options.src_dname,
#                         input_fname)

# def get_full_output_fname(options,
#                           input_fname):
#     return os.path.join(options.dest_dname,
#                         os.path.splitext(input_fname)[0]+".mp3")

def do_escape(x,bad):
    r=""
    for c in x:
        if c in bad: r+="\\"
        r+=c
    return r

def escaped(x): return do_escape(x," %")
def shescape(x): return do_escape(x," %$()&'\"|\\*?<>{}")

##########################################################################
##########################################################################

class TempDir:
    def __init__(self,options=None):
        if options is None: self._keep=False
        else: self._keep=options.keep

    def __enter__(self):
        self._path=tempfile.mkdtemp()
        return self

    def __exit__(self,type,value,traceback):
        if not self._keep: shutil.rmtree(self._path)

    @property
    def path(self): return self._path

    def get_file_path(self,name): return os.path.join(self._path,name)

##########################################################################
##########################################################################

def sort_out_duplicates(input_fnames,options):
    names={}
    any=False

    for input_fname in input_fnames:
        name=os.path.splitext(os.path.basename(input_fname))[0]

        if name in names:
            print>>sys.stderr,"Duplicated name: %s"%names[name]
            print>>sys.stderr,"            and: %s"%input_fname
            any=True
        else:
            names[name]=input_fname

    if any: fatal("some names are duplicated")

    return names.values()

##########################################################################
##########################################################################

def main(options):
    global g_verbose
    g_verbose=options.verbose

    input_fnames=get_fnames(options.src_dname,["*.wav","*.flac"])
    # v("%d file(s)\n"%len(input_fnames))
    for x in input_fnames: v("    %s\n"%x)

    input_fnames=sort_out_duplicates(input_fnames,options)

    if options.dest_dname is None: fatal("no dest location supplied")

    with TempDir(options) as temp_dir:
        v("Temp dir: %s\n"%temp_dir.path)
        with open(temp_dir.get_file_path("Makefile"),"wt") as f:
            for i,input_fname in enumerate(input_fnames):
                f.write(".PHONY:T%d\n"%i)
                f.write("T%d:\n"%i)

                ext=os.path.splitext(os.path.normpath(input_fname))[1]
                flac=ext==".flac"
                
                if flac:
                    flac_name=os.path.join(options.src_dname,
                                           input_fname)
                    wav_name=temp_dir.get_file_path("%d.wav"%i)
                    # -s = silent
                    # -f = always overwrite
                    # -d = decode
                    # -o XXX = write to XXX
                    f.write("\tflac -s -f -d -o %s %s\n"%(shescape(wav_name),
                                                          shescape(flac_name)))
                else:
                    wav_name=os.path.join(options.src_dname,
                                          input_fname)

                mp3_name=os.path.join(options.dest_dname,
                                      os.path.dirname(input_fname),
                                      os.path.splitext(os.path.basename(input_fname))[0]+".mp3")
                f.write("\tmkdir -p %s\n"%shescape(os.path.dirname(mp3_name)))
                f.write("\tlame --preset insane -S %s %s\n"%(shescape(wav_name),
                                                             shescape(mp3_name)))
                if options.delete: f.write("\trm %s\n"%shescape(input_fname))

            f.write(".PHONY:all\n")
            f.write("all:")

            for i in range(len(input_fnames)): f.write(" T%d"%i)

            f.write("\n")

        make_command=options.make+" -j%d -f %s all"%(options.ncpu,
                                                     shescape(temp_dir.get_file_path("Makefile")))
        
        v("%s\n"%make_command)

        os.system(make_command)
                
##########################################################################
##########################################################################

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="bulk convert WAVs/FLACs to MP3")

    parser.add_argument("-m",
                        "--make",
                        metavar="MAKE",
                        default="make",
                        help="use %(metavar)s to invoke GNU Make (default: %(default)s)")
                        
    parser.add_argument("-v",
                        "--verbose",
                        action="store_true",
                        help="be more verbose")

    parser.add_argument("-j",
                        dest="ncpu",
                        default=multiprocessing.cpu_count(),
                        help="specify number of CPUs to use (default: %(default)s)")

    parser.add_argument("-o",
                        dest="dest_dname",
                        metavar="DIR",
                        help="location for compressed files")

    parser.add_argument("-k",
                        "--keep",
                        action="store_true",
                        help="keep temp files rather than deleting them afterwards")

    parser.add_argument("-d",
                        "--delete",
                        action="store_true",
                        help="delete input WAVs/FLACs after conversion")

    parser.add_argument("src_dname",
                        metavar="DIR",
                        help="location of WAV/FLAC files")

    main(parser.parse_args(sys.argv[1:]))
    
