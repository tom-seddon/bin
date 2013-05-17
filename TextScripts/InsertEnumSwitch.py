#!/usr/bin/python
# -*- mode: python -*-
#XcodeMenuName: Insert enum switch
import sys,shlex

def next(l,expected=None):
    t=l.get_token()

    if t==l.eof or (expected is not None and t not in expected):
        print>>sys.stderr,"Syntax error \"%s\"; expecting %s"%(t,expected)
        sys.exit(1)
        
    return t

raw=sys.stdin.read()
    
l=shlex.shlex(raw)

l.commenters+="/" # not QUITE right...

next(l,"enum")
enum_name=next(l)
if enum_name=="{":
    enum_name=None
else:
    next(l,"{")

value_names=[]

while 1:
    t=next(l)

    if t=="}":
        break

    value_names.append(t)

    sep=next(l,["}",
                ",",
                "="])
    if sep==",":
        # ok, next one.
        pass
    elif sep=="}":
        # ok, done.
        break
    if sep=="=":
        # doesn't handle expressions!
        while next(l)!=",":
            pass

next(l,";")

sys.stdout.write(raw[:l.instream.tell()])
sys.stdout.write("\n\n")
sys.stdout.flush()

print "switch()"
print "{"
print "default:"
print "break;"
for value_name in value_names:
    print
    print "case %s:"%value_name
    print "{"
    print "}"
    print "break;"

print "}"
