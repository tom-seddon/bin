#!/usr/bin/python
import optparse,sys,glob

def dump(f):
    offset=0

    cols=range(options.cols)

    while 1:
        row=f.read(options.cols)

        if row=="":
            break

        line="%08X: %s  %s\n"%(offset,
                               " ".join(["%02X"%ord(row[i]) if i<len(row) else "  " for i in cols]),
                               "".join([(row[i] if ord(row[i])>=32 and ord(row[i])<=126 else ".") if i<len(row) else " " for i in cols]))

        # line="%08X: "%offset

        # for i in range(options.cols):
        #     if i<len(row):
        #         line+=" %02X"%ord(row[i])
        #     else:
        #         line+="   "

        # line+="  "

        # for i in range(options.cols):
        #     if i<len(row):
        #         if ord(row[i])>=32 and ord(row[i])<=126:
        #             line+=row[i]
        #         else:
        #             line+="."
        #     else:
        #         line+=" "

        # line+="\n"

        sys.stdout.write(line)

        offset+=options.cols

def main(options,
         args):
    if len(args)<1:
        sys.stderr.write("FATAL: must supply name(s) of file to dump.")
        sys.exit(1)

    file_names=[]
    for arg in args:
        file_names+=glob.glob(arg)

    if len(file_names)==0:
        sys.stderr.write("FATAL: given name(s) don't appear to match any file(s).")
        sys.exit(1)

    try:
        for file_name in file_names:
            if len(file_names)>1:
                sys.stdout.write("\n** %s:\n\n"%file_name)

            if file_name=="-":
                dump(sys.stdin)
            else:
                with open(file_name,"rb") as f:
                    dump(f)
    except IOError,e:
        if e.errno==32:
            # Broken pipe. Just ignore this.
            pass
        else:
            raise

if __name__=="__main__":
    parser=optparse.OptionParser(usage="%prog [options] FILE(s)")

    parser.add_option("-c",
                      "--cols",
                      dest="cols",
                      metavar="COLS",
                      default=16,
                      type="int",
                      help="set number of columns to COLS (default %default)")

    options,args=parser.parse_args()

    main(options,
         args)
