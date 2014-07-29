import argparse,sys,os,os.path,subprocess
emacs=os.getenv("EMACS") is not None

##########################################################################
##########################################################################

g_verbose=False

def v(x):
    global g_verbose
    
    if g_verbose:
        sys.stdout.write(x)
        sys.stdout.flush()

##########################################################################
##########################################################################

def find_files(root):
    all_fnames=[]

    v("Scanning `%s'...\n"%root)
    
    for dname,dnames,fnames in os.walk(root):
        for fname in fnames:
            #full_fname=os.path.normpath(os.path.join(dname,fname))
            all_fnames.append(fname)

    return all_fnames

##########################################################################
##########################################################################

def get_full_fname(root,name):
    return os.path.join(root,name)

##########################################################################
##########################################################################

def get_normpath(x):
    return os.path.normpath(os.path.normcase(x))

##########################################################################
##########################################################################

def print_file(options,change_type,root,name):
    if not options.bare:
        sys.stdout.write(change_type)
        sys.stdout.write(": ")

    sys.stdout.write(get_full_fname(root,name))
    sys.stdout.write("\n")

    sys.stdout.flush()

##########################################################################
##########################################################################

def are_files_same(a,b):
    size_a=os.path.getsize(a)
    size_b=os.path.getsize(b)

    if size_a!=size_b:
        return False

    with open(a,"rb") as fa:
        with open(b,"rb") as fb:
            data_a=fa.read()
            data_b=fb.read()

            if data_a!=data_b:
                return False

    return True

##########################################################################
##########################################################################

def main(options):
    g_verbose=options.verbose

    if not options.adds and not options.edits and not options.dels:
        options.adds=True
        options.edits=True
        options.dels=True

    if options.bare:
        if int(options.adds)+int(options.edits)+int(options.dels)!=1:
            print>>sys.stderr,"FATAL: when using -b, must specify only one of -a/-d/-e."
            sys.exit(1)

    if options.diff and not options.edits:
        print>>sys.stderr,"WARNING: --diff is a bit pointless when not showing edits."
    
    fs_a=find_files(options.a)
    fs_a.sort()
    
    fs_b=find_files(options.b)
    fs_b.sort()

    set_a=set([get_normpath(x) for x in fs_a])
    set_b=set([get_normpath(x) for x in fs_b])

    if options.adds or options.edits:
        for f_a in fs_a:
            if get_normpath(f_a) in set_b:
                if options.edits:
                    # compare
                    f_a_full=get_full_fname(options.a,f_a)
                    f_b_full=get_full_fname(options.b,f_a)
                    if not are_files_same(f_a_full,f_b_full):
                        print_file(options,"edit",options.b,f_a)

                        if options.diff:
                            result=subprocess.call(["diff.exe","-u",f_a_full,f_b_full])
                        
            else:
                # deleted
                if options.dels:
                    print_file(options,"del ",options.a,f_a)

    if options.adds:
        for f_b in fs_b:
            if get_normpath(f_b) not in set_a:
                # added
                print_file(options,"add ",options.b,f_b)

##########################################################################
##########################################################################

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="find differences between folders.")

    parser.add_argument("a",
                        metavar="OLD",
                        help="old folder")

    parser.add_argument("b",
                        metavar="NEW",
                        help="new folder")
    
    parser.add_argument("-b",
                        dest="bare",
                        action="store_true",
                        default=False,
                        help="if specified, bare output")

    parser.add_argument("-a",
                        dest="adds",
                        action="store_true",
                        help="if specified, show adds")
    
    parser.add_argument("-d",
                        dest="dels",
                        action="store_true",
                        help="if specified, show deletes")
    
    parser.add_argument("-e",
                        dest="edits",
                        action="store_true",
                        help="if specified, show edits")

    parser.add_argument("--diff",
                        action="store_true",
                        help="if specified, do a diff of any edits")

    parser.add_argument("-v",
                        "--verbose",
                        action="store_true",
                        help="if specified, verbosity")

    result=parser.parse_args(sys.argv[1:])
    main(result)
