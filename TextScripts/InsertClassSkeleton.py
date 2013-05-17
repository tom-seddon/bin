#!/usr/bin/python
#XcodeMenuName: Insert class skeleton
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

        w("{\npublic:\nprotected:\nprivate:\n};\n")
          
    any=True
    
