#pragma D option quiet

/*
 * Command line arguments
 */
inline int OPT_has_target   = OPT_HAS_TARGET;
inline int OPT_follow    = OPT_FOLLOW;
inline int OPT_printid   = OPT_PRINTID;
inline int OPT_relative  = OPT_RELATIVE;
inline int OPT_elapsed   = OPT_ELAPSED;
inline int OPT_cpu       = OPT_CPU;
inline int OPT_counts    = OPT_COUNTS;
inline int OPT_pid       = OPT_PID;
inline int OPT_name      = OPT_NAME;
inline int OPT_trace     = OPT_TRACE;
inline int OPT_stack     = OPT_STACK;
inline int PID           = OPT_PID_VALUE;
inline string NAME       = OPT_NAME_VALUE;
inline string TRACE      = OPT_TRACE_VALUE;

/* Flag values for renameatx_np */
inline u_int RENAME_SECLUDE = 0x00000001;
inline u_int RENAME_SWAP = 0x00000002;
inline u_int RENAME_EXCL = 0x00000004;

dtrace:::BEGIN 
{
    /* print header */
    /* OPT_printid  ? printf("%-8s  ","PID/LWP") : 1; */
    OPT_printid  ? printf("\t%-8s  ","PID/THRD") : 1;
    OPT_relative ? printf("%8s ","RELATIVE") : 1;
    OPT_elapsed  ? printf("%7s ","ELAPSD") : 1;
    OPT_cpu      ? printf("%6s ","CPU") : 1;
    printf("SYSCALL(args) \t\t = return\n");

    /* Apple: Names of top-level sysctl MIBs */
    sysctl_first[0] = "CTL_UNSPEC";
    sysctl_first[1] = "CTL_KERN";
    sysctl_first[2] = "CTL_VM";
    sysctl_first[3] = "CTL_VFS";
    sysctl_first[4] = "CTL_NET";
    sysctl_first[5] = "CTL_DEBUG";
    sysctl_first[6] = "CTL_HW";
    sysctl_first[7] = "CTL_MACHDEP";
    sysctl_first[9] = "CTL_MAXID";

    /* globals */
    self->child = 0;
    this->type = 0;
}

/*
 * Save syscall entry info
 */

/* MacOS X: notice first appearance of child from fork. Its parent
   fires syscall::*fork:return in the ususal way (see below) */
syscall:::entry
/(OPT_follow && progenyof($target)) && 0 == self->child/
{
    /* set as child */
    self->child = 1;

    /* print output */
    self->code = errno == 0 ? "" : "Err#";
    /* OPT_printid  ? printf("%5d/%d:  ",pid,tid) : 1; */
    OPT_printid  ? printf("%5d/0x%x:  ",pid,tid) : 1;
    OPT_relative ? printf("%8d:  ",vtimestamp/1000) : 1;
    OPT_elapsed  ? printf("%7d:  ",0) : 1;
    OPT_cpu      ? printf("%6d ",0) : 1;
    printf("%s()\t\t = %d %s%d\n","fork",
           0,self->code,(int)errno);
}

syscall:::entry
/(OPT_has_target && pid == $target) ||
(OPT_pid && pid == PID) ||
(OPT_name && NAME == strstr(NAME, execname)) ||
(OPT_name && execname == strstr(execname, NAME)) ||
(self->child)/
{
    /* set start details */
    self->start = timestamp;
    self->vstart = vtimestamp;
    self->arg0 = arg0;
    self->arg1 = arg1;
    self->arg2 = arg2;

    /* count occurances */
    OPT_counts == 1 ? @Counts[probefunc] = count() : 1;
}

/* 4, 5 and 6 arguments */
syscall::select:entry,
    syscall::mmap:entry,
    syscall::pwrite:entry,
    syscall::pread:entry,
    syscall::openat:entry,
    syscall::unlinkat:entry,
    syscall::getattrlistat:entry,
    syscall::readlinkat:entry,
    syscall::linkat:entry,
    syscall::fchownat:entry,
    syscall::renameat:entry,
    syscall::renameatx_np:entry,
    syscall::sysctl:entry,
    syscall::sysctlbyname:entry,
    syscall::faccessat:entry,
    syscall::kdebug_trace64:entry
    /(OPT_has_target && pid == $target) ||
    (OPT_pid && pid == PID) ||
    (OPT_name && NAME == strstr(NAME, execname)) ||
    (OPT_name && execname == strstr(execname, NAME)) ||
    (self->child)/
    {
        self->arg3 = arg3;
        self->arg4 = arg4;
        self->arg5 = arg5;
    }

