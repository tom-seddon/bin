#!/usr/bin/python
#XcodeMenuName: Insert separator
import sys,os

sys.stdout.write("//////////////////////////////////////////////////////////////////////////\n")

if os.getenv("windir") is not None:
    # workaround for stupid .NET annoyance... must fix this better.
    sys.stdout.write("\n")

    
