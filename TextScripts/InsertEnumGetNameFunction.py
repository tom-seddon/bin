#!/usr/bin/python
# -*- mode: python -*-
#XcodeMenuName: Insert enum GetName function
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

x=next(l,["enum","typedef"])
if x=="typedef":
    x=next(l,"enum")

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
                "=",
                ";"])
    if sep==",":
        # ok, next one.
        pass
    elif sep=="}" or sep==";":
        # ok, done.
        break
    if sep=="=":
        # doesn't handle expressions!
        while next(l) not in [",","}"]:
            pass

#next(l,";")
            
sys.stdout.write(raw[:l.instream.tell()])
sys.stdout.write("\n\n")
sys.stdout.flush()

print "static const char *Get%sName(int value)"%enum_name
print "{"
print "    switch(value)"
print "    {"
print "    S_DEFAULT_NAME_CASE(%s,value)"%enum_name
for value_name in value_names:
    if not value_name.lower().endswith("endvalue"):
        print "    S_NAME_CASE(%s)"%value_name
print "    }"
print "}"