/* syscall::rexit:entry */
syscall::exit:entry
{
    /* forget child */
    self->child = 0;
}

/*
 * Check for syscall tracing
 */
syscall:::entry
/OPT_trace && probefunc != TRACE/
{
    /* drop info */
    self->start = 0;
    self->vstart = 0;
    self->arg0 = 0;
    self->arg1 = 0;
    self->arg2 = 0;
    self->arg3 = 0;
    self->arg4 = 0;
    self->arg5 = 0;
}

/*
 * Print return data
 */

/*
 * NOTE:
 *  The following code is written in an intentionally repetetive way.
 *  The first versions had no code redundancies, but performed badly during
 *  benchmarking. The priority here is speed, not cleverness. I know there
 *  are many obvious shortcuts to this code, Ive tried them. This style has
 *  shown in benchmarks to be the fastest (fewest probes, fewest actions).
 */

/* print 3 args, return as hex */
syscall::sigprocmask:return
/self->start/
{
    /* calculate elapsed time */
    this->elapsed = timestamp - self->start;
    self->start = 0;
    this->cpu = vtimestamp - self->vstart;
    self->vstart = 0;
    self->code = errno == 0 ? "" : "Err#";

    /* print optional fields */
    /* OPT_printid  ? printf("%5d/%d:  ",pid,tid) : 1; */
    OPT_printid  ? printf("%5d/0x%x:  ",pid,tid) : 1;
    OPT_relative ? printf("%8d ",vtimestamp/1000) : 1;
    OPT_elapsed  ? printf("%7d ",this->elapsed/1000) : 1;
    OPT_cpu ? printf("%6d ",this->cpu/1000) : 1;

    /* print main data */
    printf("%s(0x%X, 0x%X, 0x%X)\t\t = 0x%X %s%d\n",probefunc,
           (int)self->arg0,self->arg1,self->arg2,(int)arg0,
           self->code,(int)errno);
    OPT_stack ? ustack()    : 1;
    OPT_stack ? trace("\n") : 1;
    self->arg0 = 0;
    self->arg1 = 0;
    self->arg2 = 0;
}

/* print 3 args, arg0 as a string */
syscall::execve:return,
    syscall::stat:return,
    syscall::stat64:return,
    syscall::lstat:return,
    syscall::lstat64:return,
    syscall::access:return,
    syscall::mkdir:return,
    syscall::chdir:return,
    syscall::chroot:return,
    syscall::getattrlist:return, /* XXX 5 arguments */
    syscall::chown:return,
    syscall::lchown:return,
    syscall::chflags:return,
    syscall::readlink:return,
    syscall::utimes:return,
    syscall::pathconf:return,
    syscall::truncate:return,
    syscall::getxattr:return,
    syscall::setxattr:return,
    syscall::removexattr:return,
    syscall::unlink:return,
    syscall::open:return,
    syscall::open_nocancel:return
    /self->start/
    {
        /* calculate elapsed time */
        this->elapsed = timestamp - self->start;
        self->start = 0;
        this->cpu = vtimestamp - self->vstart;
        self->vstart = 0;
        self->code = errno == 0 ? "" : "Err#";

        /* print optional fields */
        /* OPT_printid  ? printf("%5d/%d:  ",pid,tid) : 1; */
        OPT_printid  ? printf("%5d/0x%x:  ",pid,tid) : 1;
        OPT_relative ? printf("%8d ",vtimestamp/1000) : 1;
        OPT_elapsed  ? printf("%7d ",this->elapsed/1000) : 1;
        OPT_cpu      ? printf("%6d ",this->cpu/1000) : 1;

        /* print main data */
        printf("%s(\"%S\", 0x%X, 0x%X)\t\t = %d %s%d\n",probefunc,
               copyinstr(self->arg0),self->arg1,self->arg2,(int)arg0,
               self->code,(int)errno);
        OPT_stack ? ustack()    : 1;
        OPT_stack ? trace("\n") : 1;
        self->arg0 = 0;
        self->arg1 = 0;
        self->arg2 = 0;
    }

