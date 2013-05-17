#!/usr/bin/python
#XcodeMenuName: Insert struct and typedef
import sys

any=False

for line in sys.stdin.readlines():
    if any:
        print
        
    line=line.strip()

    print "struct %s"%line
    print "{"
    print "\t%%%{PBXSelection}%%%"
    print "};"
    print "typedef struct %s %s;"%(line,line)

    any=True
    
