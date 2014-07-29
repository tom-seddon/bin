import sys,argparse,os,subprocess,fnmatch,re
emacs=os.getenv("EMACS") is not None

##########################################################################
##########################################################################

def get_p4_lines(args,stdin_data):
    process=subprocess.Popen(args=args,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    output=process.communicate(stdin_data)
    output=[x.strip() for x in output[0].splitlines()]
    return output

def main(options):
    files=[]
    
    if options.changelist==0:
        output=get_p4_lines(["p4.exe","info"],None)
        
        prefix="Client name: "
        client_name=None
        for line in output:
            if line.startswith(prefix):
                client_name=line[len(prefix):]
                break
                
        if client_name is None:
            print>>sys.stderr,"FATAL: couldn't find client name."
            sys.exit(1)

        output=get_p4_lines(["p4.exe","opened","-C",client_name],None)

        default_change_re=re.compile("^(?P<fname>.*)#[0-9]+ - edit default change .*$")
        for line in output:
            match=default_change_re.match(line)
            if match is not None:
                files.append(match.group("fname"))
    else:
        output=get_p4_lines(["p4.exe","describe",str(options.changelist)],None)

        try:
            index=output.index("Affected files ...")
        except IndexError:
            print>>sys.stderr,"FATAL: no files in given changelist."
            sys.exit(1)

        done=False
        while not done:
            index+=1
            if output[index].strip()!="":
                done=True

        ellipsis="... "

        done=False
        while index<len(output):
            file=output[index].strip()
            if file=="":
                break

            if file.startswith(ellipsis):
                file=file[len(ellipsis):]

            h=file.find("#")
            if h>=0:
                file=file[:h].strip()

            files.append(file)

            index+=1

    if options.patterns is not None:
        i=0
        while i<len(files):
            keep=False
            for pattern in options.patterns:
                if fnmatch.fnmatch(files[i],pattern):
                    keep=True
                    break

            if keep:
                i+=1
            else:
                del files[i]

    output_lines=get_p4_lines(["p4.exe","-e","-x","-","where"],"\n".join(files))

    localPath_prefix="... localPath "
    for output_line in output_lines:
        if output_line.startswith(localPath_prefix):
            print output_line[len(localPath_prefix):]

##########################################################################
##########################################################################
            
if __name__=="__main__":
    parser=argparse.ArgumentParser(description="print local paths of files in perforce changelist.")

    parser.add_argument("changelist",
                        type=int,
                        help="changelist to show.")

    parser.add_argument("-n",
                        "--name",
                        metavar="PATTERN",
                        dest="patterns",
                        action="append",
                        help=
                        """print files matching PATTERN. (If any
                        patterns specified, any file matching any
                        pattern will be printed. If no patterns
                        specified, all files will be printed.)

                        """)

    result=parser.parse_args(sys.argv[1:])
    main(result)
