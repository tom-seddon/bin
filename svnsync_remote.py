#!/usr/bin/python
import argparse,os,os.path,sys,stat,subprocess,pipes

def fatal(str):
    sys.stderr.write("FATAL: %s"%str)
    if str[-1]!='\n': sys.stderr.write("\n")

    if os.getenv("EMACS") is not None: raise RuntimeError
    else: sys.exit(1)

def run(argv):
    print 80*"-"
    print " ".join([pipes.quote(x) for x in argv])
    print 80*"-"

    ret=subprocess.call(argv)

    if ret!=0: fatal("process failed")

def main(options):
    dest=os.path.abspath(options.output_folder)
    
    if not os.path.isdir(dest): os.makedirs(dest)

    run(["svnadmin","create",dest])

    pre_revprop_change_fname=os.path.join(dest,"hooks/pre-revprop-change")
    with open(pre_revprop_change_fname,"wt") as f: f.write("#!/bin/sh\n")
    run(["chmod","+x",pre_revprop_change_fname])

    run(["svnsync","init","--quiet","file:///%s"%dest,options.url])
    
    run(["svnsync","sync","file:///%s"%dest])

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="do svnsync on a remote repo")

    parser.add_argument("-o",
                        dest="output_folder",
                        default=".",
                        metavar="DIR",
                        help="put repo in %(metavar)s (will be created if required). Default: %(default)s")

    parser.add_argument("url",
                        metavar="URL",
                        help="read remote svn repo from %(metavar)s")

    main(parser.parse_args(sys.argv[1:]))
    
