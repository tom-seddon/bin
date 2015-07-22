##########################################################################
##########################################################################

# this (otherwise unnecessary) import fixes problems locating
# pywintypes with anaconda. see
# https://github.com/ContinuumIO/anaconda-issues/issues/37#issuecomment-109201314
import win32com.client

##########################################################################
##########################################################################

import sys,argparse,os,subprocess,pywintypes

got_win32console=True
try:
    import win32console
except:
    got_win32console=False

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

    if options.dry_run:
        options.progress=True
        options.verbose=True

    if options.keep_going_quietly:
        options.keep_going=True

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

        if got_win32console:
            win32console.SetConsoleTitle("%d/%d: %s"%(1+i,n," ".join(argv)))

        if options.progress and not options.verbose:
            pe(progress_line)
            pe("\r")
        elif options.progress or options.verbose:
            con_stdout=None
            
            if got_win32console:
                con_stdout=win32console.GetStdHandle(win32console.STD_OUTPUT_HANDLE)
                try:
                    con_info=con_stdout.GetConsoleScreenBufferInfo()
                    con_attr=con_info["Attributes"]
                    con_stdout.SetConsoleTextAttribute(((con_attr>>4)&0x0F)|((con_attr<<4)&0xF0))
                except pywintypes.error:
                    # probably redirected.
                    con_stdout=None
                
            pe(progress_line)

            if con_stdout!=None:
                con_stdout.SetConsoleTextAttribute(con_attr)
            
            pe("\n")

        r=0
        if not options.dry_run:
            r=subprocess.call(argv,
                              shell=options.shell)
            
        #r=os.system(cmd)
        if r!=0:
            if not options.keep_going_quietly:
                pe("%s: Command returned %d: %s\n"%("WARNING" if options.keep_going else "ERROR",
                                                    r,
                                                    " ".join(argv)))

            if not options.keep_going:
                return 1

        if options.progress and not options.verbose:
            pe(" "*len(progress_line)+"\r")

    return 0

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

    parser.add_argument("-n",
                        "--dry-run",
                        default=False,
                        action="store_true",
                        help=
                        """If specified, don't actually run any commands (implies --progress and --verbose).""")

    parser.add_argument("-k",
                        "--keep-going",
                        default=False,
                        action="store_true",
                        help=
                        """If specified, keep going even when a command fails.""")

    parser.add_argument("-K",
                        "--keep-going-quietly",
                        default=False,
                        action="store_true",
                        help=
                        """If specified, keep going even when a
                        command fails, and don't print a warning.

                        """)

    # parser.add_argument("--max-args",
    #                     metavar="MAX-ARGS",
    #                     default=1,
    #                     help=
    #                     """Use at most %(metavar)s arguments (default %(default)s) per command line. 

    # Work up to the '-'
    argv=sys.argv[1:]
    
    if not "-" in argv:
        sep_index=len(argv)
    else:
        sep_index=argv.index("-")

    old_title=None
    if got_win32console:
        old_title=win32console.GetConsoleTitle()

    result=main(parser.parse_args(argv[:sep_index]),
                argv[sep_index+1:])

    if got_win32console:
        if old_title is not None:
            win32console.SetConsoleTitle(old_title)
    
    sys.exit(result)
    
