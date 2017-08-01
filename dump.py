#!/usr/bin/python
import argparse,sys,glob

##########################################################################
##########################################################################

def dump(f,options):
    offset=0

    cols=range(options.cols)

    while 1:
        row=f.read(options.cols)

        if row=="":
            break

        line="%08X: %s  %s\n"%(offset+options.base,
                               " ".join(["%02X"%ord(row[i]) if i<len(row) else "  " for i in cols]),
                               "".join([(row[i] if ord(row[i])>=32 and ord(row[i])<=126 else ".") if i<len(row) else " " for i in cols]))
        
        sys.stdout.write(line)

        offset+=options.cols

##########################################################################
##########################################################################

def main(options):
    # file_names=[]
    # for arg in args:
    #     file_names+=glob.glob(arg)

    # if len(file_names)==0:
    #     sys.stderr.write("FATAL: given name(s) don't appear to match any file(s).")
    #     sys.exit(1)

    try:
        for file_name in options.file_names:
            if len(options.file_names)>1:
                sys.stdout.write("\n** %s:\n\n"%file_name)

            if file_name=="-": dump(sys.stdin,options)
            else:
                with open(file_name,"rb") as f: dump(f,options)
    except IOError,e:
        if e.errno==32 or e.errno==22:
            # Broken pipe. Just ignore this.
            #
            # Close stdout and stderr so that the Python C code
            # doesn't pop up a message when it tries to close them
            # itself later. See, e.g., http://stackoverflow.com/questions/12790328/
            #
            # This prevents problems with stuff like "dump XXX | head -n 5"
            try:
                sys.stdout.close()
            except:
                pass

            try:
                sys.stderr.close()
            except:
                pass
        else:
            raise

##########################################################################
##########################################################################

# http://stackoverflow.com/questions/25513043/python-argparse-fails-to-parse-hex-formatting-to-int-type
def auto_int(x): return int(x,0)

if __name__=="__main__":
    parser=argparse.ArgumentParser()

    parser.add_argument("-c","--cols",dest="cols",metavar="COLS",default=16,type=auto_int,help="set number of columns to COLS")
    parser.add_argument("-b","--base",default=0,type=auto_int,help="base address for offsets")
    parser.add_argument("file_names",metavar="FILE",help="file to dump",action="append")

    main(parser.parse_args(sys.argv[1:]))
