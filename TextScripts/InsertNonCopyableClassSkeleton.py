#!/usr/bin/python
#XcodeMenuName: Insert non-copyable class skeleton
import sys

done_sel=False

w=sys.stdout.write

any=False
for line in sys.stdin.readlines():
    if any:
        print
        
    line=line.strip().split()

    if len(line)>=1:
        w("class "+line[0])

        if len(line)>=2:
            w(":")

        w("\n")

        if len(line)>=2:
            w("public "+line[1]+"\n")

        w("{\n")
        w("public:\n")
        w("protected:\n")
        w("private:\n")
        w("\t%s(const %s &);\n"%(line[0],line[0]))
        w("\t%s &operator=(const %s &);\n"%(line[0],line[0]))
        w("};\n")
          
    any=True
    
