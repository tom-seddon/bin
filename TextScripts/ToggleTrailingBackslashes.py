#!/usr/bin/python
#XcodeMenuName: Toggle trailing \
import sys

lines=[line.rstrip() for line in sys.stdin.readlines()]
    
add_bs=True
for line in lines:
    if line.endswith("\\"):
        add_bs=False
        break

if add_bs:
    tab_width=4#@TODO...

    widths=[]

    for line in lines:
        width=0
        for c in line:
            if c=='\t':
                width=(width+tab_width)/tab_width*tab_width
            else:
                width+=1

        widths.append(width)

    max_width=max(widths)

    for i in range(len(lines)-1):
        for j in range(widths[i],
                       max_width+1):
            lines[i]+=" "

        lines[i]+="\\"
        
else:
    for i in range(len(lines)):
        while lines[i].endswith("\\"):
            lines[i]=lines[i][:-1]

        lines[i]=lines[i].rstrip()
    
for line in lines:
    print line
    
