#!/usr/bin/python3
import sys,os,os.path,argparse

##########################################################################
##########################################################################

def main2(options):
    good=True
    
    for input_path in options.input_paths:
        with open(input_path,'rb') as f: data=f.read()

        num_crlf=0
        num_lfcr=0
        num_lf=0
        num_cr=0

        line=1
        line_start=0

        def eol(print_flag,name):
            nonlocal i,line_start,line

            i+=1
            if print_flag:
                print('%s: line %d: start=+%d (+0x%x)'%(name,line,line_start,line_start))
            line_start=i
            line+=1

        i=0
        while i<len(data):
            if data[i]==13:
                if i+1<len(data) and data[i+1]==10:
                    num_crlf+=1
                    i+=1
                    eol(options.crlf,'CR+LF')
                else:
                    num_cr+=1
                    eol(options.cr,'CR')
            elif data[i]==10:
                if i+1<len(data) and data[i+1]==13:
                    num_lfcr+=1
                    i+=1
                    eol(options.lfcr,'LF+CR')
                else:
                    num_lf+=1
                    eol(options.lf,'LF')
            else: i+=1

        output='%s: '%input_path
        num_kinds=0
        
        def add(prefix,n):
            if n>0:
                nonlocal output
                nonlocal num_kinds

                if num_kinds>0: output+='; '
                output+='%s: %d'%(prefix,n)
                num_kinds+=1
        
        add('LF',num_lf)
        add('CR',num_cr)
        add('CR+LF',num_crlf)
        add('LF+CR',num_lfcr)

        if num_kinds==0: output+='(no line endings)'
        elif num_kinds>1: good=False

        if options.only_inconsistent:
            if num_kinds>1: print(output)
        else: print(output)

        #print('%s: LF: %d; CR: %d; CR+LF: %d; LF+CR: %d'%(input_path,num_lf,num_cr,num_crlf,num_lfcr))

    if not good: sys.exit(1)
    
            
##########################################################################
##########################################################################

def main(argv):
    parser=argparse.ArgumentParser()

    parser.add_argument('input_paths',nargs='+',metavar='FILE',help='''read data from %(metavar)s''')
    parser.add_argument('--cr',action='store_true',help='''print lines ending in CR''')
    parser.add_argument('--lf',action='store_true',help='''print lines ending in LF''')
    parser.add_argument('--crlf',action='store_true',help='''print lines ending in CR+LF''')
    parser.add_argument('--lfcr',action='store_true',help='''print lines ending in LF+CR''')
    parser.add_argument('-i','--only-inconsistent',action='store_true',help='''only print info for files with inconsistent line endings''')

    main2(parser.parse_args(argv[1:]))

##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv)
