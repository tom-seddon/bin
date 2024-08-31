#!/usr/bin/python32
import sys,os,os.path,subprocess,argparse,collections

##########################################################################
##########################################################################

g_verbose=False

def pv(msg):
    if g_verbose:
        sys.stdout.write(msg)
        sys.stdout.flush()

##########################################################################
##########################################################################
        
def fatal(x):
    sys.stderr.write('FATAL: %s\n'%x)
    sys.exit(1)

##########################################################################
##########################################################################

Branch=collections.namedtuple('Branch','hash category name')

##########################################################################
##########################################################################

def split_branch_name(branch_name):
    name_parts=branch_name.split('/')

    if len(name_parts)>1: return tuple(name_parts)
    else: return (None,branch_name)

def get_branches(categories=None):
    if categories is not None: categories=set(categories)
    
    lines=subprocess.check_output(['git','branch','--list','--format','%(objectname) %(refname:short)']).decode('utf-8').splitlines()

    branches=[]
    for line in lines:
        line_parts=line.split(None,1)

        name_parts=split_branch_name(line_parts[1])
        
        branch=Branch(hash=line_parts[0],
                      name=line_parts[1],
                      category=name_parts[0])

        if categories is not None:
            if branch.category not in categories:
                continue

        branches.append(branch)
        
    return branches

##########################################################################
##########################################################################

def list_branches_cmd(options):
    branches=get_branches(options.categories)
    for branch in branches: print(branch.name)

##########################################################################
##########################################################################

def list_categories_cmd(options):
    branches=get_branches()
    categories=set()
    for branch in branches:
        if branch.category is not None:
            categories.add(branch.category)
    for category in sorted(categories): print(category)

##########################################################################
##########################################################################

def find_by_merged_status_cmd(merged,options):
    branches=get_branches(options.categories)
    for branch in branches:
        if branch.name==options.branch: continue
        result=subprocess.run(['git','merge-base','--is-ancestor',branch.name,options.branch])
        # result is 0 if merged, 1 if unmerged
        if ((merged and result.returncode==0) or
            (not merged and result.returncode!=0)):
            print(branch.name)

##########################################################################
##########################################################################

def find_unmerged_cmd(options): find_by_merged_status_cmd(False,options)

##########################################################################
##########################################################################
        
def find_merged_cmd(options): find_by_merged_status_cmd(True,options)

##########################################################################
##########################################################################

def change_category_cmd(options):
    branches=get_branches()

    branches_by_name={}
    for branch in branches:
        assert branch.name not in branches_by_name
        branches_by_name[branch.name]=branch

    Change=collections.namedtuple('Change','old new')

    good=True
    changes=[]
    for old_branch_name in options.branch_names:
        category,rest=split_branch_name(old_branch_name)
        new_branch_name='%s/%s'%(options.new_category,rest)

        changes.append(Change(old=old_branch_name,
                              new=new_branch_name))

        if new_branch_name in branches_by_name:
            sys.stderr.write('FATAL: New branch name will already exist: %s\n'%new_branch_name)
            good=False
            
        branches_by_name[new_branch_name]=None
        
    if not good: fatal('Category change failed')

    for change in changes:
        subprocess.check_call(['git','branch','-m',change.old,change.new])
    
##########################################################################
##########################################################################

def main(argv):
    parser=argparse.ArgumentParser()

    parser.add_argument('-v','--verbose',dest='g_verbose',action='store_true',help='''be more verbose''')

    subparsers=parser.add_subparsers()

    def add_subparser(fun,name,**kwargs):
        subparser=subparsers.add_parser(name,**kwargs)
        subparser.set_defaults(fun=fun)
        return subparser

    def add_category_argument(parser): parser.add_argument('-c','--category',action='append',dest='categories',metavar='CATEGORY',help='''use branch(es) in category %(metavar)s''')
    
    list_branches_parser=add_subparser(list_branches_cmd,'list-branches',aliases=['lb'],help='''list branches''')
    add_category_argument(list_branches_parser)

    list_categories_parser=add_subparser(list_categories_cmd,'list-categories',aliases=['lc'],help='''list branch categories''')

    find_unmerged_parser=add_subparser(find_unmerged_cmd,'find-unmerged',aliases=['fu'],help='''find branches not merged int o a branch''')
    find_unmerged_parser.add_argument('branch',help='''show branches not merged into %(metavar)s''')
    add_category_argument(find_unmerged_parser)

    find_merged_parser=add_subparser(find_merged_cmd,'find-merged',aliases=['fm'],help='''find branches not merged int o a branch''')
    find_merged_parser.add_argument('branch',help='''show branches not merged into %(metavar)s''')
    add_category_argument(find_merged_parser)

    change_category_parser=add_subparser(change_category_cmd,'change-category',aliases=['cc'],help='''change the category part of branch name(s)''')
    change_category_parser.add_argument('new_category',metavar='CATEGORY',help='''change category to %(metavar)s''')
    change_category_parser.add_argument('branch_names',metavar='BRANCH',nargs='+',help='''change category of branch %(metavar)s''')

    options=parser.parse_args(argv[1:])
    if options.fun is None:
        parser.print_help()
        sys.exit(1)

    global g_verbose
    g_verbose=options.g_verbose

    options.fun(options)

if __name__=='__main__': main(sys.argv)
