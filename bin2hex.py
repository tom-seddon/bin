#!/usr/bin/python
import sys,os,os.path,argparse

##########################################################################
##########################################################################

def main(options):
    if options.output_fname=="-": o=sys.stdout
    else: o=open(options.output_fname,"wt")

    if options.input_fname=="-": i=sys.stdin
    else: i=open(options.input_fname,"rb")

    while True:
        line=i.read(options.num_columns)
        if line=="": break

        for x in line:
            o.write("0x%02X,"%ord(x))

        o.write("\n")

    # just let the files leak.

##########################################################################
##########################################################################

# http://stackoverflow.com/questions/25513043/python-argparse-fails-to-parse-hex-formatting-to-int-type
def auto_int(x): return int(x,0)

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="convert binary data into C source code")

    parser.add_argument("-c",
                        dest="num_columns",
                        type=auto_int,
                        default=16,
                        help="specify number of bytes per line")

    parser.add_argument("-o",
                        dest="output_fname",
                        metavar="FILE",
                        default="-",
                        help="file to save to, or \"-\" for stdout")

    parser.add_argument("input_fname",
                        metavar="FILE",
                        help="file to read from, or \"-\" for stdin")

    main(parser.parse_args(sys.argv[1:]))
    
