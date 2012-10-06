#!/usr/bin/python
# -*- python-mode -*-
import argparse,sys,re,subprocess,os,os.path

##########################################################################
##########################################################################

g_verbose=False
g_very_verbose=False

##########################################################################
##########################################################################

def fatal(str):
    sys.stderr.write("FATAL: %s"%str)
    sys.exit(1)

##########################################################################
##########################################################################

def v(str):
    global g_verbose
    global g_very_verbose
    
    if g_verbose or g_very_verbose:
        sys.stderr.write(str)

##########################################################################
##########################################################################
        
def vv(str):
    global g_very_verbose
    
    if g_very_verbose:
        sys.stderr.write(str)

##########################################################################
##########################################################################

class Module:
    def __init__(self,
                 module_name,
                 begin,
                 end,
                 arch,
                 uid,
                 path):
        self.module_name=module_name
        if self.module_name.startswith("+"):
            self.module_name=self.module_name[1:]

        self.begin=begin
        self.end=end

        self.arch=arch

        self.uid=uid
        if self.uid[0].startswith("<"):
            self.uid=self.uid[1:]

        if self.uid.endswith(">"):
            self.uid=self.uid[:-1]

        self.path=path

        self.sympaths=set()

##########################################################################
##########################################################################

def symbolicate_crash_file(args,
                           file_name):
    modules_by_name={}

    #
    # load .crash file
    #
    f=open(file_name,
           "rt")
    crash_lines=[line.strip() for line in f.readlines()]
    f.close()
    del f

    #
    # get UIDs and stuff for each loaded module
    #
    try:
        binary_images_section=crash_lines[crash_lines.index("Binary Images:")+1:]
    except ValueError:
        fatal("Couldn't find Binary Images section.")

    for line in binary_images_section:
        parts=line.split(None,7)

        m=Module(parts[3],
                 int(parts[0],0),
                 int(parts[2],0),
                 parts[4],
                 parts[5],
                 parts[6])

        dsym_uuid="%s-%s-%s-%s-%s"%(m.uid[0:8],
                                    m.uid[8:12],
                                    m.uid[12:16],
                                    m.uid[16:20],
                                    m.uid[20:32])

        # using mdfind to search by the dsym UUID is useless... it
        # never finds anything (probably because I don't use Xcode
        # Archive).
        
        mdfind_cmd=["mdfind",
                    "-onlyin","/",
                    "-name","dsym"]
        dsyms=[x.strip() for x in subprocess.check_output(mdfind_cmd).splitlines()]

        vv("Searching for dSYMs for %s (%s)...\n"%(m.module_name,dsym_uuid))

        for dsym in dsyms:
            if not os.path.isdir(dsym):
                # could be .dSYM.zip or something
                continue

            if not os.path.isfile(os.path.join(dsym,
                                               "Contents/Resources/DWARF",
                                               m.module_name)):
                # certainly not for this module
                continue

            uuid_cmd=["dwarfdump",
                      "--uuid",dsym]
            uuids=[x.strip() for x in subprocess.check_output(uuid_cmd).splitlines()]

            #v("%s"%uuids)

            added=False

            for uuid in uuids:
                parts=uuid.split()

                if len(parts)>=2 and parts[0]=="UUID:" and parts[1].lower()==dsym_uuid.lower():
                    # looking positive...
                    m.sympaths.add(dsym)
                    added=True
                    break

            vv("    %s: %s\n"%("YES" if added else "No",
                               dsym))

        modules_by_name[m.module_name]=m

        if len(m.sympaths)>0:
            prefix="dSYMs for %s: "%m.module_name
            paths=list(m.sympaths)
            for i in range(len(paths)):
                v("%s%s\n"%(prefix if i==0 else len(prefix)*" ",
                            paths[i]))

    #
    # work through threads
    #
    result_lines=[]
    cur_thread=None
    printed_crash_header=False
    printed_thread_header=False
    for crash_line in crash_lines:
        parts=crash_line.split()

        if (len(parts)==3 and parts[0]=="Thread" and parts[1].isdigit() and parts[2]=="Crashed:"):
            cur_thread=crash_line
            printed_thread_header=False
        elif len(parts)==2 and parts[0]=="Thread" and parts[1].endswith(":") and parts[1][:-1].isdigit():
            cur_thread=crash_line
            printed_thread_header=False
        elif len(parts)==6 and parts[4]=="+" and parts[0].isdigit() and parts[5].isdigit():
            m=modules_by_name.get(parts[1])
            sym=False
            if m is not None:
                for path in m.sympaths:
                    full_sym_path=os.path.join(path,
                                               "Contents/Resources/DWARF",
                                               m.module_name)
                    cmd_parts=["atos",
                               "-arch",m.arch,
                               "-l",hex(m.begin),
                               "-o",full_sym_path,
                               parts[2]]

                    #print cmd_parts

                    output=subprocess.check_output(cmd_parts,stderr=subprocess.STDOUT)
                    if len(output)>0:
                        output=output.splitlines()

                        output=[x for x in output if not x.startswith("got symbolicator")]
                        #print output

                        crash_line+=" - "+output[0].strip()
                        #print crash_line

                        if not printed_crash_header:
                            print
                            print len(file_name)*"*"
                            print file_name
                            print len(file_name)*"*"

                            printed_crash_header=True

                        if not printed_thread_header:
                            print
                            print "Thread: %s"%cur_thread
                            print

                            printed_thread_header=True

                        print crash_line

                        sym=True
                        break

        result_lines.append(crash_line)

    # write te output
    output_file_name=os.path.splitext(file_name)[0]+".txt"

    f=open(output_file_name,"wt")
    f.write("\n".join(result_lines))
    f.close()
    del f

##########################################################################
##########################################################################
    
def main(args):
    global g_verbose
    global g_very_verbose
    
    g_verbose=args.verbose
    g_very_verbose=args.very_verbose

    for file_name in args.crash_files:
        symbolicate_crash_file(args,
                               file_name)

##########################################################################
##########################################################################
        
if __name__=="__main__":
    parser=argparse.ArgumentParser(description="symbolicate .crash files")

    parser.add_argument("-v",
                        "--verbose",
                        action="store_true",
                        default=False,
                        help="If specified, verbosity.")

    parser.add_argument("-V",
                        "--very-verbose",
                        action="store_true",
                        default=False,
                        help="If specified, extra verbosity. (Implies -v.)")

    parser.add_argument("crash_files",
                        metavar="CRASH-FILE",
                        nargs="+",
                        help=
                        """Path to .crash files to symbolicate.""")

    result=parser.parse_args()
    main(result)

##########################################################################
##########################################################################
    
