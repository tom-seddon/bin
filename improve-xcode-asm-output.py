#!/usr/bin/python
import re,sys,os,os.path

ignore_re=re.compile(r'^(Ltmp|Lfunc_|LPC|\s*(#|@|\.cfi_|\.align|\.code|\.thumb_func))')
section_re=re.compile(r'^\s*\.section\s+(?P<attrs>.*)$')
file2_re=re.compile(r'^(?P<indent>\s*)\.file\s+(?P<num>[0-9]+)\s+"(?P<base_name>[^"]*)"\s+"(?P<file_name>[^"]*)"')
file1_re=re.compile(r'^(?P<indent>\s*)\.file\s+(?P<num>[0-9]+)\s+"(?P<file_name>[^"]*)"')
loc_re=re.compile(r'^(?P<indent>\s*)\.loc\s+(?P<num>[0-9]+)\s+(?P<line>[0-9]+)\s+(?P<col>[0-9]+)')

##########################################################################
##########################################################################
    
g_files={}

##########################################################################
##########################################################################

def add_file(num,base_name,file_name):
    assert not g_files.has_key(num)

    if file_name=='<stdin>':
        # ???
        lines=[]
    else:
        if not os.path.isabs(file_name) and base_name is not None:
            file_name=os.path.normpath(os.path.join(base_name, file_name))

        with open(file_name,'rt') as f:
            lines=(file_name,[ln.rstrip() for ln in f.readlines()])
        
    g_files[num]=lines
    print "%d: %s (%d lines)"%(num,file_name,len(g_files[num]))

##########################################################################
##########################################################################

def main():
    curSourceLine = None
    inCodeSection = False
    
    for line in sys.stdin.readlines():
        line=line.rstrip()

        extra=[]

        if ignore_re.match(line) is not None:
            # Ignore comments, noise labels, and unimportant directives
            continue

        # Watch ".section" directives and skip sections that don't contain instructions:
        m=section_re.match(line)
        if m is not None:
            attrs = m.group("attrs").split(",")
            inCodeSection = attrs[0] == "__TEXT" and attrs[1] == "__text"
            continue
        if not inCodeSection:
            continue

        m=file2_re.match(line)
        if m is not None:
            add_file(int(m.group("num")),m.group("base_name"),m.group("file_name"))
            continue

        m=file1_re.match(line)
        if m is not None:
            add_file(int(m.group("num")),None,m.group("file_name"))
            continue

        m=loc_re.match(line)
        if m is not None:
            # Display a source line:
            file_num=int(m.group("num"))
            line_num=int(m.group("line"))
            col_num=int(m.group("col"))

            if curSourceLine != (file_num, line_num):
                curSourceLine = (file_num, line_num)
                if g_files.has_key(file_num):
                    if line_num>=1 and line_num<=len(g_files[file_num][1]):
                        extra.append("")
                        extra.append("%-60s//%s:%d"%(g_files[file_num][1][line_num-1].lstrip(),
                                                     os.path.basename(g_files[file_num][0]),
                                                     line_num))
                        extra.append("")
                        line=None

        if line is not None:
            print line

        for e in extra:
            print "%s; %s"%(m.group("indent"),e)

##########################################################################
##########################################################################

if __name__=='__main__': main()
