import sys,argparse

def count_lines(args,lines,f):
    for line in f.readlines():
        if args.strip:
            line=line.strip()
        elif line[-1]=='\n':
            line=line[:-1]

        if args.ignore_case:
            line=line.upper()

        lines[line]=lines.get(line,0)+1

def cmp_by_count(a,b):
    return cmp((a[1],a[0]),(b[1],b[0]))

def main(args):
    lines={}
    if len(args.input_files)==0:
        count_lines(args,lines,sys.stdin)
    else:
        for input_file in args.input_files:
            f=open(input_file,"rt")
            count_lines(args,lines,f)
            f.close()

    lines=sorted(lines.items(),cmp if args.by_line else cmp_by_count)

    for line,count in lines:
        print "%-5d: %s"%(count,line)

if __name__=="__main__":
    parser=argparse.ArgumentParser()

    parser.add_argument("-s",
                        "--strip",
                        action="store_true",
                        help="strip leading and trailing whitespace")

    parser.add_argument("-f",
                        "--ignore-case",
                        action="store_true",
                        help="fold lower case to upper case characters")

    parser.add_argument("-l",
                        "--by-line",
                        action="store_true",
                        help="sort output by line rather than by count")

    parser.add_argument("input_files",
                        metavar="INPUT-FILE",
                        nargs=argparse.REMAINDER)

    argv=sys.argv[1:]
    args=parser.parse_args(argv)
    main(args)