/* print 3 args, arg1 as a string, for read/write variant */
syscall::write:return,
    syscall::write_nocancel:return,
    syscall::read:return,
    syscall::read_nocancel:return
    /self->start/
    {
        /* calculate elapsed time */
        this->elapsed = timestamp - self->start;
        self->start = 0;
        this->cpu = vtimestamp - self->vstart;
        self->vstart = 0;
        self->code = errno == 0 ? "" : "Err#";

        /* print optional fields */
        /* OPT_printid  ? printf("%5d/%d:  ",pid,tid) : 1; */
        OPT_printid  ? printf("%5d/0x%x:  ",pid,tid) : 1;
        OPT_relative ? printf("%8d ",vtimestamp/1000) : 1;
        OPT_elapsed  ? printf("%7d ",this->elapsed/1000) : 1;
        OPT_cpu      ? printf("%6d ",this->cpu/1000) : 1;

        /* print main data */
        printf("%s(0x%X, \"%S\", 0x%X)\t\t = %d %s%d\n",probefunc,self->arg0,
               arg0 == -1 ? "" : stringof(copyin(self->arg1,arg0)),self->arg2,(int)arg0,
               self->code,(int)errno);
        OPT_stack ? ustack()    : 1;
        OPT_stack ? trace("\n") : 1;
        self->arg0 = 0;
        self->arg1 = 0;
        self->arg2 = 0;
    }

/* print 3 args, arg1 as a string */
syscall::mkdirat:return,
    syscall::unlinkat:return
    /self->start/
    {
        /* calculate elapsed time */
        this->elapsed = timestamp - self->start;
        self->start = 0;
        this->cpu = vtimestamp - self->vstart;
        self->vstart = 0;
        self->code = errno == 0 ? "" : "Err#";

        /* print optional fields */
        /* OPT_printid  ? printf("%5d/%d:  ",pid,tid) : 1; */
        OPT_printid  ? printf("%5d/0x%x:  ",pid,tid) : 1;
        OPT_relative ? printf("%8d ",vtimestamp/1000) : 1;
        OPT_elapsed  ? printf("%7d ",this->elapsed/1000) : 1;
        OPT_cpu      ? printf("%6d ",this->cpu/1000) : 1;

        /* print main data */
        printf("%s(0x%X, \"%S\", 0x%X)\t\t = %d %s%d\n",probefunc,self->arg0,
               copyinstr(self->arg1),self->arg2,(int)arg0,
               self->code,(int)errno);
        OPT_stack ? ustack()    : 1;
        OPT_stack ? trace("\n") : 1;
        self->arg0 = 0;
        self->arg1 = 0;
        self->arg2 = 0;
    }

/* print 3 args, arg0 and arg2 as strings */
syscall::symlinkat:return
/self->start/
{
    /* calculate elapsed time */
    this->elapsed = timestamp - self->start;
    self->start = 0;
    this->cpu = vtimestamp - self->vstart;
    self->vstart = 0;
    self->code = errno == 0 ? "" : "Err#";

    /* print optional fields */
    /* OPT_printid  ? printf("%5d/%d:  ",pid,tid) : 1; */
    OPT_printid  ? printf("%5d/0x%x:  ",pid,tid) : 1;
    OPT_relative ? printf("%8d ",vtimestamp/1000) : 1;
    OPT_elapsed  ? printf("%7d ",this->elapsed/1000) : 1;
    OPT_cpu      ? printf("%6d ",this->cpu/1000) : 1;

    /* print main data */
    printf("%s(\"%S\", 0x%X, \"%S\")\t\t = %d %s%d\n",probefunc,
           copyinstr(self->arg0), self->arg1, copyinstr(self->arg2), (int)arg0,
           self->code,(int)errno);
    OPT_stack ? ustack()    : 1;
    OPT_stack ? trace("\n") : 1;
    self->arg0 = 0;
    self->arg1 = 0;
    self->arg2 = 0;
}


/* print 2 args, arg0 and arg1 as strings */
syscall::rename:return,
    syscall::symlink:return,
    syscall::link:return
    /self->start/
    {
        /* calculate elapsed time */
        this->elapsed = timestamp - self->start;
        self->start = 0;
        this->cpu = vtimestamp - self->vstart;
        self->vstart = 0;
        self->code = errno == 0 ? "" : "Err#";

        /* print optional fields */
        OPT_printid  ? printf("%5d/0x%x:  ",pid,tid) : 1;
        OPT_relative ? printf("%8d ",vtimestamp/1000) : 1;
        OPT_elapsed  ? printf("%7d ",this->elapsed/1000) : 1;
        OPT_cpu      ? printf("%6d ",this->cpu/1000) : 1;

        /* print main data */
        printf("%s(\"%S\", \"%S\")\t\t = %d %s%d\n",probefunc,
               copyinstr(self->arg0), copyinstr(self->arg1),
               (int)arg0,self->code,(int)errno);
        OPT_stack ? ustack()    : 1;
        OPT_stack ? trace("\n") : 1;
        self->arg0 = 0;
        self->arg1 = 0;
        self->arg2 = 0;
    }

