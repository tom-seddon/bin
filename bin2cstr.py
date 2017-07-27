#!/usr/bin/python
import sys,textwrap,optparse,os,os.path

##########################################################################
##########################################################################

# def get_c_friendly_name(file_name):
#     name=""
#     for c in os.path.basename(file_name):
#         if c.isalnum():
#             name+=c
#         else:
#             name+="_"
#     return name

##########################################################################
##########################################################################

escapes={
    "\t":"\\t",
    "\n":"\\n",
    "\r":"\\r",
    "\\":"\\\\",
    "\"":"\\\"",
    }

max_num_line_chars=500

def do_file(f,out):
    num_line_chars=None
    last_c=None
    cont=0

    if options.comma:
        line_end="\",\n"
    else:
        line_end="\"\n"

    data=f.read()

    if options.elisp:
        i=0
        n=16
        while i<len(data):
            out.write('"')
            for j in range(n):
                if i+j>=len(data): break
                out.write("\\x%02X"%ord(data[i+j]))
            i+=n
            out.write('"\n')
    else:
        for c in data:
            if num_line_chars>=max_num_line_chars:
                out.write("\"//...\n")
                cont=1
                num_line_chars=None
            elif (c!="\n" and c!="\r") and (last_c=="\n" or last_c=="\r"):
                out.write(line_end)
                num_line_chars=None

            if num_line_chars is None:
                if cont:
                    out.write("    ")
                    cont=0

                out.write("\"")
                num_line_chars=0

            if escapes.has_key(c):
                do_print=1
                if options.no_newlines:
                    if c=="\n" or c=="\r":
                        do_print=0

                if do_print:
                    out.write(escapes[c])
                    num_line_chars+=1

            elif ord(c)>=32 and ord(c)<=127:
                out.write(c)
                num_line_chars+=1
            else:
                out.write("\\x%02X"%ord(c))
                num_line_chars+=1

            last_c=c

            if (c=="\n" or c=="\r") and (last_c=="\n" or last_c=="\r") and last_c!=c:
                out.write(line_end)
                num_line_chars=None

        if num_line_chars is not None:
            out.write(line_end)
            
def main(args,
         options,
         out):
    if len(args)==0: do_file(sys.stdin,out)
    else:
        for arg in args:
            with open(arg,"rb") as f: do_file(f,out)

##########################################################################
##########################################################################

if __name__=="__main__":
    parser=optparse.OptionParser()

    parser.add_option("-,",
                      action="store_true",
                      dest="comma",
                      help="put a comma after each line")

    parser.add_option("-n",
                      "--no-newlines",
                      action="store_true",
                      help="don't include newline chars in output. (Strings will still be broken at input newlines)")

    parser.add_option("-e",
                      "--elisp",
                      action="store_true",
                      help="produce elisp-friendly output")

    parser.set_defaults(comma=0,
                        no_newlines=0)
    
    options,args=parser.parse_args()
    main(args,
         options,
         sys.stdout)
