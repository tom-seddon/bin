import sys,argparse,os,unittest,stat
emacs=os.getenv("EMACS") is not None

def main(options):
    with open(options.file,"rb") as f:
        data=f.read()

    data=list(data)

    if options.ascii:
        any_changed=False
        for i in xrange(len(data)):
            c=ord(data[i])

            if c>=33 and c<127:
                c-=33
                c+=47
                c%=94
                c+=33

                any_changed=True

            data[i]=chr(c)

        if not any_changed:
            print>>sys.stderr,"WARNING: the file didn't actually change."
            
    else:
        for i in xrange(len(data)):
            data[i]=chr(ord(data[i])^255)

    data="".join(data)

    if not os.access(options.file,os.W_OK):
        os.chmod(options.file,stat.S_IWRITE)

    with open(options.file,"wb") as f:
        f.write(data)

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="modify a file so that p4 reconcile will spot that it has changed.")

    parser.add_argument("file",
                        help="the file to modify")

    parser.add_argument("-a",
                        "--ascii",
                        default=False,
                        action="store_true",
                        help="if specified, assume file is text")

    parser.add_argument("-f",
                        "--force",
                        action="store_true",
                        help="if specified, modify even read-only files")

    args=sys.argv[1:]
    result=parser.parse_args(args)
    main(result)
