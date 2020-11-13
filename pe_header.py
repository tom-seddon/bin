#!/usr/bin/python
import sys,os,os.path,argparse

# Upgrade to use https://github.com/erocarrera/pefile/ ?
#
# See also http://www.debuginfo.com/articles/debuginfomatch.html

##########################################################################
##########################################################################

def get2(xs,i): return xs[i+0]<<0|xs[i+1]<<8
def get4(xs,i): return xs[i+0]<<0|xs[i+1]<<8|xs[i+2]<<16|xs[i+3]<<24

def get_pe_timestamp(path):
    def fatal(msg):
        print>>sys.stderr,'FATAL: %s: %s'%(path,msg)
        sys.exit(1)

    def read(f,n):
        pos=f.tell()
        data=f.read(n)
        if len(data)!=n:
            fatal('failed to read %d byte(s) from +0x%x'%(n,pos))

        return [ord(x) for x in data]
    
    with open(path,'rb') as f: 
        dos_header=read(f,0x40)

        if get2(dos_header,0)!=0x5a4d: fatal('no MZ in DOS header')

        pe_header_offset=get4(dos_header,0x3c)

        f.seek(pe_header_offset)

        coff_header=read(f,0x18)

        if get4(coff_header,0)!=0x4550: fatal('no PE in COFF header')

        return get4(coff_header,8)

def pe_header(options):
    print 'TimeDateStamp=0x%08X: %s'%(get_pe_timestamp(options.exe_path),
                                      options.exe_path)
        

##########################################################################
##########################################################################

def main(argv):
    parser=argparse.ArgumentParser()

    parser.add_argument('exe_path',metavar='FILE',help='read from %(metavar)s')

    pe_header(parser.parse_args(argv))

if __name__=='__main__': main(sys.argv[1:])
