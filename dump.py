#!/usr/bin/python
from __future__ import print_function
import argparse,sys,glob

##########################################################################
##########################################################################

def dump(f,options):
    offset=0

    cols=range(options.cols)

    while 1:
        row=bytearray(f.read(options.cols))

        if len(row)==0: break

        line='%08X:'%(offset+options.base)
        
        for col in cols:
            if col<len(row): line+=' %02x'%row[col]
            else: line+='   '

        line+=' '

        for col in cols:
            if col<len(row):
                if row[col]>=32 and row[col]<=126: line+=chr(row[col])
                else: line+='.'
            else:  line+=' '

        line+='\n'

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
    except IOError as e:
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
