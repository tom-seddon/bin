#!/usr/bin/python
import optparse,sys,glob

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

    out=sys.stdout

    for file_name in file_names:
        if len(file_names)>1:
            out.write("\n** %s:\n\n"%file_name)
        
        f=open(file_name,
               "rb")

        offset=0

        while 1:
            row=f.read(options.cols)

            if row=="":
                break

            out.write("%08X: "%offset)

            for i in range(options.cols):
                if i<len(row):
                    out.write(" %02X"%ord(row[i]))
                else:
                    out.write("   ")

            out.write("  ")

            for i in range(options.cols):
                if i<len(row):
                    if ord(row[i])>=32 and ord(row[i])<=126:
                        out.write(row[i])
                    else:
                        out.write(".")
                else:
                    out.write(" ")

            out.write("\n")

            offset+=options.cols

        f.close()
        

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