/* print 0 arg output */
syscall::*fork:return
/self->start/
{
    /* calculate elapsed time */
    this->elapsed = timestamp - self->start;
    self->start = 0;
    this->cpu = vtimestamp - self->vstart;
    self->vstart = 0;
    self->code = errno == 0 ? "" : "Err#";

    /* print optional fields */
    OPT_printid  ? printf("%5d/0x%x:  ",pid,tid) : 1;
    OPT_relative ? printf("%8d ",vtimestamp/1000) : 1;
    OPT_elapsed  ? printf("%7d ",this->elapsed/1000) : 1;
    OPT_cpu      ? printf("%6d ",this->cpu/1000) : 1;

    /* print main data */
    printf("%s()\t\t = %d %s%d\n",probefunc,
           (int)arg0,self->code,(int)errno);
    OPT_stack ? ustack()    : 1;
    OPT_stack ? trace("\n") : 1;
    self->arg0 = 0;
    self->arg1 = 0;
    self->arg2 = 0;
}

/* print 1 arg output */
syscall::close:return,
    syscall::close_nocancel:return
    /self->start/
    {
        /* calculate elapsed time */
        this->elapsed = timestamp - self->start;
        self->start = 0;
        this->cpu = vtimestamp - self->vstart;
        self->vstart = 0;
        self->code = errno == 0 ? "" : "Err#";

        /* print optional fields */
        OPT_printid  ? printf("%5d/0x%x:  ",pid,tid) : 1;
        OPT_relative ? printf("%8d ",vtimestamp/1000) : 1;
        OPT_elapsed  ? printf("%7d ",this->elapsed/1000) : 1;
        OPT_cpu      ? printf("%6d ",this->cpu/1000) : 1;

        /* print main data */
        printf("%s(0x%X)\t\t = %d %s%d\n",probefunc,self->arg0,
               (int)arg0,self->code,(int)errno);
        OPT_stack ? ustack()    : 1;
        OPT_stack ? trace("\n") : 1;
        self->arg0 = 0;
        self->arg1 = 0;
        self->arg2 = 0;
    }

/* print 2 arg output */
syscall::utimes:return,
    syscall::munmap:return
    /self->start/
    {
        /* calculate elapsed time */
        this->elapsed = timestamp - self->start;
        self->start = 0;
        this->cpu = vtimestamp - self->vstart;
        self->vstart = 0;
        self->code = errno == 0 ? "" : "Err#";

        /* print optional fields */
        OPT_printid  ? printf("%5d/0x%x:  ",pid,tid) : 1;
        OPT_relative ? printf("%8d ",vtimestamp/1000) : 1;
        OPT_elapsed  ? printf("%7d ",this->elapsed/1000) : 1;
        OPT_cpu      ? printf("%6d ",this->cpu/1000) : 1;

        /* print main data */
        printf("%s(0x%X, 0x%X)\t\t = %d %s%d\n",probefunc,self->arg0,
               self->arg1,(int)arg0,self->code,(int)errno);
        OPT_stack ? ustack()    : 1;
        OPT_stack ? trace("\n") : 1;
        self->arg0 = 0;
        self->arg1 = 0;
        self->arg2 = 0;
    }

/* print pread/pwrite with 4 arguments */
syscall::pread*:return,
    syscall::pwrite*:return
    /self->start/
    {
        /* calculate elapsed time */
        this->elapsed = timestamp - self->start;
        self->start = 0;
        this->cpu = vtimestamp - self->vstart;
        self->vstart = 0;
        self->code = errno == 0 ? "" : "Err#";

        /* print optional fields */
        OPT_printid  ? printf("%5d/0x%x:  ",pid,tid) : 1;
        OPT_relative ? printf("%8d ",vtimestamp/1000) : 1;
        OPT_elapsed  ? printf("%7d ",this->elapsed/1000) : 1;
        OPT_cpu      ? printf("%6d ",this->cpu/1000) : 1;

        /* print main data */
        printf("%s(0x%X, \"%S\", 0x%X, 0x%X)\t\t = %d %s%d\n",probefunc,self->arg0,
               stringof(copyin(self->arg1,self->arg2)),self->arg2,self->arg3,(int)arg0,self->code,(int)errno);
        OPT_stack ? ustack()    : 1;
        OPT_stack ? trace("\n") : 1;
        self->arg0 = 0;
        self->arg1 = 0;
        self->arg2 = 0;
        self->arg3 = 0;
    }

