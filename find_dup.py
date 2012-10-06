#!/usr/bin/python
# -*- mode:python -*-
import argparse,sys,os,os.path,hashlib,stat

g_verbose=False

##########################################################################
##########################################################################

def v(str):
    global g_verbose

    if g_verbose:
        sys.stdout.write(str)

    # for size in sorted(filekeys_by_size.keys()):
    #     prefix="{:,}".format(size)+": "

    #     filekeys=filekeys_by_size[size]

    #     for i in range(len(filekeys)):
    #         files=files_by_filekey[filekeys[i]]

    #         v(prefix if i==0 else " "*len(prefix))

    #         v(str(files))
    #         v("\n")

##########################################################################
##########################################################################
        
def main(options):
    global g_verbose

    g_verbose=options.verbose

    # map (st_dev,st_ino) to files
    files_by_filekey={}
    filekeys_by_size={}

    # retrieve everything
    for dir_path,dir_names,file_names in os.walk(options.dir):
        v("    Looking in \"%s\"...\n"%dir_path)
        for file_name in file_names:
            full_name=os.path.join(dir_path,file_name)

            s=os.lstat(full_name)

            if stat.S_ISLNK(s.st_mode):
                pass
            else:
                filekey=(s.st_dev,s.st_ino)

                files_by_filekey.setdefault(filekey,[]).append(full_name)
                filekeys_by_size.setdefault(s.st_size,[]).append(filekey)

    # remove anything uninteresting...
    for size,filekeys in filekeys_by_size.items():
        if len(filekeys)==1:
            del filekeys_by_size[size]
        elif size*len(filekeys)<options.min_size:
            #print size,len(filekeys)
            del filekeys_by_size[size]

    #sys.exit(1)

    sorted_sizes=sorted(filekeys_by_size.keys())
    for size_idx in range(len(sorted_sizes)):
        size=sorted_sizes[size_idx]
        filekeys=filekeys_by_size[size]
        
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

            if sys.stdout.isatty():
                perc=int(offset/float(size)*1000)
                msg="%d/%d; %03d.%d%%"%(size_idx+1,len(sorted_sizes),perc/10,perc%10)

                if msg!=last_msg:
                    last_msg=msg
                    sys.stdout.write("\r"+last_msg)
                    sys.stdout.flush()

            if len(remaps)==0:
                # no dups...
                break

            for chunk,indexes in remaps.items():
                if len(indexes)==1:
                    fs[indexes[0]].close()
                    fs[indexes[0]]=None

        sys.stdout.write("\r"+len(last_msg)*" "+"\r")

        groups={}
        for i in range(len(fs)):
            if fs[i] is not None:
                groups.setdefault(digests[i].hexdigest(),[]).append(filekeys[i])

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
            
        for f in fs:
            if f is not None:
                f.close()

        del fs

##########################################################################
##########################################################################

if __name__=="__main__":
    parser=argparse.ArgumentParser(fromfile_prefix_chars="@",
                                   description="Find duplicate files.")

    parser.add_argument("-d",
                        "--dir",
                        default=".",
                        metavar="DIR",
                        help="""Read files from %(metavar)s. (Default %(metavar)s: \"%(default)s\".)""")

    parser.add_argument("-l",
                        "--less-than",
                        default=262144,
                        metavar="SIZE",
                        dest="min_size",
                        nargs=1,
                        help="""Ignore sets totalling less than %(metavar)s bytes. (Default %(metavar)s: %(default)d.)""")

    parser.add_argument("-v",
                        "--verbose",
                        action="store_true",
                        default=False,
                        help="""If specified, verbosity.""")

    main(parser.parse_args())
    
