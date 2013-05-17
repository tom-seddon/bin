#!/usr/bin/python
#XcodeMenuName: Insert non-copyable class skeleton
import sys

any=False
for line in sys.stdin.readlines():
    if any:
        print

    line=line.strip()
    print "class %s"%line
    print "{"
    print "public:"
    print "protected:"
    print "private:"
    print "\t%s(const %s &);"%(line,line)
    print "\t%s &operator=(const %s &);"%(line,line)
    print "};"

    any=True
    
