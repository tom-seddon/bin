#!/usr/bin/python3
import sys,os,argparse,subprocess

##########################################################################
##########################################################################

def main2(options):
    num_runs=0
    while True:
        result=subprocess.run(options.subprocess_argv)
        num_runs+=1
        if result.returncode!=0:
            sys.stderr.write('FATAL: exited after %d runs with exit code: %d\n'%(num_runs,result.returncode))

            # TODO: use the subprocess's exit code?
            sys.exit(1)

##########################################################################
##########################################################################

def main(argv):
    parser=argparse.ArgumentParser()

    parser.add_argument('subprocess_argv',nargs='+',metavar='ARGS',help='''argument(s) for program to run''')

    main2(parser.parse_args(argv))

##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv[1:])
