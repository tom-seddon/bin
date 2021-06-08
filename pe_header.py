#!/usr/bin/python
import sys,os,os.path,argparse,struct

# Upgrade to use https://github.com/erocarrera/pefile/ ?
#
# See also http://www.debuginfo.com/articles/debuginfomatch.html
#
# https://www.fireeye.com/blog/threat-research/2019/08/definitive-dossier-of-devilish-debug-details-part-one-pdb-paths-malware.html

##########################################################################
##########################################################################

# def get2(xs,i): return xs[i+0]<<0|xs[i+1]<<8
# def get4(xs,i): return xs[i+0]<<0|xs[i+1]<<8|xs[i+2]<<16|xs[i+3]<<24

def get_pe_timestamp(path):
    def fatal(msg):
        print>>sys.stderr,'FATAL: %s: %s'%(path,msg)
        sys.exit(1)

    with open(path,'rb') as f: 
        dos_header=f.read(0x40)
        if len(dos_header)!=0x40: fatal('failed to read DOS header')
        if dos_header[0:2]!='MZ': fatal('no MZ in DOS header')

        coff_header_offset=struct.unpack_from('<I',dos_header,0x3c)[0]

        f.seek(coff_header_offset)
        coff_header=f.read(0x18)
        if len(coff_header)!=0x18: fatal('failed to read COFF header')
        if coff_header[0:2]!='PE': fatal('no PE in COFF header')

        return struct.unpack_from('<I',coff_header,8)[0]

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
