#!/usr/bin/python3
#XcodeMenuName: Insert separator
import sys,os

ext=os.getenv('Extension') or ''
if ext.lower()==".cs":
    sys.stdout.write("//########################################################################\n")
else:
    sys.stdout.write("//////////////////////////////////////////////////////////////////////////\n")

if os.getenv("windir") is not None:
    # workaround for stupid .NET annoyance... must fix this better.
    sys.stdout.write("\n")
