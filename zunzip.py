#!/usr/bin/python3
import sys,os,os.path,zipfile,fnmatch,glob,argparse,collections,re

##########################################################################
##########################################################################

g_verbose=False

def pv(msg):
    if g_verbose: sys.stderr.write(msg)

##########################################################################
##########################################################################
    
def fatal(msg):
    sys.stderr.write('FATAL: %s\n'%msg)
    sys.exit(1)

##########################################################################
##########################################################################

def get_input_paths(options):
    input_paths=[]
    for input_path in options.input_paths: input_paths+=glob.glob(input_path)
    return input_paths
    
##########################################################################
##########################################################################

def get_normalized_path(path):
    path=os.path.normpath(path)
    
    path=os.path.normcase(path)
    
    # \\ is annoying when using regexps.
    path=path.replace('\\','/')
    
    return path

##########################################################################
##########################################################################

def l_cmd(options):
    input_paths=get_input_paths(options)
    for input_path in input_paths:
        with zipfile.ZipFile(input_path,'r') as zfile:
            zinfolist=zfile.infolist()
            
            for zinfo in zinfolist:
                line=''
            
                if options.long:
                    line+='%20s '%('{:,}'.format(zinfo.file_size))
                    #line+='%20s '%zinfo.file_size
                    
                if options.normalize: line+=get_normalized_path(zinfo.filename)
                else: line+=zinfo.filename
                
                print(line)
                
##########################################################################
##########################################################################

def x_cmd(options):
    input_paths=get_input_paths(options)
    
    output_root=options.output_folder or '.'
    
    exclude_regexps=[]
    for exclude_regexp_str in options.exclude_regexp_strs:
        exclude_regexps.append(re.compile(exclude_regexp_str))
    
    for input_path in input_paths:
        with zipfile.ZipFile(input_path,'r') as zfile:
            zinfolist=zfile.infolist()
            
            try:
                commonpath=os.path.commonpath([zinfo.filename for zinfo in zinfolist])
            except ValueError: commonpath=''
            
            if (len(zinfolist)>1 and len(commonpath)==0) or len(input_paths)>1:
                # not all files in a common folder, or extracting multiple zip files.
                # Make a folder for each one, named after the zip file.
                output_path=os.path.join(output_root,os.path.splitext(os.path.basename(input_path))[0])
            else:
                # single file, or everything in a common root
                output_path=output_root
                
            for zinfo in zinfolist:
                if zinfo.is_dir(): continue
                
                exclude=False
                if len(exclude_regexps)>0:
                    zinfo_filename=get_normalized_path(zinfo.filename)
                    for exclude_regexp in exclude_regexps:
                        if exclude_regexp.match(zinfo_filename):
                            exclude=True
                            break
                            
                sys.stdout.write('%s::%s -> '%(input_path,zinfo.filename))
                if exclude: sys.stdout.write('(excluded)\n')
                else:   
                    dest_path=os.path.join(output_path,zinfo.filename)
                
                    sys.stdout.write('%s (%s)\n'%(dest_path,'{:,}'.format(zinfo.file_size)))
                
                    dest_folder=os.path.split(dest_path)[0]
                    if not os.path.isdir(dest_folder): os.makedirs(dest_folder)
                    
                    with zfile.open(zinfo.filename) as f: data=f.read()
                    with open(dest_path,'wb') as f: f.write(data)
                        
                    del data
                            
                sys.stdout.flush()

##########################################################################
##########################################################################

def main(argv):
    parser=argparse.ArgumentParser()
    
    parser.add_argument('-v','--verbose',action='store_true',dest='g_verbose',help='''be more verbose''')
    parser.set_defaults(fun=None)
    
    subparsers=parser.add_subparsers()
    
    def add_subparser(fun,*args,**kwargs):
        subparser=subparsers.add_parser(*args,**kwargs)
        subparser.set_defaults(fun=fun)
        return subparser
    
    l_parser=add_subparser(l_cmd,'l',help='''list zip file contents''')
    l_parser.add_argument('-l','--long',action='store_true',help='''long output''')
    l_parser.add_argument('-n','--normalize',action='store_true',help='''normalize paths, showing the strings that x --exclude will match''')
    l_parser.add_argument('input_paths',metavar='FILE',nargs='+',help='''zip file(s)''')
    
    x_parser=add_subparser(x_cmd,'x',help='''extract zip file contents''')
    x_parser.add_argument('-o',dest='output_folder',metavar='FOLDER',default=None,help='''extract contents to given folder, or working folder if not specified''')
    x_parser.add_argument('-x','--exclude',metavar='REGEXP',action='append',dest='exclude_regexp_strs',default=[],help='''don't extract files with paths matching %(metavar)s (paths are normpath'd and normcase'd)''')
    x_parser.add_argument('input_paths',metavar='FILE',nargs='+',help='''zip file(s)''')
    
    options=parser.parse_args(argv)
    if options.fun is None:
        parser.print_help()
        sys.exit(1)
        
    global g_verbose
    g_verbose=options.g_verbose
        
    options.fun(options)
    
##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv[1:])