/* print 4 args, arg1 as string */
syscall::openat:return,
    syscall::faccessat:return,
    syscall::fchmodat:return,
    syscall::readlinkat:return,
    syscall::fstatat:return
    /self->start/
    {
        /* calculate elapsed time */
        this->elapsed = timestamp - self->start;
        self->start = 0;
        this->cpu = vtimestamp - self->vstart;
        self->vstart = 0;
        self->code = errno == 0 ? "" : "Err#";

        /* print optional fields */
        OPT_printid  ? printf("%5d/0x%x:  ",pid,tid) : 1;
        OPT_relative ? printf("%8d ",vtimestamp/1000) : 1;
        OPT_elapsed  ? printf("%7d ",this->elapsed/1000) : 1;
        OPT_cpu      ? printf("%6d ",this->cpu/1000) : 1;

        /* print main data */
        printf("%s(0x%X, \"%S\", 0x%X, 0x%X)\t\t = %d %s%d\n",probefunc,
               self->arg0, copyinstr(self->arg1),self->arg2,self->arg3,(int)arg0,
               self->code,(int)errno);
        OPT_stack ? ustack()    : 1;
        OPT_stack ? trace("\n") : 1;
        self->arg0 = 0;
        self->arg1 = 0;
        self->arg2 = 0;
        self->arg3 = 0;
    }

/* print 4 args, arg1 and arg3 as strings */
syscall::renameat:return
/self->start/
{
    /* calculate elapsed time */
    this->elapsed = timestamp - self->start;
    self->start = 0;
    this->cpu = vtimestamp - self->vstart;
    self->vstart = 0;
    self->code = errno == 0 ? "" : "Err#";

    /* print optional fields */
    OPT_printid  ? printf("%5d/0x%x:  ",pid,tid) : 1;
    OPT_relative ? printf("%8d ",vtimestamp/1000) : 1;
    OPT_elapsed  ? printf("%7d ",this->elapsed/1000) : 1;
    OPT_cpu      ? printf("%6d ",this->cpu/1000) : 1;

    /* print main data */
    printf("%s(0x%X, \"%S\", 0x%X, \"%S\")\t\t = %d %s%d\n",probefunc,
           self->arg0, copyinstr(self->arg1), self->arg2, copyinstr(self->arg3), (int)arg0,
           self->code,(int)errno);
    OPT_stack ? ustack()    : 1;
    OPT_stack ? trace("\n") : 1;
    self->arg0 = 0;
    self->arg1 = 0;
    self->arg2 = 0;
    self->arg3 = 0;
}

/* print 5 args, arg1 and arg3 as strings */
syscall::renameatx_np:return
/self->start/
{
    /* calculate elapsed time */
    this->elapsed = timestamp - self->start;
    self->start = 0;
    this->cpu = vtimestamp - self->vstart;
    self->vstart = 0;
    self->code = errno == 0 ? "" : "Err#";

    /* print optional fields */
    OPT_printid  ? printf("%5d/0x%x:  ",pid,tid) : 1;
    OPT_relative ? printf("%8d ",vtimestamp/1000) : 1;
    OPT_elapsed  ? printf("%7d ",this->elapsed/1000) : 1;
    OPT_cpu      ? printf("%6d ",this->cpu/1000) : 1;

    /* print main data */
    printf("%s(0x%X, \"%S\", 0x%X, \"%S\", %s|%s|%s)\t\t = %d %s%d\n",probefunc,
           self->arg0, copyinstr(self->arg1), self->arg2, copyinstr(self->arg3),
           ((self->arg4 & RENAME_SECLUDE) ? "RENAME_SECLUDE" : "0"),
           ((self->arg4 & RENAME_SWAP) ? "RENAME_SWAP" : "0"),
           ((self->arg4 & RENAME_EXCL) ? "RENAME_EXCL" : "0"),
           (int)arg0,
           self->code,(int)errno);
    OPT_stack ? ustack()    : 1;
    OPT_stack ? trace("\n") : 1;
    self->arg0 = 0;
    self->arg1 = 0;
    self->arg2 = 0;
    self->arg3 = 0;
}

