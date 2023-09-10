#!/usr/bin/python3
import os,os.path,sys,stat,glob,optparse,re

##########################################################################
#
# tma - Time Machine analysis
# ---------------------------
#
# Tom Seddon - tma@tomseddon.plus.com
#
##########################################################################
#
# Run from your Time Machine backups folder - the one with the dated
# folders in it. (e.g., on my Mac, which is called tmbp, this is
# ``/Volumes/Time Machine Backups/Backups.backupdb/tmbp/''.)
#
# There are various options - see the -h output. But generally you'll
# probably use tma to find out why the last Time Machine backup was
# larger than expected. For that, visit the backups folder, and use
# this:
#
#     tma -wum
#
# This shows you the difference between the two most recent backups,
# and a list of the 5 largest new folders in the most recent backup.
#
##########################################################################
#
# TODO
# ----
#
# - Most of the options have turned out to be a bit pointless...
#
##########################################################################

emacs=1
try:
    import emacs
except:
    emacs=0

##########################################################################

NUM_WORST=5
SIZE_WIDTH=10
    
##########################################################################
    
def listdir(options,
            path):
    try:
        return os.listdir(path)
    except OSError as e:
        if not options.Q:
            sys.stderr.write("%s: %s\n"%(path,str(e)))
            
        return None

def du_h(n):
    # approximate du --h display...

    if n<1024:
        # Bytes
        return "%d"%n
    elif n<1024*1024:
        # K
        return "%.1fK"%(n/1024.0)
    elif n<1024*1024*1024:
        # M
        return "%.1fM"%(n/1024.0/1024.0)
    else:
        # G
        return "%.1fG"%(n/1024.0/1024.0/1024.0)

def walk_error(e):
    sys.stderr.write("%s: %s\n"%(e.filename,str(e)))
    
def display(options,
            flag,
            prefix,
            full,
            st,
            suffix,
            worst):
    if not flag:
        return

    isdir=stat.S_ISDIR(st.st_mode)

    pretty_full=full
    if isdir:
        pretty_full+="/"
    
    if options.du and sys.stdout.isatty():
        sys.stdout.write(SIZE_WIDTH*" ")
        sys.stdout.write(prefix)
        sys.stdout.write(pretty_full)
        sys.stdout.write("\r")

    if options.du:
        size=0
        
        if isdir:
            num_files=0
            last_msg_len=0
            for path,dirs,files in os.walk(full,
                                           True,
                                           walk_error):
                for f in files:
                    st=os.lstat(os.path.join(path,f))
                    size+=st.st_size

                    num_files+=1
                    if num_files>1000:
                        num_files=0
                        if sys.stdout.isatty():
                            sys.stdout.write("\r")
                            sys.stdout.write(SIZE_WIDTH*" ")
                            sys.stdout.write("\r")
                            sys.stdout.write(du_h(size))
                            sys.stdout.flush()

            if sys.stdout.isatty():
                sys.stdout.write("\r")
                sys.stdout.write(SIZE_WIDTH*" ")
                sys.stdout.write("\r")
        else:
            size=st.st_size
            
        sys.stdout.write("%-*s"%(SIZE_WIDTH,
                                 du_h(size)))

        if worst is not None:
            for i in range(len(worst)):
                if worst[i] is None or size>worst[i][1]:
                    worst[i]=(pretty_full,
                              size)
                    break

    if not options.du or not sys.stdout.isatty():
        sys.stdout.write(prefix)
        sys.stdout.write(pretty_full)
        sys.stdout.write("\r")

    sys.stdout.write(suffix)
    
