from __future__ import print_function
import sys,argparse,os,subprocess,fnmatch,re,stat,collections,json
emacs=os.getenv("EMACS") is not None

##########################################################################
##########################################################################

# regarding charset, so far "handled" very poorly, see
# https://www.perforce.com/perforce/doc.current/user/i18nnotes.txt

g_verbose=False

##########################################################################
##########################################################################

def get_argv(argv): return [x for x in argv if x is not None]

def get_p4_lines(args,stdin_data):
    process=subprocess.Popen(args=get_argv(args),
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    outputs=process.communicate(stdin_data)

    outputs=[output.decode('utf8').splitlines() for output in outputs]

    if g_verbose:
        sep=80*'-'
        print(sep,file=sys.stderr)
        print('Command: %s'%args,file=sys.stderr)
        print('Exit code: %s'%process.returncode)

        def dump_output(name,index):
            print('%d line(s) of %s'%(len(outputs[index]),name),file=sys.stderr)
            for line in outputs[index]: print('    %s'%line)
        
        dump_output('stdout',0)
        dump_output('stderr',1)
        print(sep,file=sys.stderr)

    return outputs

##########################################################################
##########################################################################

def get_p4_json(args,stdin_data):
    args=['p4.exe','-Mj','-ztag']+get_argv(args)
    process=subprocess.Popen(args=args,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    outputs=process.communicate(stdin_data)
    outputs=[output.decode('utf8').splitlines() for output in outputs]

    if g_verbose:
        sep=80*'-'
        print(sep,file=sys.stderr)
        print('Command: %s'%args,file=sys.stderr)
        print('Exit code: %s'%process.returncode)

        def dump_output(name,index):
            print('%d line(s) of %s'%(len(outputs[index]),name),file=sys.stderr)
            for line in outputs[index]: print('    %s'%line)

    if process.returncode!=0:
        print('Command: %s'%args,file=sys.stderr)
        print('Command failed with exit code: %d',file=sys.stderr)
        sys.exit(1)

    js=[]
    for line in outputs[0]: js.append(json.loads(line))

    return js

##########################################################################
##########################################################################

class ChangelistFile:
    def __init__(self,depot_path,ftype):
        assert depot_path is not None
        self._depot_path=depot_path
        self.local_path=None
        self.diff=None
        self.diff_error=None
        self.ftype=ftype
        self.fmods=None
        self.p4_file=None

    @property
    def depot_path(self): return self._depot_path

    @property
    def type(self):
        result=self.ftype or '*unknown*'
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

def fill_cl_file_diffs(cl_files,options):
    for cl_file in cl_files:
        if cl_file.diff is not None:
            # Might encounter the same ChangelistFile multiple times,
            # because of the way the lists are built up.
            # 
            # TODO: should really fix this.
            continue
        
        diff_output,diff_error_output=get_p4_lines(['p4.exe',
                                                    'diff',
                             '-du%d'%options.num_diff_context_lines,
                             cl_file.depot_path],None)
        if len(diff_error_output)>0:
            cl_file.diff_error=diff_error_output
        else:
            assert diff_output[0].startswith('--- ')
            assert diff_output[1].startswith('+++ ')

            cl_file.diff=diff_output[2:]

##########################################################################
##########################################################################

g_client_name=None

def get_client_name():
    global g_client_name
    
    if g_client_name is None:
        p4_info_js=get_p4_json(['info'],None)
        g_client_name=p4_info_js[0].get('clientName')
        
        if g_client_name is None:
            print("FATAL: couldn't find client name.",file=sys.stderr)
            sys.exit(1)

    return g_client_name

##########################################################################
##########################################################################

def get_changes_changelists(state,options):
    js=get_p4_json(['changes','-s',state,'-c',get_client_name()],None)

    changelists=set()
    for j in js: changelists.add(int(j.get('change')))

    return changelists

##########################################################################
##########################################################################

def get_cl_files_for_default_changelist(options):
    cl_files=[]
    
    p4_opened_js=get_p4_json(['opened','-C',get_client_name()],None)
    for p4_opened_j in p4_opened_js:
        if p4_opened_j.get('action')=='edit' and p4_opened_j.get('change')=='default':
            depot_path=p4_opened_j.get('depotFile')
            ftype=p4_opened_j.get('type')

            cl_files.append(ChangelistFile(depot_path,ftype))

    remove_unwanted_files(cl_files,options)

    # This is rather inefficient, but since I typically use a p4
    # proxy, it's not a huge problem.
    #
    # The output of p4 -ztag -Mj is a bit easier to work with, but
    # I had a few instances of diffs with random junk at the end.
    if options.diffs: fill_cl_file_diffs(cl_files,options)

    return cl_files

##########################################################################
##########################################################################

def get_cl_file_by_depot_path(cl_files):
    cl_file_by_depot_path={}
    for cl_file in cl_files: cl_file_by_depot_path[cl_file.depot_path]=cl_file
    
    return cl_file_by_depot_path

##########################################################################
##########################################################################

def get_cl_files_for_changelist(changelist,quiet,options):
    output,error_output=get_p4_lines(["p4.exe",
                                      "describe",
                                      '-S' if options.shelved else None,
                                      '-du%d'%options.num_diff_context_lines,
                                      str(changelist)],None)

    if len(output)==0:
        print('\n'.join(error_output),file=sys.stderr)
        print('FATAL: failed to get details for changelist: %d'%changelist,file=sys.stderr)
        sys.exit(1)

    # for k,v in enumerate(output): print('%d: %s'%(k,v))

    is_pending_changelist=output[0].endswith('*pending*')

    # Affected files...
    try:
        if options.shelved: header='Shelved files ...'
        else: header='Affected files ...'
        index=output.index(header)
        index+=2
    except ValueError:
        if quiet: return []
        print("FATAL: no files in changelist: %d"%changelist,file=sys.stderr)
        sys.exit(1)

    while index<len(output):
        if output[index].strip()!="": break
        index+=1

    # if index==len(output):
    #     if quiet: return []
    #     print("FATAL: no files in given changelist.",file=sys.stderr)
    #     sys.exit(1)

    ellipsis="... "

    cl_files=[]
    done=False
    while index<len(output) and output[index].startswith(ellipsis):
        depot_path=output[index][len(ellipsis):].strip()

        h=depot_path.find("#")
        if h>=0: depot_path=depot_path[:h].strip()

        #print('add (%d): %s'%(changelist,depot_path))
        cl_files.append(ChangelistFile(depot_path,None))

        index+=1

    remove_unwanted_files(cl_files,options)

    # Differences...
    if options.diffs:
        if is_pending_changelist and not options.shelved: fill_cl_file_diffs(cl_files,options)
        else:
            try: index=output.index('Differences ...')+2
            except ValueError: index=None

            if index is not None:
                cl_file_by_depot_path=get_cl_file_by_depot_path(cl_files)
                
                diff_header_re=re.compile('^==== (?P<depot_path>.*)#(?P<revision>[0-9]+)\\s+\\((?P<ftype>.*)(\\+(?P<fmods>.*))?\\) ====$')

                while index<len(output):
                    match=diff_header_re.match(output[index])
                    assert match is not None,(index,output[index])

                    depot_path=match.group('depot_path')

                    # file may not exist, if remove_unwanted_files
                    # stripped it out
                    file=cl_file_by_depot_path.get(depot_path)

                    if file is not None:
                        file.ftype=match.group('ftype')
                        file.fmods=match.group('fmods')

                    index+=1    # skip header
                    index+=1    # skip separating blank line

                    begin=index
                    while index<len(output) and len(output[index])>0: index+=1

                    end=index
                    index+=1    # skip terminating blank line

                    if file is not None:
                        if file.ftype=='text': file.diff=output[begin:end]

    return cl_files

##########################################################################
##########################################################################

def main(options):
    global g_verbose
    g_verbose=options.verbose
    
    # TODO...
    # os.putenv('P4CHARSET','utf8')

    # form list of unique changelists specified.
    changelists=set()
    for changelist in options.changelists:
        if changelist=='w':
            changelists.add(0)  # default changelist
            changelists.update(get_changes_changelists('pending',options))
            changelists.update(get_changes_changelists('shelved',options))
        else:
            try: changelists.add(int(changelist))
            except:
                print('FATAL: bad changelist number: %s'%changelist,file=sys.stderr)
                sys.exit(1)

    if options.shelved:
        if len(changelists)==1 and 0 in changelists:
            print('FATAL: default changelist not compatible with -S/--shelved',file=sys.stderr)
            sys.exit(1)
        else: changelists.remove(0)

    quiet_errors=len(changelists)>1

    cl_files=[]
    for changelist in changelists:
        if changelist==0: cl_files+=get_cl_files_for_default_changelist(options)
        else: cl_files+=get_cl_files_for_changelist(changelist,len(changelists)>1,options)

    cl_file_by_depot_path=get_cl_file_by_depot_path(cl_files)

    files_list="\n".join([depot_path for depot_path in sorted(cl_file_by_depot_path.keys())])
    where_output,where_error_output=get_p4_lines(["p4.exe","-e","-x","-","where"],files_list.encode())
    where_result=parse_where_output(where_output)

    for p4_file in where_result:
        cl_file=cl_file_by_depot_path[p4_file.depotFile]
        cl_file.p4_file=p4_file

    if options.diffs:
        diff_flags=[False,True]
        if options.emacs: print('# -*- mode:diff -*-')
    else: diff_flags=[None]

    num_files=0
    
    for diff_flag in diff_flags:
        for depot_path in sorted(cl_file_by_depot_path.keys()):
            cl_file=cl_file_by_depot_path[depot_path]

            if diff_flag is None: show=True
            else: show=diff_flag==(cl_file.diff is not None)

            if show:
                if cl_file.p4_file is None: print('???????'+cl_file.depot_path)
                elif options.depot: print(cl_file.p4_file.depotFile)
                else: print(cl_file.p4_file.localPath)

                if options.diffs:
                    if cl_file.diff_error is not None:
                        print()
                        for line in cl_file.diff_error: print(line)
                        print()
                    elif cl_file.diff is None:
                        print()
                        print('(No diff for file of type: %s)'%cl_file.type)
                        print()
                    else:
                        print()
                        for line in cl_file.diff: print(line)
                        print()

    if options.stats:
        total_size=0
        for cl_file in cl_file_by_depot_path.values():
            try:
                st=os.stat(cl_file.p4_file.localPath)
                total_size+=st.st_size
            except: print('WARNING: failed to stat: %s'%cl_file.p4_file.localPath,file=sys.stderr)

    if options.stats: print('{:,} byte(s) in {:,} matching file(s)'.format(total_size,len(cl_file_by_depot_path)))

##########################################################################
##########################################################################
            
if __name__=="__main__":
    parser=argparse.ArgumentParser(description="print local paths of files in perforce changelist.")

    parser.add_argument('-v','--verbose',action='store_true',help='''be more verbose''')

    parser.add_argument("changelists",
                        default=[],
                        nargs='+',
                        help="changelist(s) to show. 0 means default changelist, 'w' means default/pending/shelved changelist(s) in current workspace. When multiple changelists specified, some errors will be ignored")

    parser.add_argument('-d',
                        '--diffs',
                        action='store_true',
                        help='''show unified diffs. Undiffables printed first. Files are diffed against source revision''')

    parser.add_argument('-e',
                        '--emacs',
                        action='store_true',
                        help='''when diffing, be Emacs-friendly. Add a file local variable indicating diff mode''')

    parser.add_argument('-c',
                        '--context',
                        metavar='N',
                        dest='num_diff_context_lines',
                        type=int,
                        default=3,
                        help='''set number of diff context lines. Default: %(default)d''')

    parser.add_argument('-s',
                        '--stats',
                        action='store_true',
                        help='''print summary statistics''')

    parser.add_argument('-S',
                        '--shelved',
                        action='store_true',
                        help='''work with files shelved in changelist (not valid with default changelist)''')

    parser.add_argument('-D',
                        '--depot',
                        action='store_true',
                        help='''print depot path rather than local path''')

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
