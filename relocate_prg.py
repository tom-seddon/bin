#!env python
import sys,os,os.path,argparse,struct
emacs=os.getenv("EMACS") is not None

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
        sys.stdout.write(str)
        sys.stdout.flush()

##########################################################################
##########################################################################

def getl(xs,i): return (xs[i+0]<<24)|(xs[i+1]<<16)|(xs[i+2]<<8)|(xs[i+3]<<0)

def setl(xs,i,x):
    xs[i+0]=(x>>24)&255
    xs[i+1]=(x>>16)&255
    xs[i+2]=(x>>8)&255
    xs[i+3]=(x>>0)&255

def main(options):
    global g_verbose
    g_verbose=options.verbose

    global emacs
    if options.not_emacs: emacs=False

    with open(options.input_fname,"rb") as f: data=[ord(x) for x in f.read()]
    v("%s: %d bytes\n"%(options.input_fname,len(data)))

    if data[0]!=0x60 or data[1]!=0x1A: fatal("file doesn't start with GEMDOS magic number")

    text_size=getl(data,2)
    data_size=getl(data,6)
    bss_size=getl(data,10)
    syms_size=getl(data,14)

    v("    Text size: %d\n"%text_size)
    v("    Data size: %d\n"%data_size)
    v("    BSS size: %d\n"%bss_size)
    v("    Symbols size: %d\n"%syms_size)

    header_offset=0
    text_offset=0x1c
    data_offset=text_offset+text_size
    syms_offset=data_offset+data_size
    rel_offset=syms_offset+syms_size

    v("    (Relocation size: %d)\n"%(len(data)-rel_offset))

    # Do the TEXT and DATA relocations.
    offset=getl(data,rel_offset)
    if offset==0: print>>sys.stderr,"NOTE: No fixups in file."
    else:
        num_relocated=0
        i=rel_offset+4
        value=None
        while value!=0:
            value=data[i]
            if value==1: offset+=254
            elif value%2==1: fatal("found odd value in relocation data")
            else:
                x=getl(data,text_offset+offset)
                x+=options.address
                setl(data,text_offset+offset,x)

                offset+=value
                num_relocated+=1

            i+=1

        v("    Relocated %d longs.\n"%num_relocated)

    # Strip off symbols and relocation table.
    data=data[:syms_offset]

    # Add in a BSS.
    data+=[0]*bss_size

    with open(options.output_fname,"wb") as f: f.write("".join([chr(x) for x in data]))
    v("%s: %d bytes at 0x%08X\n"%(options.output_fname,len(data),options.address))
    
##########################################################################
##########################################################################

# http://stackoverflow.com/questions/25513043/python-argparse-fails-to-parse-hex-formatting-to-int-type
def auto_int(x): return int(x,0)

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="turn Atari GEMDOS executable file into a memory image")

    parser.add_argument("--not-emacs",
                        action="store_true",
                        help="assume not running under emacs")

    parser.add_argument("-v",
                        "--verbose",
                        action="store_true",
                        help="be more verbose")

    parser.add_argument("-a",
                        "--address",
                        nargs=1,
                        type=auto_int,
                        default=0x20000,
                        help="address to relocate to (default: %(default)X)")

    parser.add_argument("-o",
                        "--output-file",
                        dest="output_fname",
                        help="memory image file to save to (N.B.: no longer a valid GEMDOS executable)")

    parser.add_argument("input_fname",
                        metavar="FILE",
                        help="name of TOS/PRG file to relocate")
    
    args=sys.argv[1:]

    options=parser.parse_args(args)

    main(options)

    
