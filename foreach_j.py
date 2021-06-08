##########################################################################
##########################################################################

from __future__ import print_function
import sys,argparse,os,subprocess,ctypes,term_tools,multiprocessing,threading,collections,signal
    
##########################################################################
##########################################################################

def flushall():
    sys.stdout.flush()
    sys.stderr.flush()

def pe(str):
    sys.stderr.write(str)
    sys.stderr.flush()

##########################################################################
##########################################################################

def get_quoted_arg(x):
    if ' ' in x: return '"%s"'%x
    else: return x

##########################################################################
##########################################################################

class JobQueue:
    def __init__(self):
        self.jobs=[]
        self.results=[]
        self.index=0

    def add(self,job):
        self.jobs.append(job)
        self.results.append(None)

##########################################################################
##########################################################################

Job=collections.namedtuple('Job','argv')

JobResult=collections.namedtuple('JobResult','returncode stdout stderr')

##########################################################################
##########################################################################

class JobsThread(threading.Thread):
    def __init__(self,thread_index,queue,cv,shell):
        threading.Thread.__init__(self)
        self.thread_index=thread_index
        self._queue=queue
        self._cv=cv
        self.pid=None
        self._shell=shell

    def run(self):
        while True:
            with self._cv:
                assert self._queue.index<=len(self._queue.jobs)
                if self._queue.index==len(self._queue.jobs): break

                index=self._queue.index
                self._queue.index+=1
                
                job=self._queue.jobs[index]
                assert index<=len(self._queue.results),(index,len(self._queue.results))

                # print(job.argv)
                process=subprocess.Popen(args=job.argv,
                                         shell=self._shell,
                                         stdin=None,#subprocess.PIPE,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)

                self.pid=process.pid
            
            stdout,stderr=process.communicate(None)
            
            with self._cv:
                self.pid=None
                assert self._queue.results[index] is None
                print('%d: %d -> %d'%(self.thread_index,index,process.returncode))
                self._queue.results[index]=JobResult(process.returncode,
                                                     stdout,
                                                     stderr)
                self._cv.notify()
        
##########################################################################
##########################################################################

def main2(options,
          cmd_argv):
    if len(cmd_argv)==0:
        pe("FATAL: No command specified.\n")
        sys.exit(1)

    if len(options.inputs)==0: lines=sys.stdin.readlines()
    else:
        lines=[]
        for i in options.inputs:
            with open(i,"rt") as f: lines+=f.readlines()

    queue=JobQueue()
    for line in lines:
        # Replace -I string with the input line, or append it to the
        # supplied argv.
        argv=[]
        line=line.strip()
        replaced=False
        for arg in cmd_argv:
            new_arg=arg.replace(options.replstr,line)
            if new_arg!=arg: replaced=True
            argv.append(new_arg)
        if not replaced: argv.append(line)

        job=Job(argv)
        queue.add(job)

    print('%d job(s)'%len(queue.jobs))

    job_lock=threading.Lock()
    job_cv=threading.Condition(job_lock)

    num_threads=multiprocessing.cpu_count()
    #num_threads=1

    threads=[]
    for i in range(num_threads):
        thread=JobsThread(i,queue,job_cv,options.shell)
        threads.append(thread)

    for thread in threads: thread.start()

    result_index=0
    while True:
        new_results=[]
        while len(new_results)==0:
            with job_cv:
                if result_index==len(queue.results): break

                if queue.results[result_index] is None: job_cv.wait()

                num_jobs=len(queue.results)
                job_index=queue.index

                while (result_index<len(queue.results) and
                       queue.results[result_index] is not None):
                    new_results.append(queue.results[result_index])
                    result_index+=1

        if len(new_results)==0: break

        print('qi=%d ri=%d tot=%d'%(job_index,result_index,num_jobs))
            
        for new_result in new_results:
            if new_result.stdout is not None:
                sys.stdout.write(new_result.stdout)
                sys.stdout.flush()
                
            if new_result.stderr is not None:
                sys.stderr.write(new_result.stderr)
                sys.stderr.flush()

            if new_result.returncode!=0:
                if not options.keep_going_quietly:
                    prefix='WARNING' if options.keep_going else 'ERROR'
                    pe('%s: command returned %d: %s\n'%(prefix,
                                                        new_result.returncode,
                                                        ' '.join(job.argv)))

                if not options.keep_going:
                    with job_cv:
                        for thread in threads:
                            if thread.pid is not None:
                                os.kill(thread.pid,signal.SIGTERM)
                            
                        queue.result_index=len(queue.results)

                        break

    for thread in threads: thread.join()

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

        cmd_line=" ".join([get_quoted_arg(arg) for arg in argv])

        if options.verbose: progress_line+=cmd_line

        term_tools.set_title("%d/%d: %s"%(1+i,n,cmd_line))

        if options.progress and not options.verbose:
            pe(progress_line)
            pe("\r")
        elif options.progress or options.verbose:
            con_stdout=None

            with term_tools.TextColourInverter(): pe(progress_line)

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

class MultiprocessingAction(argparse.Action):
    def __init__(self,
                 option_strings,
                 dest,
                 nargs=None,
                 **kwargs):
        print('%r %r %r %r'%(option_strings,dest,nargs,kwargs))
        super(MultiprocessingAction,self).__init__(option_strings,
                                                   dest,
                                                   **kwargs)
    def __call__(self,parser,namespace,values,option_string=None):
        print('%r %r %r'%(namespace,values,option_string))
        #setattr(namespace,self.dest,values)

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

    parser.add_argument('-j',
                        dest='multiprocess',
                        action='store_true',
                        help='''if specified, run multiple processes simultaneously''')

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

    # old_title=None
    # if got_win32console:
    #     old_title=win32console.GetConsoleTitle()

    result=main2(parser.parse_args(argv[:sep_index]),argv[sep_index+1:])

    # if got_win32console:
    #     if old_title is not None:
    #         win32console.SetConsoleTitle(old_title)
    
    sys.exit(result)
    