/* Apple: print the arguments passed to sysctl */
syscall::sysctl:return
/self->start/
{
    /* calculate elapsed time */
    this->elapsed = timestamp - self->start;
    self->start = 0;
    this->cpu = vtimestamp - self->vstart;
    self->vstart = 0;
    self->code = errno == 0 ? "" : "Err#";

    /* print optional fields */
    OPT_printid  ? printf("%5d/0x%x:  ",pid,tid) : 1;
    OPT_relative ? printf("%8d ",vtimestamp/1000) : 1;
    OPT_elapsed  ? printf("%7d ",this->elapsed/1000) : 1;
    OPT_cpu      ? printf("%6d ",this->cpu/1000) : 1;

    /* print main data */
    mib = copyin(self->arg0, self->arg1 * sizeof(int));
    mib1 = *(int *)mib;
    mib2 = *((int *)mib + 1);

    printf("%s(", probefunc);

    printf("[%s, ", (self->arg1 > 0) ? ((*(int *)mib > 0 && *(int *)mib < 9) ? sysctl_first[mib1] : "unknown") : 0);

    printf("%d, %d, %d, %d, %d] (%d), ",
           (self->arg1 > 1) ? *((int *)mib + 1) : 0,
           (self->arg1 > 2) ? *((int *)mib + 2) : 0,
           (self->arg1 > 3) ? *((int *)mib + 3) : 0,
           (self->arg1 > 4) ? *((int *)mib + 4) : 0,
           (self->arg1 > 5) ? *((int *)mib + 5) : 0,
           self->arg1);

    printf("0x%X, 0x%X, 0x%X, 0x%X)\t\t = %d %s%d\n",
           self->arg2, self->arg3, self->arg4, self->arg5,
           (int)arg0, self->code, (int)errno);
    OPT_stack ? ustack()    : 1;
    OPT_stack ? trace("\n") : 1;
    self->arg0 = 0;
    self->arg1 = 0;
    self->arg2 = 0;
    self->arg3 = 0;
    self->arg4 = 0;
    self->arg5 = 0;
}

/* Apple: print the string provided to sysctlbyname */
syscall::sysctlbyname:return
/self->start/
{
    /* calculate elapsed time */
    this->elapsed = timestamp - self->start;
    self->start = 0;
    this->cpu = vtimestamp - self->vstart;
    self->vstart = 0;
    self->code = errno == 0 ? "" : "Err#";

    /* print optional fields */
    OPT_printid  ? printf("%5d/0x%x:  ",pid,tid) : 1;
    OPT_relative ? printf("%8d ",vtimestamp/1000) : 1;
    OPT_elapsed  ? printf("%7d ",this->elapsed/1000) : 1;
    OPT_cpu      ? printf("%6d ",this->cpu/1000) : 1;

    /* print main data */
    printf("%s(%s, 0x%X, 0x%X, 0x%X, 0x%X)\t\t = %d %s%d\n",probefunc,
           copyinstr(self->arg0),
           self->arg1,self->arg2,self->arg3,self->arg4,(int)arg0,self->code,(int)errno);
    OPT_stack ? ustack()    : 1;
    OPT_stack ? trace("\n") : 1;
    self->arg0 = 0;
    self->arg1 = 0;
    self->arg2 = 0;
    self->arg3 = 0;
    self->arg4 = 0;
}

/* print 5 arguments */
syscall::kdebug_trace64:return,
    syscall::select:return
    /self->start/
    {
        /* calculate elapsed time */
        this->elapsed = timestamp - self->start;
        self->start = 0;
        this->cpu = vtimestamp - self->vstart;
        self->vstart = 0;
        self->code = errno == 0 ? "" : "Err#";

        /* print optional fields */
        OPT_printid  ? printf("%5d/0x%x:  ",pid,tid) : 1;
        OPT_relative ? printf("%8d ",vtimestamp/1000) : 1;
        OPT_elapsed  ? printf("%7d ",this->elapsed/1000) : 1;
        OPT_cpu      ? printf("%6d ",this->cpu/1000) : 1;

        /* print main data */
        printf("%s(0x%X, 0x%X, 0x%X, 0x%X, 0x%X)\t\t = %d %s%d\n",probefunc,self->arg0,
               self->arg1,self->arg2,self->arg3,self->arg4,(int)arg0,self->code,(int)errno);
        OPT_stack ? ustack()    : 1;
        OPT_stack ? trace("\n") : 1;
        self->arg0 = 0;
        self->arg1 = 0;
        self->arg2 = 0;
        self->arg3 = 0;
        self->arg4 = 0;
    }

