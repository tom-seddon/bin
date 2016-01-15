#!/usr/bin/python
import sys,os.path,argparse,os,subprocess,uuid,collections

##########################################################################
##########################################################################

g_verbose=False

def v(x):
    if g_verbose:
        sys.stdout.write(x)
        sys.stdout.flush()

##########################################################################
##########################################################################

def toggle_prefix(s,p):
    if s.startswith(p): return s[len(p):]
    else: return p+s

##########################################################################
##########################################################################
    
def get_switch_opts(so,lo):
    args=[]

    if so is not None: args.append("-"+so)
    if lo is not None: args.append("--"+lo)

    return args

##########################################################################
##########################################################################

def get_option_name(o):
    if o.lo is not None: return o.lo
    if o.so is not None: return o.so
    return "???"

##########################################################################
##########################################################################

class FlagOption:
    def __init__(self,so,lo,dest,help):
        self.lo=lo
        self.so=so
        self.dest=dest
        self.help=help

    def add_argparse_options(self,parser):
        parser.add_argument(*get_switch_opts(self.so,self.lo),dest=self.dest,action="store_true",help=self.help,default=False)

        if self.lo is not None:
            parser.add_argument("--"+toggle_prefix(self.lo,"no-"),
                                dest=self.dest,
                                action="store_false",
                                default=False,
                                help=toggle_prefix(self.help,"don't "))

##########################################################################
##########################################################################

class StringOption:
    def __init__(self,so,lo,dest,help,default=None):
        self.so=so
        self.lo=lo
        self.dest=dest
        self.help=help
        self.default=default

    def add_argparse_options(self,parser):
        parser.add_argument(*get_switch_opts(self.so,self.lo),dest=self.dest,action="store",help=self.help,default=self.default)

class PathOption(StringOption):
    def __init__(self,so,lo,dest,help,default=None): StringOption.__init__(self,so,lo,dest,help,default)
        
##########################################################################
##########################################################################

g_options=[
    FlagOption("p","pch","pch",'include #include "pch.h" at the top of the .cpp file'),
    FlagOption("s","stdafx","stdafx",'include #include "stdafx.h" at the top of the .cpp file'),
    FlagOption("c","class","_class","include C++ class skeleton"),
    FlagOption("n","noncopyable","noncopyable","generate C++ class skeleton that's noncopyable"),
    FlagOption(None,"c","c","generate .c."),
    FlagOption(None,"m","m","generate .m."),
    FlagOption(None,"mm","mm","generate .mm."),
    FlagOption(None,"extern-c","extern_c","include extern \"C\" junk in header."),
    FlagOption(".",None,"cwd","always put files in ."),
    FlagOption("_","extra-underscores","extra_underscores","extra underscores in header include guard (__THIS__ instead of THIS_)"),
    FlagOption("N","no-separators","no_separators","don't add separating comment lines"),
    FlagOption("i","inl","inl","generate empty .inl file next to header"),
    FlagOption("k","knr","knr","produce K&R-style braces"),
    StringOption("b","base","base","base class when generating a class skeleton"),
    StringOption(None,"tab","tab","string to use as a tab (default is tab char)",default="\t"),
    PathOption("t","template","template","file to read comment template from"),
    PathOption(None,"header-folder","h_folder","folder to put header files in",default="."),
    PathOption(None,"src-folder","src_folder","folder to put source files in",default="."),
    PathOption(None,"MKHC_H","h_folder","folder to put header files in"),
    PathOption(None,"MKHC_CPP","src_folder","folder to put source files in"),
]

##########################################################################
##########################################################################

def get_brace(options):
    if options.knr: return " {"
    else: return "\n{"

##########################################################################
##########################################################################

def get_source_ext(options):
    if options.c: return "c"
    elif options.m: return "m"
    elif options.mm: return "mm"
    else: return "cpp"

##########################################################################
##########################################################################

def copy_template_file(options,f):
    if options.template is None: return

    with open(options.template,"rt") as tf: lines=[x.strip() for x in tf.readlines()]

    for line in lines: f.write("%s\n"%line)
    f.write("\n")
    
##########################################################################
##########################################################################

