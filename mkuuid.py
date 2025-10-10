#!/usr/bin/python3
import uuid,sys,argparse

##########################################################################
##########################################################################

def main2(options):
    for i in range(int(options.n)):
        #sys.stdout.write(str(pythoncom.CreateGuid()).translate(None,"{}"))
        u=uuid.uuid4()

        if options.bytes: print(','.join(['0x%02x'%x for x in u.bytes]))
        elif options.underscore: print(str(u).replace('-','_'))
        else: print(u)

##########################################################################
##########################################################################

def main(argv):
    parser=argparse.ArgumentParser()

    parser.add_argument("-n",
                        metavar="N",
                        default="1",
                        help="Number of UUIDs to generate. (Default: %(default)s)")

    parser.add_argument("-_",
                        action="store_true",
                        dest="underscore",
                        default=False,
                        help="use '_' to separate UUID parts rather than '-'.")

    parser.add_argument('--bytes',
                        action='store_true',
                        help='''print output as hex bytes, suitable for use in C and whatnot''')

    main2(parser.parse_args(argv))
        
##########################################################################
##########################################################################

if __name__=="__main__": main(sys.argv[1:])
