#!/usr/bin/python
import re,sys,os,os.path

file_re=re.compile(r'^(?P<indent>\s*)\.file\s+(?P<num>[0-9]+)\s+"(?P<file_name>[^"]*)"')
loc_re=re.compile(r'^(?P<indent>\s*)\.loc\s+(?P<num>[0-9]+)\s+(?P<line>[0-9]+)\s+(?P<col>[0-9]+)')
asciz_re=re.compile(r'^\s*\.asciz\s+"(?P<str>[^"]*)"')

lines=[line.rstrip() for line in sys.stdin.readlines()]

# find path (this is just a big dirty hack)
path=""
ascizs=[]
for line in lines:
    m=asciz_re.match(line)
    if m is not None:
        ascizs.append(m.group("str"))

for i in range(len(ascizs)):
    if ascizs[i].lower().startswith("apple clang"):
        if i+2<len(ascizs):
            path=ascizs[i+2]
            break
        
files={}

for line in lines:
    line=line.rstrip()
    m=file_re.match(line)

    extra=[]

    if m is not None:
        num=int(m.group("num"))
        assert not files.has_key(num)

        file_name=m.group("file_name")
        if not os.path.isabs(file_name):
            file_name=os.path.normpath(os.path.join(path,
                                                    file_name))
            
        f=open(file_name,
               "rt")
        
        files[num]=(file_name,
                    [line.rstrip() for line in f.readlines()])
        
        f.close()
        del f

        #print "%d: %s (%d lines)"%(num,m.group("file_name"),len(files[num]))
    else:
        m=loc_re.match(line)
        if m is not None:
            file_num=int(m.group("num"))
            line_num=int(m.group("line"))
            col_num=int(m.group("col"))

            if files.has_key(file_num):
                if line_num>=1 and line_num<=len(files[file_num][1]):
                    extra.append("")
                    extra.append("%s:%d: %s"%(os.path.basename(files[file_num][0]),
                                              line_num,
                                              files[file_num][1][line_num-1].lstrip()))
                    extra.append("")

            line=None

    if line is not None:
        print line

    for e in extra:
        print "%s; %s"%(m.group("indent"),e)