/* print 5 args, arg1 as string */
syscall::fchownat:return
/self->start/
{
    /* calculate elapsed time */
    this->elapsed = timestamp - self->start;
    self->start = 0;
    this->cpu = vtimestamp - self->vstart;
    self->vstart = 0;
    self->code = errno == 0 ? "" : "Err#";

    /* print optional fields */
    OPT_printid  ? printf("%5d/0x%x:  ",pid,tid) : 1;
    OPT_relative ? printf("%8d ",vtimestamp/1000) : 1;
    OPT_elapsed  ? printf("%7d ",this->elapsed/1000) : 1;
    OPT_cpu      ? printf("%6d ",this->cpu/1000) : 1;

    /* print main data */
    printf("%s(0x%X, \"%S\", 0x%X, 0x%X, 0x%X)\t\t = %d %s%d\n",probefunc,
           self->arg0, copyinstr(self->arg1), self->arg2, self->arg3, self->arg4,
           (int)arg0,self->code,(int)errno);

    OPT_stack ? ustack()    : 1;
    OPT_stack ? trace("\n") : 1;
    self->arg0 = 0;
    self->arg1 = 0;
    self->arg2 = 0;
    self->arg3 = 0;
    self->arg4 = 0;
}
/* print 5 args, arg1 and arg3 as strings */
syscall::linkat:return
/self->start/
{
    /* calculate elapsed time */
    this->elapsed = timestamp - self->start;
    self->start = 0;
    this->cpu = vtimestamp - self->vstart;
    self->vstart = 0;
    self->code = errno == 0 ? "" : "Err#";

    /* print optional fields */
    OPT_printid  ? printf("%5d/0x%x:  ",pid,tid) : 1;
    OPT_relative ? printf("%8d ",vtimestamp/1000) : 1;
    OPT_elapsed  ? printf("%7d ",this->elapsed/1000) : 1;
    OPT_cpu      ? printf("%6d ",this->cpu/1000) : 1;

    /* print main data */
    printf("%s(0x%X, \"%S\", 0x%X, \"%S\", 0x%X)\t\t = %d %s%d\n",probefunc,
           self->arg0, copyinstr(self->arg1), self->arg2, self->arg3 ? copyinstr(self->arg3) : "", self->arg4,
           (int)arg0,self->code,(int)errno);

    OPT_stack ? ustack()    : 1;
    OPT_stack ? trace("\n") : 1;
    self->arg0 = 0;
    self->arg1 = 0;
    self->arg2 = 0;
    self->arg3 = 0;
    self->arg4 = 0;
}

/* getattrlistat has 6 arguments */
syscall::getattrlistat:return
/self->start/
{
    /* calculate elapsed time */
    this->elapsed = timestamp - self->start;
    self->start = 0;
    this->cpu = vtimestamp - self->vstart;
    self->vstart = 0;
    self->code = errno == 0 ? "" : "Err#";

    /* print optional fields */
    OPT_printid  ? printf("%5d/0x%x:  ",pid,tid) : 1;
    OPT_relative ? printf("%8d ",vtimestamp/1000) : 1;
    OPT_elapsed  ? printf("%7d ",this->elapsed/1000) : 1;
    OPT_cpu      ? printf("%6d ",this->cpu/1000) : 1;

    /* print main data */
    printf("%s(0x%X, \"%S\", 0x%X, 0x%X, 0x%X, 0x%X)\t\t = 0x%X %s%d\n",probefunc,self->arg0,
           copyinstr(self->arg1),self->arg2,self->arg3,self->arg4,self->arg5, arg0,self->code,(int)errno);
    OPT_stack ? ustack()    : 1;
    OPT_stack ? trace("\n") : 1;
    self->arg0 = 0;
    self->arg1 = 0;
    self->arg2 = 0;
    self->arg3 = 0;
    self->arg4 = 0;
    self->arg5 = 0;
}

/* kill has 2 args that should be shown as decimal*/
syscall::kill:return
/self->start/
{
    /* calculate elapsed time */
    this->elapsed = timestamp - self->start;
    self->start = 0;
    this->cpu = vtimestamp - self->vstart;
    self->vstart = 0;
    self->code = errno == 0 ? "" : "Err#";

    /* print optional fields */
    OPT_printid  ? printf("%5d/0x%x:  ",pid,tid) : 1;
    OPT_relative ? printf("%8d ",vtimestamp/1000) : 1;
    OPT_elapsed  ? printf("%7d ",this->elapsed/1000) : 1;
    OPT_cpu      ? printf("%6d ",this->cpu/1000) : 1;

    /* print main data */
    printf("%s(%d, %d)\t\t = %d %s%d\n",probefunc,self->arg0,
           self->arg1,(int)arg0,self->code,(int)errno);
    OPT_stack ? ustack()    : 1;
    OPT_stack ? trace("\n") : 1;
    self->arg0 = 0;
    self->arg1 = 0;
}

