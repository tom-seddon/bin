#!/usr/bin/python
# -*- mode:python -*-
import argparse,sys,os,os.path,hashlib,stat,fnmatch

g_verbose=False

##########################################################################
##########################################################################

def pv(str):
    global g_verbose

    if g_verbose:
        sys.stdout.write(str)

    # for size in sorted(filekeys_by_size.keys()):
    #     prefix="{:,}".format(size)+": "

    #     filekeys=filekeys_by_size[size]

    #     for i in range(len(filekeys)):
    #         files=files_by_filekey[filekeys[i]]

    #         pv(prefix if i==0 else " "*len(prefix))

    #         pv(str(files))
    #         pv("\n")

##########################################################################
##########################################################################

g_last_progress_msg=None

def print_progress(index,num_items,value,total):
    global g_last_progress_msg
    
    if sys.stdout.isatty():
        perc=int(value/float(total)*1000)
        msg="%d/%d: %03d.%d%%"%(index+1,num_items,perc/10,perc%10)

        if msg!=g_last_progress_msg:
            g_last_progress_msg=msg
            sys.stdout.write("\r"+g_last_progress_msg)
            sys.stdout.flush()

def main(options):
    global g_verbose

    g_verbose=options.verbose

    # map (st_dev,st_ino) to files
    files_by_filekey={}
    filekeys_by_size={}

    # retrieve everything
    for dir in options.dirs:
        for dir_path,dir_names,file_names in os.walk(dir):
            for i in range(len(dir_names)-1,-1,-1):
                if dir_names[i] in ["$RECYCLE.BIN",
                                    ".Trashes",
                                    ".Trash-1000",
                                    ".DS_Store",
                                    ".fseventsd"]:
                    del dir_names[i]
                    
            pv("    Looking in \"%s\"...\n"%dir_path)
            for file_name in file_names:
                keep=True

                for exclude in options.excludes:
                    if fnmatch.fnmatch(file_name,exclude):
                        keep=False
                        break

                if keep:
                    full_name=os.path.join(dir_path,file_name)

                    s=os.lstat(full_name)

                    if stat.S_ISLNK(s.st_mode):
                        pass
                    else:
                        filekey=(s.st_dev,s.st_ino)

                        files_by_filekey.setdefault(filekey,[]).append(full_name)
                        filekeys_by_size.setdefault(s.st_size,[]).append(filekey)

    # remove anything uninteresting...
    for size,filekeys in [item for item in filekeys_by_size.items()]:
        if len(filekeys)==1:
            del filekeys_by_size[size]
        elif size*len(filekeys)<options.min_size:
            #print size,len(filekeys)
            del filekeys_by_size[size]

    #sys.exit(1)

    sorted_sizes=sorted(filekeys_by_size.keys(),reverse=options.reverse_sort)
    
    for size_idx,size in enumerate(sorted_sizes):
        filekeys=filekeys_by_size[size]

        groups={}
        
        if len(filekeys)<500:
            fs=[]
            digests=[]
            for filekey in filekeys:
                fs.append(open(files_by_filekey[filekey][0],"rb"))
                digests.append(hashlib.md5())

            last_msg=""
            chunk_size=8192
            for offset in range(0,size,chunk_size):
                remaps={}
                for i in range(len(fs)):
                    if fs[i] is not None:
                        chunk=fs[i].read(chunk_size)
                        digests[i].update(chunk)
                        remaps.setdefault(chunk,[]).append(i)

                print_progress(size_idx,len(sorted_sizes),offset,size)

                if len(remaps)==0:
                    # no dups...
                    break

                for chunk,indexes in remaps.items():
                    if len(indexes)==1:
                        fs[indexes[0]].close()
                        fs[indexes[0]]=None

            sys.stdout.write("\r"+len(last_msg)*" "+"\r")

            for i in range(len(fs)):
                if fs[i] is not None:
                    groups.setdefault(digests[i].hexdigest(),[]).append(filekeys[i])

            for f in fs:
                if f is not None:
                    f.close()

            del fs
        else:
            nbytes_total=len(filekeys)*size
            nbytes_seen=0
            chunk_size=1048576

            for filekey in filekeys:
                with open(files_by_filekey[filekey][0],"rb") as f:
                    digest=hashlib.md5()

                    for offset in range(0,size,chunk_size):
                        chunk=f.read(chunk_size)
                        digest.update(chunk)
                        nbytes_seen+=len(chunk)

                        print_progress(size_idx,len(sorted_sizes),nbytes_seen,nbytes_total)

                    groups.setdefault(digest.hexdigest(),[]).append(filekey)

            for key,val in groups.items():
                if len(val)==1: del groups[key]
        
        if len(groups)>0:
            for hexdigest,filekeys in groups.items():
                lines=[hexdigest+": ",
                       "({:,})  ".format(size)]

                width=max([len(line) for line in lines])

                lines=[(width*" "+line)[-width:] for line in lines]

                for i in range(len(filekeys)):
                    sys.stdout.write(lines[i] if i<len(lines) else width*" ")
                    sys.stdout.write(files_by_filekey[filekeys[i]][0])
                    sys.stdout.write("\n")


##########################################################################
##########################################################################

if __name__=="__main__":
    parser=argparse.ArgumentParser(fromfile_prefix_chars="@",
                                   description="Find duplicate files.")

    parser.add_argument("-l",
                        "--less-than",
                        default=262144,
                        metavar="SIZE",
                        dest="min_size",
                        nargs=1,
                        help="""Ignore sets totalling less than %(metavar)s bytes. (Default %(metavar)s: %(default)d.)""")

    parser.add_argument("-r",
                        dest="reverse_sort",
                        default=False,
                        action="store_true",
                        help="""reverse sort order and look at largest files first""")

    parser.add_argument("-x",
                        dest="excludes",
                        action="append",
                        default=[],
                        metavar="PATTERN",
                        help="""ignore file(s) with name part matching %(metavar)s""")

    parser.add_argument("-v",
                        "--verbose",
                        action="store_true",
                        default=False,
                        help="""If specified, verbosity.""")

    parser.add_argument("dirs",
                        metavar="DIR",
                        nargs="+",
                        help="""read files from %(metavar)s.""")

    main(parser.parse_args())
    
