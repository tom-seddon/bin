#!env python
import sys,argparse,os,os.path,fnmatch
emacs=os.getenv("EMACS") is not None

##########################################################################
##########################################################################

g_verbose=False

def v(msg):
    if g_verbose:
        sys.stdout.write(msg)
        sys.stdout.flush()

def exit(x):
    if emacs: raise RuntimeError
    else: sys.exit(x)

def get_full_ext(ext):
    if len(ext)>0 and ext[0]!=".": return "."+ext
    else: return ext

def main(options):
    global g_verbose
    g_verbose=options.verbose

    old_ext_nrm=get_full_ext(os.path.normcase(options.old_ext))

    # Get full list of old files.
    v("Searching in ``%s''...\n"%options.dir)
    old_fnames=[]
    for dname,dnames,fnames in os.walk(options.dir):
        for fname in fnames:
            if os.path.normcase(os.path.splitext(fname)[1])==old_ext_nrm:
                old_fnames.append(os.path.join(dname,fname))

    v("    Found %d matching files\n"%len(old_fnames))

    # Decide on full list of new files. Check for existing files if
    # necessary.
    new_ext=get_full_ext(options.new_ext)
    bad=False
    new_fnames=[]
    for old_fname in old_fnames:
        new_fname=os.path.splitext(old_fname)[0]+new_ext
        new_fnames.append(new_fname)

        if not options.force:
            if os.path.exists(new_fname):
                print>>sys.stderr,"WARNING: File exists: %s"%new_fname
                bad=True

    if bad: exit(1)

    # Rename files.
    for i in range(len(old_fnames)):
        if g_verbose:
            v("RENAME: %s\n"%old_fname)
            v("    TO: %s\n"%new_fname)
            
        os.rename(old_fnames[i],new_fnames[i])

##########################################################################
##########################################################################

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="change file extensions en masse")

    parser.add_argument("-n","--dry-run",
                        action="store_true",
                        help="""Don't actually do anything""")
    
    parser.add_argument("-f",
                        "--force",
                        action="store_true",
                        help="""Rename even if the destination file exists""")

    parser.add_argument("-v",
                        dest="verbose",
                        action="store_true",
                        help="""Be more verbose""")

    parser.add_argument("-d","--dir",
                        metavar="DIR",
                        default=".",
                        help="""look in DIR. Default %(metavar)s: %(default)s""")

    parser.add_argument("old_ext",
                        metavar="OLD-EXT",
                        help="""extension to replace""")

    parser.add_argument("new_ext",
                        metavar="NEW-EXT",
                        help="""new extension""")

    options=parser.parse_args(sys.argv[1:])
    main(options)