def tma_recurse(options,
                old_folder,
                new_folder,
                worst):
    olds=listdir(options,
                 os.path.join(options.root,
                              old_folder))
    news=listdir(options,
                 os.path.join(options.root,
                              new_folder))

    if olds is None or news is None:
        return
    
    olds=set(olds)

    folders=[]

    # Humm, should only do this once, really...
    if options.zero:
        add_prefix=""
        del_prefix=""
        chg_prefix=""
        suffix=chr(0)
    else:
        add_prefix="ADD   : "
        del_prefix="DELETE: "
        chg_prefix="CHANGE: "
        suffix="\n"

    for new in news:
        new_full=os.path.join(new_folder,
                              new)
        try:
            new_st=os.lstat(os.path.join(options.root,
                                         new_full))
        except: new_st=None
        
        if not new in olds:
            display(options,
                    options.added,
                    add_prefix,
                    new_full,
                    new_st,
                    suffix,
                    worst)
        else:
            old_full=os.path.join(old_folder,
                                  new)
            old_st=os.lstat(os.path.join(options.root,
                                         old_full))

            olds.remove(new)

            if old_st.st_ino==new_st.st_ino:
                # Entry unchanged.
                pass
            else:
                # Entry changed
                if stat.S_ISDIR(new_st.st_mode):
                    # Don't print out the folder, just the changed
                    # files in it.
                    folders.append(new)
                elif stat.S_ISLNK(new_st.st_mode):
                    # Changes in symlinks aren't especially
                    # interesting. They (probably) just point to the
                    # same target, relatively speaking.
                    #
                    # Should really check, though...
                    pass
                else:
                    display(options,
                            options.changed,
                            chg_prefix,
                            new_full,
                            new_st,
                            suffix,
                            worst)
                        
    for old in olds:
        old_full=os.path.join(old_folder,
                              old)
        old_st=os.lstat(os.path.join(options.root,
                                     old_full))

        display(options,
                options.deleted,
                del_prefix,
                old_full,
                old_st,
                suffix,
                None)

    del olds
    del news

    for folder in folders:
        tma_recurse(options,
                    os.path.join(old_folder,
                                 folder),
                    os.path.join(new_folder,
                                 folder),
                    worst)
    
##########################################################################

def main(argv):
    parser=optparse.OptionParser("%prog [options] OLD-BACKUP NEW-BACKUP")
    parser.add_option("-m",
                      "--most_recent",
                      action="store_true",
                      default=False,
                      help="if specified, compare two most recent backups.")
    parser.add_option("-r",
                      "--root",
                      metavar="FOLDER",
                      help="specify root folder of Time Machine backups, if not `.'.",
                      default=".")
    parser.add_option("-a",
                      "--added",
                      action="store_true",
                      default=False,
                      help="if specified, show added files.")
    parser.add_option("-d",
                      "--deleted",
                      action="store_true",
                      default=False,
                      help="if specified, show deleted files.")
    parser.add_option("-c",
                      "--changed",
                      action="store_true",
                      default=False,
                      help="if specified, show changed files.")
    parser.add_option("-0",
                      action="store_true",
                      default=False,
                      dest="zero",
                      help="if specified, output in a form suitable for xargs -0. (-ac recommended.)")
    parser.add_option("-Q",
                      action="store_true",
                      default=False,
                      help="if specified, be quiet stderr.")
    parser.add_option("-u",
                      "--du",
                      action="store_true",
                      default=False,
                      help="if specified, print disk usage for each item. (Ignored if -0.)")
    parser.add_option("-w",
                      "--worst",
                      action="store_true",
                      default=False,
                      help="Specify along with --du to print top %d worst offenders, space-wise."%NUM_WORST)
    
    options,args=parser.parse_args(argv[1:])
    if not options.most_recent:
        if len(args)!=2:
            parser.print_help()
            sys.stderr.write("FATAL: Must specify 2 backups.\n")
            sys.exit(1)

        a=args[0]
        b=args[1]
    else:
        backup_re=re.compile("[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{6}")

        backups=[]
        for name in os.listdir(options.root):
            if backup_re.match(name):
                backups.append(name)
        
        if len(backups)<2:
            sys.stderr.write("FATAL: Too few backups for --most-recent.\n")
            sys.exit(1)

        # lexicographical sort is fine due to the naming.
        backups.sort()

        a=backups[-2]
        b=backups[-1]

    if not (options.added or
            options.changed or
            options.deleted):
        options.added=True
        options.changed=True
        options.deleted=True

    if options.zero:
        options.du=False

    worst=None
    if options.worst:
        worst=[None]*NUM_WORST
        
    tma_recurse(options,
                a,
                b,
                worst)

    if worst is not None:
        def compare_worst(a,b):
            if a is None:
                if b is None:
                    return 0
                else:
                    return -1
            elif b is None:
                return 1
            else:
                return b[1]-a[1]
            
        worst.sort(compare_worst)

        for w in worst:
            if w is not None:
                print("%-*s%s"%(SIZE_WIDTH,
                                du_h(w[1]),
                                w[0]))

if emacs:
    main(["",
          "--root=/Volumes/Time Machine Backups/Backups.backupdb/tmbp",
          "-m"])
else:
    main(sys.argv)
    
