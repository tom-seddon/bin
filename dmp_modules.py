#!/usr/bin/python
import sys,os,os.path,argparse,subprocess

##########################################################################
##########################################################################

def run(args,stdin_data):
    #print args
    process=subprocess.Popen(args=args)
                             # stdin=None,#subprocess.PIPE,
                             # stdout=subprocess.PIPE,
                             # stderr=subprocess.PIPE)
    #print args
    output=process.communicate(stdin_data)
    if output[0] is None: return output
    else: return output[0].splitlines()


def dmp_modules(options):
    command='lmoftD'
    if options.module is not None: command+=' m %s'%options.module
    command+=';q'
    
    output=run([options.cdb_path,
                '-c',command,
                '-z',options.dmp_path],
               None)
    if output is not None: print output
    

##########################################################################
##########################################################################

def main(argv):
    parser=argparse.ArgumentParser()

    parser.add_argument('--cdb-path',metavar='PATH',default=r'''C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe''',help='use %(metavar)s as cdb.exe. Default: %(default)s')

    parser.add_argument('-m','--module',metavar='WILDCARD',help='specify modules to list, using WinDbg string wildcard syntax (list all if not specified)')

    parser.add_argument('dmp_path',metavar='FILE',help='read dump file from %(metavar)s')

    dmp_modules(parser.parse_args(argv))

if __name__=='__main__': main(sys.argv[1:])
