#!/usr/bin/python
# -*- python-mode -*-
import uuid

output=str(uuid.uuid4())
output=output.replace("-","")
value=int(output,16)

chars="1234567890PYFGCRLAOEUIDHTNSQJKXBMWVZpyfgcrlaoeuidhtnsqjkxbmwvz_-"

passwd=""

num_bits_left=32*4
while num_bits_left>0:
    passwd+=chars[value&63]
    
    value>>=6
    num_bits_left-=6

print passwd