/* mmap has 6 arguments */
syscall::mmap:return
/self->start/
{
    /* calculate elapsed time */
    this->elapsed = timestamp - self->start;
    self->start = 0;
    this->cpu = vtimestamp - self->vstart;
    self->vstart = 0;
    self->code = errno == 0 ? "" : "Err#";

    /* print optional fields */
    OPT_printid  ? printf("%5d/0x%x:  ",pid,tid) : 1;
    OPT_relative ? printf("%8d ",vtimestamp/1000) : 1;
    OPT_elapsed  ? printf("%7d ",this->elapsed/1000) : 1;
    OPT_cpu      ? printf("%6d ",this->cpu/1000) : 1;

    /* print main data */
    printf("%s(0x%X, 0x%X, 0x%X, 0x%X, 0x%X, 0x%X)\t\t = 0x%X %s%d\n",probefunc,self->arg0,
           self->arg1,self->arg2,self->arg3,self->arg4,self->arg5, arg0,self->code,(int)errno);
    OPT_stack ? ustack()    : 1;
    OPT_stack ? trace("\n") : 1;
    self->arg0 = 0;
    self->arg1 = 0;
    self->arg2 = 0;
    self->arg3 = 0;
    self->arg4 = 0;
    self->arg5 = 0;
}

/* ioctl */
syscall::ioctl:return
/self->start/
{
    /* calculate elapsed time */
    this->elapsed = timestamp - self->start;
    self->start = 0;
    this->cpu = vtimestamp - self->vstart;
    self->vstart = 0;
    self->code = errno == 0 ? "" : "Err#";

    /* print optional fields */
    OPT_printid  ? printf("%5d/0x%x:  ",pid,tid) : 1;
    OPT_relative ? printf("%8d ",vtimestamp/1000) : 1;
    OPT_elapsed  ? printf("%7d ",this->elapsed/1000) : 1;
    OPT_cpu      ? printf("%6d ",this->cpu/1000) : 1;
    
    /* print main data */
    printf("%s(0x%X, 0x%X, 0x%X)\t\t = %d %s%d",probefunc,self->arg0,self->arg1,self->arg2,(int)arg0,self->code,(int)errno);
    if(self->arg1==0x4004746a){
        /* TIOCMGET */
        tracemem(copyin(self->arg2,4),4);
    }else if(self->arg1==0x8004746d){
        /* TIOCMSET */
        tracemem(copyin(self->arg2,4),4);
    }else if(self->arg1==0x40487413){
        /* TIOCGETA */
        tracemem(copyin(self->arg2,64),64);
    }else if(self->arg1==0x80487414){
        /* TIOCSETA */
        tracemem(copyin(self->arg2,64),64);
    }
    printf("\n");
    OPT_stack ? ustack()    : 1;
    OPT_stack ? trace("\n") : 1;
    self->arg0 = 0;
    self->arg1 = 0;
    self->arg2 = 0;
}

/* print 3 arg output - default */
syscall:::return
/self->start/
{
    /* calculate elapsed time */
    this->elapsed = timestamp - self->start;
    self->start = 0;
    this->cpu = vtimestamp - self->vstart;
    self->vstart = 0;
    self->code = errno == 0 ? "" : "Err#";

    /* print optional fields */
    OPT_printid  ? printf("%5d/0x%x:  ",pid,tid) : 1;
    OPT_relative ? printf("%8d ",vtimestamp/1000) : 1;
    OPT_elapsed  ? printf("%7d ",this->elapsed/1000) : 1;
    OPT_cpu      ? printf("%6d ",this->cpu/1000) : 1;

    /* print main data */
    printf("%s(0x%X, 0x%X, 0x%X)\t\t = %d %s%d\n",probefunc,self->arg0,
           self->arg1,self->arg2,(int)arg0,self->code,(int)errno);
    OPT_stack ? ustack()    : 1;
    OPT_stack ? trace("\n") : 1;
    self->arg0 = 0;
    self->arg1 = 0;
    self->arg2 = 0;
}

/* print counts */
dtrace:::END
{
    OPT_counts == 1 ? printf("\n%-32s %16s\n","CALL","COUNT") : 1;
    OPT_counts == 1 ? printa("%-32s %@16d\n",@Counts) : 1;
}
