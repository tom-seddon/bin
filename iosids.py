#!/usr/bin/python
# -*- mode: python -*-

# iosids
# ======
#
# Tool to stop you going insane when trying to bulk add people from
# Test Flight. No more "this device already exists" from the
# provisioning portal, forcing you to very carefully cross reference
# the two lists.
#
# How to use:
#
# 1. Ask Test Flight to export device IDs list for your team
# members. You'll get a file called something like
# ``testflight_devices.txt'' in your downloads folder.
#
# 2. Visit the iOS Provisioning Portal, Devices section. Use File>Save
# As to save the page in Page Source format (i.e., an HTML file).
#
# 3. Run this script, supplying name of HTML file and devices txt. The
# output is all device identifiers and device names that are mentioned
# in the Test Flight devices list, but not in the provisioning
# portal. Redirect the output to a .txt file, since you'll need it in
# the next step:
#
#     iosids /tmp/Devices\ -\ iOS\ Provisioning\ Portal\ -\ Apple\ Developer.html ~/Downloads/testflight_devices.txt > /tmp/devices.txt
#
# 4. Use the Upload Devices button in the Provisioning Portal to bulk
# add the new devices. Point it at the text file created in step 3.

import argparse,HTMLParser

class StoreIDsHTMLParser(HTMLParser.HTMLParser):
    def __init__(self,
                 ids):
        HTMLParser.HTMLParser.__init__(self)

        self._await_id=False
        self._ids=ids
        
    def handle_starttag(self,
                        tag,
                        attrs):
        self._await_id=tag=="td" and dict(attrs).get("class")=="id"

    def handle_endtag(self,
                      tag):
        self._await_id=False

    def handle_data(self,
                    data):
        if self._await_id:
            self._ids.add(data.strip().lower())
            self._await_id=False
            
def main(options):
    got_ids=set()
    add_ids={}
    
    f=open(options.html,
           "rt")
    StoreIDsHTMLParser(got_ids).feed(f.read())
    f.close()
    del f

    f=open(options.ids,
           "rt")
    lines=f.readlines()
    f.close()
    del f
    
    for i in range(1,
                   len(lines)):
        parts=lines[i].split("\t")
        if len(parts)!=2:
            print>>sys.stderr,"FATAL: %s:%d: syntax error."%(options.ids,
                                                             i)
            sys.exit(1)

        add_ids[parts[0].strip().lower()]=parts[1].rstrip()

    print "deviceIdentifier\tdeviceName"
    
    for k,v in add_ids.items():
        if k not in got_ids:
            print "%s\t%s"%(k,
                            v)

if __name__=="__main__":
    parser=argparse.ArgumentParser(fromfile_prefix_chars="@")

    parser.add_argument("html",
                        metavar="HTML")
    parser.add_argument("ids",
                        metavar="IDS")

    main(parser.parse_args())
                       
    
