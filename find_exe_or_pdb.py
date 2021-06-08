#!/usr/bin/python
import sys,os,os.path,argparse,fnmatch,stat
import pdb_info
import pe_header

##########################################################################
##########################################################################

g_verbose=False

def pv(x):
    if g_verbose:
        sys.stdout.write(x)
        sys.stdout.flush()

##########################################################################
##########################################################################

def main2(options):
    global g_verbose
    g_verbose=options.verbose
    # pdb_info.set_verbose(options.verbose)
    
    if options.timestamp is None:
        print>>sys.stderr,'FATAL: must specify something to search by'
        sys.exit(1)
    
    def check_pdb(path):
        try:
            st=os.stat(path)
            if st.st_size==0: return False
            header=pdb_info.get_pdb_header(path)
            pv('%08x : %s\n'%(header.Signature,path))
            return header.Signature==options.timestamp
        except pdb_info.PDBError,e: print>>sys.stderr,'WARNING: %s: %s'%(e.pdb_path,e.pdb_message)
        except Error,e: print>>sys.stderr,'WARNING: %s: %s'%(path,e.message)
        return False
    
    def check_exe(path):
        timestamp=pe_header.get_pe_timestamp(path)
        pv('%08x : %s\n'%(timestamp,path))
        return timestamp==options.timestamp
    
    for path in options.paths:
        for dirpath,dirnames,filenames in os.walk(path):
            for filename in filenames:
                ext=os.path.splitext(os.path.normcase(filename))[1]
                if ext=='.exe': pred=check_exe
                elif ext=='.pdb': pred=check_pdb
                else: pred=None

                if pred is not None:
                    # pv('%s\n'%path)
                    path=os.path.join(dirpath,filename)
                    if pred(path): print path

##########################################################################
##########################################################################
                
def auto_int(x): return int(x,0)

def main(argv):
    parser=argparse.ArgumentParser()

    parser.add_argument('-v','--verbose',action='store_true',help='be more verbose')
    parser.add_argument('-t','--timestamp',metavar='TIMESTAMP',type=auto_int,help='search by timestamp')

    parser.add_argument('paths',nargs='+',metavar='FOLDER',help='look for EXEs/PDBs in %(metavar)s')

    main2(parser.parse_args(argv))

if __name__=='__main__': main(sys.argv[1:])