def write_header_file(options,f,name):
    define=("header_"+str(uuid.uuid4()).replace("-","")).upper()
    brace=get_brace(options)

    if options.c or options.m: emacs=""
    else: emacs="// -*- mode:c++ -*-"

    f.write("#ifndef %s%s\n"%(define,emacs))
    f.write("#define %s\n"%define)
    f.write("\n")

    copy_template_file(options,f)

    if options.extern_c:
        f.write("#ifdef __cplusplus\n")
        f.write("extern \"C\"%s\n"%brace)
        f.write("#endif\n\n")

    if options._class:
        if options.base is None: f.write("class %s%s\n"%(name,brace))
        else:
            f.write("#include \"%s.h\"\n"%options.base)
            f.write("\n")
            f.write("class %s:\n"%name)
            f.write("\tpublic %s\n"%options.base)
            f.write("{\n");

        f.write("public:\n")
        f.write("%s%s();\n"%(options.tab,name))
        f.write("%s~%s();\n"%(options.tab,name))
        f.write("protected:\n")
        f.write("private:\n")

        if options.noncopyable:
            f.write("%s%s(const %s &);\n"%(options.tab,name,name))
            f.write("%s%s &operator=(const %s &);\n"%(options.tab,name,name))

        f.write("};\n")

    if options.extern_c:
        f.write("\n#ifdef __cplusplus\n")
        f.write("}\n")
        f.write("#endif\n")

    f.write("\n#endif\n")

##########################################################################
##########################################################################

def write_source_file(options,f,name):
    brace=get_brace(options)

    copy_template_file(options,f)
    
    if options.pch: f.write("#include \"pch.h\"\n")
    elif options.stdafx: f.write("#include \"stdafx.h\"\n")

    if not (options.pch and name.lower()=="pch"): f.write("#include \"%s.h\"\n"%name)

    if options._class:
        f.write("\n")

        f.write("%s::%s()%s\n}\n\n"%(name,name,brace))
        f.write("%s::~%s()%s\n}\n"%(name,name,brace))

##########################################################################
##########################################################################
        
def write_inl_file(options,f,name):
    copy_template_file(options,f)

##########################################################################
##########################################################################

def pretty_print_options(options):
    max_width=0
    for option in g_options: max_width=max(max_width,len(get_option_name(option)))

    v("Settings:\n")
    attrs_seen=set()
    for option in g_options:
        if option.dest in attrs_seen: continue

        attrs_seen.add(option.dest)
        x=getattr(options,option.dest)
        
        v("    %-*s: %s\n"%(max_width,get_option_name(option),x))

##########################################################################
##########################################################################

class Output: pass

def main(options):
    global g_verbose ; g_verbose=options.verbose

    # Knobble a couple of things.
    if options.cwd:
        options.h_folder="."
        options.src_folder="."
    
    pretty_print_options(options)

    good=True
    outputs=[]
    for name in options.names:
        o=Output()

        o.name=name
        
        o.h=os.path.join(options.h_folder,"%s.h"%name)

        if options.inl: o.inl=os.path.join(options.h_folder,"%s.inl"%name)
        else: o.inl=None

        o.src=os.path.join(options.src_folder,"%s.%s"%(name,get_source_ext(options)))
        
        if not options.force:
            for fname in [o.h,o.inl,o.src]:
                if fname is None: continue
                if os.path.isfile(fname):
                    print>>sys.stderr,"FATAL: file exists: %s"%fname
                    good=False

        outputs.append(o)

    if not good: sys.exit(1)

    for output in outputs:
        if output.h is not None:
            with open(output.h,"wt") as f: write_header_file(options,f,output.name)

        if output.inl is not None:
            with open(output.inl,"wt") as f: write_inl_file(options,f,output.name)

        if output.src is not None:
            with open(output.src,"wt") as f: write_source_file(options,f,output.name)

##########################################################################
##########################################################################

def read_mkhc_args(args):
    path="."
    while True:
        mkhc_fname=os.path.join(path,".mkhc")
        if os.path.isfile(mkhc_fname):
            parent=False
            with open(mkhc_fname,"rt") as f:
                for x in f.readlines():
                    x=x.strip()
                    if x.startswith("#"):
                        # comment
                        if x=="#..": parent=True
                        continue

                    # munge file name, if necessary
                    parts=x.split("=",1)
                    if len(parts)==2:
                        for option in g_options:
                            if not isinstance(option,PathOption): continue
                            if parts[0]==option.lo:
                                parts[1]=os.path.join(path,parts[1])
                                break

                        args.append("--%s=%s"%(parts[0],parts[1]))
                    else:
                        args.append("--%s"%parts[0])

            if not parent: break

        next_path=path+"/.."
        if os.name=="nt":
            if os.path.normpath(os.path.abspath(path))==os.path.normpath(os.path.abspath(next_path)):
                # hit root folder...
                break
        else:
            if os.path.samefile(path,next_path):
                # hit root folder...
                break
        
        path=next_path

##########################################################################
##########################################################################
    
if __name__=="__main__":
    parser=argparse.ArgumentParser()

    for option in g_options: option.add_argparse_options(parser)

    parser.add_argument("-v","--verbose",action="store_true",default=False,help="extra verbosity")
    parser.add_argument("names",metavar="NAME",nargs="*",help="name of files/classes to generate")
    parser.add_argument("-f","--force",action="store_true",default=False,
                        help="overwrite existing files")

    args=sys.argv[1:]

    read_mkhc_args(args)

    main(parser.parse_args(args))
