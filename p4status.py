import sys,argparse,os,subprocess,fnmatch,win32api,win32file,marshal,tempfile
emacs=os.getenv("EMACS") is not None

##########################################################################
##########################################################################

g_verbose=False

def v(msg):
    if g_verbose:
        sys.stdout.write(msg)
        sys.stdout.flush()

##########################################################################
##########################################################################

def print_file_names(options,prefix,fnames):
    for fname in sorted(fnames,
                        lambda x,y:cmp(x.lower(),y.lower())):
        if not options.bare:
            sys.stdout.write(prefix)
            sys.stdout.write(" ")
        sys.stdout.write(fname)
        sys.stdout.write("\n")

##########################################################################
##########################################################################

def add_files_in_folder(files,folder,clear_flags):
    datas=win32api.FindFiles(os.path.join(folder,"*"))
    for data in datas:
        if (data[0]&win32file.FILE_ATTRIBUTE_DIRECTORY)==0:
            if (data[0]&clear_flags)==0:
                files.add(os.path.join(folder,data[8]))

    for data in datas:
        if data[0]&win32file.FILE_ATTRIBUTE_DIRECTORY:
            if data[8]!="." and data[8]!="..":
                add_files_in_folder(files,os.path.join(folder,data[8]),clear_flags)

##########################################################################
##########################################################################
                
def run_p4_and_get_all_lines(p4_args,files):
    process=subprocess.Popen(args=p4_args,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    output=process.communicate("\n".join(files))
    return output[0].splitlines()
    
def run_p4_and_get_prefixed_lines(p4_args,files,prefix):
    all_lines=run_p4_and_get_all_lines(p4_args,files)

    result=set()
    for line in all_lines:
        if line.startswith(prefix):
            result.add(line[len(prefix):].strip())
            
    return result

##########################################################################
##########################################################################

def main(options):
    global g_verbose
    g_verbose=options.verbose
    
    if not hasattr(options,"added"):
        options.added=False
        
    if options.folders==None:
        options.folders=["."]

    if options.bare and (not options.added)!=(options.edited or options.deleted):
        sys.stderr.write("FATAL: bare mode can only be used with edited/deleted OR added.\n")
        sys.exit(1)

    adds=set()
    if options.added:
        v("finding files...\n")
        all_files=set()
        for folder in options.folders:
            add_files_in_folder(all_files,folder,0)

        v("    (found %d files.)\n"%len(all_files))

        v("getting depot adds...\n")
        depot_adds=run_p4_and_get_prefixed_lines(["p4.exe","-x","-","-e","reconcile","-a","-n"],all_files,"... depotFile ")

        v("getting local paths...\n")
        adds=run_p4_and_get_prefixed_lines(["p4.exe","-x","-","-e","where"],depot_adds,"... localPath ")

    edits=set()
    if options.edited:
        rw_files=set()
        for folder in options.folders:
            add_files_in_folder(rw_files,folder,win32file.FILE_ATTRIBUTE_READONLY)

        edits=run_p4_and_get_all_lines(["p4.exe","-x","-","diff","-se"],rw_files)

    deletes=set()
    if options.deleted:
        deletes=run_p4_and_get_all_lines(["p4.exe","-x","-","diff","-sd"],[os.path.join(folder,"...") for folder in options.folders])

    print_file_names(options,"add",adds)
    print_file_names(options,"edit",edits)
    print_file_names(options,"delete",deletes)

##########################################################################
##########################################################################

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="print perforce files modified locally.")

    parser.add_argument("folders",
                        action="append",
                        metavar="FOLDER",
                        help=
                        """folder to look in.""")

    parser.add_argument("-a",
                        "--added",
                        action="store_true",
                        help="""if specified, show files that were added.""")

    parser.add_argument("-e",
                        "--edited",
                        action="store_true",
                        help=
                        """if specified, show files that were edited.""")

    parser.add_argument("-d",
                        "--deleted",
                        action="store_true",
                        help=
                        """if specified, show files that were deleted.""")

    parser.add_argument("-b",
                        "--bare",
                        action="store_true",
                        help=
                        """if specified, just print file names,
                        without any additional information (for use
                        with, e.g., ``p4 -x - sync -f'').

                        """)

    parser.add_argument("-v",
                        "--verbose",
                        default=False,
                        action="store_true",
                        help=
                        """if specified, be more verbose.""")

    result=parser.parse_args(sys.argv[1:])
    main(result)
