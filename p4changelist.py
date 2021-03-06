import sys,argparse,os,subprocess,fnmatch,re,stat,collections
emacs=os.getenv("EMACS") is not None

##########################################################################
##########################################################################

def get_p4_lines(args,stdin_data):
    process=subprocess.Popen(args=args,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    output=process.communicate(stdin_data)
    return output[0].splitlines()

##########################################################################
##########################################################################

class ChangelistFile:
    def __init__(self,depot_path):
        assert depot_path is not None
        self._depot_path=depot_path
        self.local_path=None
        self.diff=None
        self.ftype=None
        self.fmods=None
        self.perforce_file=None

    @property
    def depot_path(self): return self._depot_path

    @property
    def type(self):
        result=self.ftype
        if self.fmods is not None: result+='+'+self.fmods
        return result

##########################################################################
##########################################################################

PerforceFile=collections.namedtuple('PerforceFile',
                                    'depotFile clientFile localPath')

def parse_where_output(lines):
    depotFile_prefix='... depotFile '
    clientFile_prefix='... clientFile '
    localPath_prefix='... localPath '
    info_prefix='info: '
    exit_prefix='exit: '

    files=[]
    
    index=0
    while index<len(lines):
        line=lines[index]
        index+=1
        
        if line.startswith(exit_prefix): break

        if line.startswith(info_prefix):
            index+=1            # skip info: xxx
            depotFile=None
            clientFile=None
            localPath=None
            while index<len(lines) and len(lines[index])>0:
                line=lines[index]
                index+=1
                
                if line.startswith(depotFile_prefix): depotFile=line[len(depotFile_prefix):]
                elif line.startswith(clientFile_prefix): clientFile=line[len(clientFile_prefix):]
                elif line.startswith(localPath_prefix): localPath=line[len(localPath_prefix):]

            files.append(PerforceFile(depotFile=depotFile,
                                      clientFile=clientFile,
                                      localPath=localPath))

    return files

##########################################################################
##########################################################################

def remove_unwanted_files(changelist_files_by_depot_path,options):
    if options.patterns is not None:
        i=0
        for depot_path,file in changelist_files_by_depot_path.items():
            keep=False
            for pattern in options.patterns:
                if fnmatch.fnmatch(file.depot_path,pattern):
                    keep=True
                    break

            if not keep: del changelist_files_by_depot_path[depot_path]

##########################################################################
##########################################################################

def main(options):
    changelist_files_by_depot_path={}
    
    if options.changelist==0:
        output=get_p4_lines(["p4.exe","info"],None)
        
        prefix="Client name: "
        client_name=None
        for line in output:
            if line.startswith(prefix):
                client_name=line[len(prefix):]
                break
                
        if client_name is None:
            print>>sys.stderr,"FATAL: couldn't find client name."
            sys.exit(1)

        output=get_p4_lines(["p4.exe","opened","-C",client_name],None)

        default_change_re=re.compile("^(?P<depot_path>.*)#[0-9]+ - edit default change .*$")
        for line in output:
            match=default_change_re.match(line)
            if match is not None:
                depot_path=match.group('depot_path')
                assert depot_path not in changelist_files_by_depot_path
                changelist_files_by_depot_path[depot_path]=ChangelistFile(depot_path)
                continue

        remove_unwanted_files(changelist_files_by_depot_path,options)

        # This is rather inefficient, but since I typically use a p4
        # proxy, it's not a huge problem.
        if options.diffs:
            for cl_file in changelist_files_by_depot_path.values():
                diff_output=get_p4_lines(['p4.exe','diff','-du',cl_file.depot_path],None)
                assert diff_output[0].startswith('--- ')
                assert diff_output[1].startswith('+++ ')

                cl_file.diff=diff_output[2:]
    else:
        output=get_p4_lines(["p4.exe","describe",'-du',str(options.changelist)],None)

        # for k,v in enumerate(output): print '%d: %s'%(k,v)

        # Affected files...
        try: index=output.index("Affected files ...")
        except IndexError:
            print>>sys.stderr,"FATAL: no files in given changelist."
            sys.exit(1)

        while True:
            index+=1
            if output[index].strip()!="": break

        ellipsis="... "

        done=False
        while index<len(output):
            depot_path=output[index].strip()
            if depot_path=="": break

            if depot_path.startswith(ellipsis): depot_path=depot_path[len(ellipsis):]

            h=depot_path.find("#")
            if h>=0: depot_path=depot_path[:h].strip()

            changelist_files_by_depot_path[depot_path]=ChangelistFile(depot_path)

            index+=1

        # Differences...
        if options.diffs:
            try:
                index=output.index('Differences ...')+2
            except IndexError: index=None

            if index is not None:
                diff_header_re=re.compile('^==== (?P<depot_path>.*)#(?P<revision>[0-9]+)\\s+\\((?P<ftype>.*)(\\+(?P<fmods>.*))?\\) ====$')

                while index<len(output):
                    match=diff_header_re.match(output[index])
                    assert match is not None,(index,output[index])

                    depot_path=match.group('depot_path')
                    assert depot_path in changelist_files_by_depot_path
                    file=changelist_files_by_depot_path[depot_path]
                    
                    file.ftype=match.group('ftype')
                    file.fmods=match.group('fmods')

                    index+=1    # skip header
                    index+=1    # skip separating blank line
                    
                    begin=index
                    while index<len(output) and len(output[index])>0: index+=1

                    end=index
                    index+=1    # skip terminating blank line

                    if file.ftype!='text': continue

                    file.diff=output[begin:end]

        # Remove anything undesirable.
        remove_unwanted_files(changelist_files_by_depot_path,options)

    where_output=get_p4_lines(["p4.exe","-e","-x","-","where"],"\n".join([depot_path for depot_path in sorted(changelist_files_by_depot_path.keys())]))
    where_result=parse_where_output(where_output)

    for p4_file in where_result:
        cl_file=changelist_files_by_depot_path[p4_file.depotFile]
        cl_file.p4_file=p4_file

    if options.diffs: diff_flags=[False,True]
    else: diff_flags=[None]

    num_files=0
    
    for diff_flag in diff_flags:
        for depot_path in sorted(changelist_files_by_depot_path.keys()):
            cl_file=changelist_files_by_depot_path[depot_path]

            if diff_flag is None: show=True
            else: show=diff_flag==(cl_file.diff is not None)

            if show:
                print cl_file.p4_file.localPath

                if options.diffs:
                    if cl_file.diff is None:
                        print
                        print '(No diff for file of type: %s)'%cl_file.type
                        print
                    else:
                        print
                        for line in cl_file.diff: print line
                        print

    if options.stats:
        total_size=0
        for cl_file in changelist_files_by_depot_path.values():
            try:
                st=os.stat(cl_file.p4_file.localPath)
                total_size+=st.st_size
            except: print>>sys.stderr,'WARNING: failed to stat: %s'%cl_file.p4_file.localPath

    if options.stats: print '{:,} byte(s) in {:,} matching file(s)'.format(total_size,len(changelist_files_by_depot_path))
            
                
    #     print_files(changelist_files_by_depot_path,False)
    #     print_files(changelist_files_by_depot_path,True)
    # else: print_files(changelist_files_by_depot_path,None)


    # def print_files(show_diffs):
    # num_=0
    # num_files=0
    # for file in where_result:
    #     cl_file=changelist_files_by_depot_path[file.depotFile]
        
    #     if options.diffs and not options.all_diffs:
    #         if cl_file.diff is None:
    #             num_undiffable+=1
    #             continue
            
    #     if options.stats:
    #         try:g
    #             st=os.stat(file.localPath)
    #             total_size+=st.st_size
    #         except: 

    #     print file.localPath
    #     num_files+=1

    #     if options.diffs:



##########################################################################
##########################################################################
            
if __name__=="__main__":
    parser=argparse.ArgumentParser(description="print local paths of files in perforce changelist.")

    parser.add_argument("changelist",
                        type=int,
                        help="changelist to show.")

    parser.add_argument('-d',
                        '--diffs',
                        action='store_true',
                        help='''show unified diffs (undiffables printed first)''')

    parser.add_argument('-s',
                        '--stats',
                        action='store_true',
                        help='''print summary statistics''')

    parser.add_argument("-n",
                        "--name",
                        metavar="PATTERN",
                        dest="patterns",
                        action="append",
                        help=
                        """print files matching PATTERN. (If any
                        patterns specified, any file matching any
                        pattern will be printed. If no patterns
                        specified, all files will be printed.)

                        """)

    result=parser.parse_args(sys.argv[1:])
    main(result)
