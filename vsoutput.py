import argparse,sys,re,collections,fnmatch

##########################################################################
##########################################################################

def vsoutput(options):
    with open(options.path,'rt') as f: lines=f.readlines()

    prefix_re=re.compile(r'''^(?P<number>[0-9]+)>(?P<rest>.*)$''')
    project_re=re.compile(r'''^-+ .*: Project: (?P<project>.*), Configuration: (?P<configuration>.*) -+$''')

    Project=collections.namedtuple('Project','project configuration')

    lines_by_number={}
    for line in lines:
        m=prefix_re.match(line)
        if m is None: number=0
        else:
            number=int(m.group('number'))
            line=m.group('rest')

        if number not in lines_by_number: lines_by_number[number]=[]
        lines_by_number[number].append(line)

    project_by_number={}
    for number,lines in lines_by_number.items():
        if number is None: continue

        m=None
        for line in lines:
            m=project_re.match(line)
            if m is not None: break

        if m is not None:
            assert number not in project_by_number
            project_by_number[number]=Project(project=m.group('project'),
                                              configuration=m.group('configuration'))
            
    if options.list_projects:
        for number in sorted(lines_by_number.keys()):
            if number==0: pass
            elif number in project_by_number:
                project=project_by_number[number]
                print('%d: Project: %s; Configuration: %s'%
                      (number,
                       project.project,
                       project.configuration))
            else: print('%d: unknown'%number)

    if len(options.prints)>0:
        good=True
        numbers=[]
        for s in options.prints:
            if s.isdigit():
                # project number
                number=int(s)
            else:
                # glob pattern
                number=None
                pattern=s.lower()
                for k,v in project_by_number.items():
                    if fnmatch.fnmatch(v.project.lower(),pattern):
                        number=k
                        break

            if number not in lines_by_number:
                print('FATAL: unknown project: %s'%s,file=sys.stderr)
                sys.exit(1)

            numbers.append(number)

        for number_idx,number in enumerate(numbers):
            if len(numbers)>1: prefix='%d>'%(1+number_idx)
            else: prefix=''
            
            for line in lines: print('%s%s'%(prefix,line))
    

##########################################################################
##########################################################################

def main(argv):
    parser=argparse.ArgumentParser()#help='examine Visual Studio build output')

    parser.add_argument('path',metavar='FILE',help='''read VS build output from %(metavar)s''')
    parser.add_argument('-l','--list-projects',action='store_true',help='''list projects in build output''')
    parser.add_argument('-p','--print',metavar='PROJECT',action='append',dest='prints',default=[],help='''print output for %(metavar)s (number, or glob pattern matching project name)''')

    vsoutput(parser.parse_args(argv))

##########################################################################
##########################################################################
    
if __name__=='__main__': main(sys.argv[1:])
