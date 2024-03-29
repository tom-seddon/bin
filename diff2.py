import argparse,sys,os,os.path,subprocess,fnmatch
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
            all_fnames.append(os.path.relpath(os.path.join(dname,fname),
                                              root))
            # v('   %s\n'%all_fnames[-1])

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
    global g_verbose
    g_verbose=options.verbose

    if not options.adds and not options.edits and not options.dels and not options.same:
        options.adds=True
        options.edits=True
        options.dels=True
        options.same=False

    if options.bare:
        if int(options.adds)+int(options.edits)+int(options.dels)+int(options.same)!=1:
            print("FATAL: when using -b, must specify only one of -a/-d/-e/-s.",file=sys.stderr)
            sys.exit(1)

    if options.diff and not options.edits:
        print("WARNING: --diff is a bit pointless when not showing edits.",file=sys.stderr)
    
    fs_a=find_files(options.a)
    fs_a.sort()
    
    fs_b=find_files(options.b)
    fs_b.sort()

    set_a=set([get_normpath(x) for x in fs_a])
    set_b=set([get_normpath(x) for x in fs_b])

    if options.adds or options.edits or options.same:
        for f_a in fs_a:
            if get_normpath(f_a) in set_b:
                if options.edits or options.same:
                    # compare
                    f_a_full=get_full_fname(options.a,f_a)
                    f_b_full=get_full_fname(options.b,f_a)
                    same=are_files_same(f_a_full,f_b_full)
                    if same:
                        if options.same:
                            print_file(options,"same",options.b,f_a)
                    else:
                        if options.edits:
                            print_file(options,"edit",options.b,f_a)

                            if options.diff:
                                if len(options.diff_pattern)==0: diff=True
                                else:
                                    diff=False
                                    for diff_pattern in options.diff_pattern:
                                        if fnmatch.fnmatch(f_a_full,diff_pattern):
                                            print('%s matches %s'%(f_a_full,diff_pattern))
                                            diff=True
                                            break

                                if diff: result=subprocess.call(["diff.exe","-u",f_a_full,f_b_full])
                        
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

    parser.add_argument("-s",
                        dest="same",
                        action="store_true",
                        help="if specified, show unchanged files")

    parser.add_argument("--diff",
                        action="store_true",
                        help="if specified, do a diff of any edits")

    parser.add_argument("--diff-pattern",
                        default=[],
                        action="append",
                        metavar="PATTERN",
                        help="when doing --diff, only diff files matching glob pattern %(metavar)s")

    parser.add_argument("-v",
                        "--verbose",
                        action="store_true",
                        help="if specified, verbosity")

    result=parser.parse_args(sys.argv[1:])
    main(result)
