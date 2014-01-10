import sys,argparse,os,subprocess

##########################################################################
##########################################################################

def flushall():
    sys.stdout.flush()
    sys.stderr.flush()

def pe(str):
    sys.stderr.write(str)

##########################################################################
##########################################################################

def main(options,
         cmd_argv):
    if len(cmd_argv)==0:
        pe("FATAL: No command specified.\n")
        sys.exit(1)

    if len(options.inputs)==0:
        lines=[x.strip() for x in sys.stdin.readlines()]
    else:
        lines=[]

        for i in options.inputs:
            with open(i,
                      "rt") as f:
                lines+=[x.strip() for x in f.readlines()]

    # re-quote everything
    n=len(lines)
    for i in range(n):
        line=lines[i]
        argv=[]
        replaced=False
        for arg in cmd_argv:
            new_arg=arg.replace(options.replstr,
                                line)
            if arg!=new_arg:
                replaced=True
                
            argv.append(new_arg)

        if not replaced:
            argv.append(line)

        progress_line=""

        if options.progress:
            progress_line+="%d/%d"%(1+i,n)

        if options.progress and options.verbose:
            progress_line+=": "

        if options.verbose:
            progress_line+=" ".join(argv)

        if options.progress and not options.verbose:
            pe(progress_line)
            pe("\r")
        elif options.progress or options.verbose:
            pe(progress_line)
            pe("\n")

        r=subprocess.call(argv,
                          shell=options.shell)
        #r=os.system(cmd)
        if r!=0:
            pe("FATAL: Command returned %d: %s\n"%(r,
                                                   " ".join(argv)))
            sys.exit(1)

        if options.progress and not options.verbose:
            pe(" "*len(progress_line)+"\r")

##########################################################################
##########################################################################

# class ForeachArgumentParser(argparse.ArgumentParser):
#     def __init__(self,
#                  *args,
#                  **kwargs):
#         super(ForeachArgumentParser,
#               self).__init__(*args,
#                               **kwargs)

#     def format_usage(self):
#         return super(ForeachArgumentParser,
#                      self).format_usage().rstrip()+" - CMD\n"
            
if __name__=="__main__":
    parser=argparse.ArgumentParser(fromfile_prefix_chars="@",
                                   description="Follow options with single '-', then command to run.")

    parser.add_argument("-i",
                        dest="inputs",
                        metavar="FILE",
                        default=[],
                        action="append",
                        help=
                        """Read items from %(metavar)s. (If specified, stdin is ignored.)""")

    parser.add_argument("-s",
                        dest="shell",
                        default=False,
                        action="store_true",
                        help=
                        """If specified, invoke command via shell.""")

    parser.add_argument("-I",
                        metavar="STR",
                        dest="replstr",
                        default="{}",
                        help=
                        """Replace %(metavar)s (default %(default)s) with line from file. (If %(metavar)s not present on command line, add line to end of command line.)""")

    parser.add_argument("-v",
                        dest="verbose",
                        default=False,
                        action="store_true",
                        help=
                        """If specified, print each command line to stderr before executing.""")

    parser.add_argument("-p",
                        dest="progress",
                        default=False,
                        action="store_true",
                        help=
                        """If specified, print progress to stderr.""")

    # Work up to the '-'
    argv=sys.argv[1:]
    
    if not "-" in argv:
        sep_index=len(argv)
    else:
        sep_index=argv.index("-")

    main(parser.parse_args(argv[:sep_index]),
         argv[sep_index+1:])
