#!/usr/bin/python3
import sys,os,argparse,collections,shlex,subprocess

##########################################################################
##########################################################################

def fatal(msg):
    sys.stderr.write('FATAL: %s\n'%msg)
    sys.exit(1)

##########################################################################
##########################################################################

def main2(options):
    if not os.path.isfile(options.d_path):
        fatal('dtrace script not found: %s'%options.d_path)

    opt_has_target=False
    if options.pid==0 and options.pname is None and options.wname is None:
        # not supporting invocation
        fatal('must specify a target')

    if options.wname is not None: opt_has_target=True

    opt_printid=options.printid
    if options.follow or options.pname is not None:
        if opt_printid!=-1: opt_printid=1
        else: opt_printid=0

    cpp_defs={
        'OPT_HAS_TARGET=%d'%opt_has_target,
        'OPT_FOLLOW=%d'%options.follow,
        'OPT_PRINTID=%d'%opt_printid,
        'OPT_RELATIVE=%d'%options.relative,
        'OPT_ELAPSED=%d'%options.elapsed,
        'OPT_CPU=%d'%options.cpu,
        'OPT_COUNTS=%d'%options.counts,
        'OPT_PID=%d'%(options.pid!=0),
        'OPT_NAME=%d'%(options.pname is not None),
        'OPT_TRACE=%d'%(options.trace is not None),
        'OPT_STACK=%d'%options.stack,
        'OPT_PID_VALUE=%d'%options.pid,
        'OPT_NAME_VALUE="%s"'%(options.pname or ""),
        'OPT_TRACE_VALUE="%s"'%(options.trace or ""),
    }

    dtrace_argv=['sudo','/usr/sbin/dtrace']
    dtrace_argv+=['-C']
    for cpp_def in cpp_defs: dtrace_argv.append('-D%s'%cpp_def)
    dtrace_argv+=['-s',options.d_path]
    if options.wname is not None: dtrace_argv+=['-W',options.wname]
    dtrace_argv+=['-x','dynvarsize=%s'%options.buf]

    result=subprocess.run(dtrace_argv)
    sys.exit(result.returncode)

##########################################################################
##########################################################################

def auto_int(x): return int(x,0)
    
def main(argv):
    parser=argparse.ArgumentParser()

    parser.add_argument('-p',metavar='PID',dest='pid',default=0,type=auto_int,help='''examine process with PID %(metavar)s''')
    parser.add_argument('-n',metavar='NAME',dest='pname',help='''examine process with name %(metavar)s''')
    parser.add_argument('-t',metavar='CALL',dest='trace',help='''examine syscall %(metavar)s only''')
    parser.add_argument('-W',metavar='NAME',dest='wname',help='''wait for process with name %(metavar)s''')
    parser.add_argument('-a',dest='all',action='store_true',help='''print all details''')
    parser.add_argument('-c',dest='counts',action='store_true',help='''print syscall counts''')
    parser.add_argument('-d',dest='relative',action='store_true',help='''print relative times (us)''')
    parser.add_argument('-e',dest='elapsed',action='store_true',help='''print elapsed times (us)''')
    parser.add_argument('-f',dest='follow',action='store_true',help='''follow children''')
    parser.add_argument('-l',dest='printid',action='store_const',const=1,help='''force printing pid/lwpid''')
    parser.add_argument('-o',dest='cpu',action='store_true',help='''print on cpu times''')
    parser.add_argument('-s',dest='stack',action='store_true',help='''print stack backtraces''')
    parser.add_argument('-L',dest='printid',action='store_const',const=1,help='''don't print pid/lwpid''')
    parser.add_argument('-b',dest='buf',metavar='BUFSIZE',default='4m',help='''set dynamic variable buf size to %(metavar)s. Default: %(default)s''')
    parser.add_argument('--d-path',metavar='PATH',default=os.path.join(os.path.dirname(os.path.realpath(__file__)),'dtruss.tom.d'),help='''read dtrace script from %(metavar)s. Default: %(default)s''')
    parser.set_defaults(printid=0)

    main2(parser.parse_args(argv))

##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv[1:])
