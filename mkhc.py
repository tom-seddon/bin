#!/usr/bin/python
import sys,os.path,optparse,os,subprocess,uuid

def sep2(f):
    f.write("//////////////////////////////////////////////////////////////////////////\n")
    f.write("//////////////////////////////////////////////////////////////////////////\n")

def get_paths(options):
    if options.cwd:
        return (".",
                ".")

    last_path=None
    cur_path=os.getcwd()
    while cur_path!=last_path:
        file_name=os.path.join(cur_path,
                               ".mkhc")
        if os.path.isfile(file_name):
            f=open(file_name,
                   "rt")
            lines=[line.strip() for line in f.readlines()]
            f.close()
            del f

            h_path="."
            cpp_path="."

            for line in lines:
                parts=line.split("=",1)
                if len(parts)==2:
                    if parts[0]=="MKHC_H":
                        h_path=parts[1]
                    elif parts[0]=="MKHC_CPP":
                        cpp_path=parts[1]

            h_path=os.path.join(cur_path,
                                h_path)
            cpp_path=os.path.join(cur_path,
                                  cpp_path)

            print>>sys.stderr,"Settings from \"%s\":"%file_name
            print>>sys.stderr,"    .cpp path: \"%s\""%cpp_path
            print>>sys.stderr,"    .h path: \"%s\""%h_path

            return (h_path,
                    cpp_path)

        last_path=cur_path
        cur_path=os.path.normpath(os.path.join(cur_path,
                                               ".."))
        
    h_path=os.getenv("MKHC_H")
    if h_path is None:
        h_path="."

    cpp_path=os.getenv("MKHC_CPP")
    if cpp_path is None:
        cpp_path="."

    return (h_path,
            cpp_path)

def main():
    parser=optparse.OptionParser()

    parser.add_option("-p",
                      "--pch",
                      action="store_true",
                      help='include #include "pch.h" at the top of the .cpp file')

    parser.add_option("-s",
                      "--stdafx",
                      action="store_true",
                      help='include #include "stdafx.h" at the top of the .cpp file')

    parser.add_option("-c",
                      "--class",
                      action="store_true",
                      dest="_class",
                      help="include C++ class skeleton")

    parser.add_option("-n",
                      "--noncopyable",
                      action="store_true",
                      help="C++ class skeleton (if present) is noncopyable")

    parser.add_option("-f",
                      "--force",
                      action="store_true",
                      help="overwrite existing files")

    parser.add_option("-b",
                      "--base",
                      action="store",
                      type="string",
                      help="specify base class if generating a class skeleton.")

    parser.add_option("--c",
                      action="store_true",
                      default=False,
                      help="if specified, generate .c.")

    parser.add_option("--m",
                      action="store_true",
                      default=False,
                      help="if specified, generate .m.")

    parser.add_option("--mm",
                      action="store_true",
                      default=False,
                      help="if specified, generate .mm.")
    
    parser.add_option("--extern-c",
                      action="store_true",
                      default=False,
                      help="if specified, include extern \"C\" junk in header.")

    parser.add_option("-.",
                      action="store_true",
                      dest="cwd",
                      default=False,
                      help="if specified, always put files in .")

    parser.add_option("-_",
                      "--extra-underscores",
                      action="store_true",
                      default=False,
                      help="if specified, extra underscores in header include guard (__THIS__ instead of THIS_)")

    parser.add_option("-N",
                      "--no-separators",
                      action="store_true",
                      default=False,
                      help="if specified, no separating comment lines")

    parser.add_option("-i",
                      "--inl",
                      action="store_true",
                      default=False,
                      help="if specified, generate empty .inl file next to header")

    options,args=parser.parse_args()

    if len(args)==0:
        parser.error("Must specify at least one output file")

    h_path,cpp_path=get_paths(options)

    guard_prefix=os.getenv("MKHC_GUARD_PREFIX")
    if guard_prefix is None:
        guard_prefix=""

    for arg in args:
        name=os.path.split(arg)[1]

        define_str="header_"+str(uuid.uuid4()).replace("-","")
        if define_str is None:
            define_str=name+"_H"

        define=""
        for c in define_str.upper():
            if c.isalpha() or c.isdigit():
                define+=c
            else:
                define+="_"

        define=guard_prefix+define
        if options.extra_underscores:
            define="__"+define+"__"
            
        h_name=arg+".h"
        inl_name=arg+".inl"

        if options.c:
            cpp_name=arg+".c"
        elif options.m:
            cpp_name=arg+".m"
        elif options.mm:
            cpp_name=arg+".mm"
        else:
            cpp_name=arg+".cpp"

        if options.c or options.m:
            emacs_mode_setting=""
        else:
            emacs_mode_setting="// -*- mode:c++ -*-"

        h_name=os.path.join(h_path,
                            h_name)

        inl_name=os.path.join(h_path,
                              inl_name)

        cpp_name=os.path.join(cpp_path,
                              cpp_name)

        if not options.force:
            exists=0
            files=[h_name,cpp_name]
            if options.inl: files.append(inl_name)
            for file in files:
                if os.path.isfile(file):
                    print>>sys.stderr,"WARNING: not overwriting \"%s\""%file
                    exists=1

            if exists:
                print>>sys.stderr,"WARNING: not creating from \"%s\""%arg
                continue

        f=open(h_name,"wt")
        f.write("#ifndef "+define+" "+emacs_mode_setting+"\n")
        f.write("#define "+define+"\n")
        f.write("\n")

        if options.extern_c:
            f.write("#ifdef __cplusplus\n")
            f.write("extern \"C\"\n")
            f.write("{\n")
            f.write("#endif//__cplusplus\n")
            f.write("\n")

        if options._class:
            if not options.no_separators:
                sep2(f)
                f.write("\n")

            if options.base is None:
                f.write("class %s\n"%name)
            else:
                f.write("#include \"%s.h\"\n"%options.base)
                
                f.write("\n")

                if not options.no_separators:
                    sep2(f)
                    f.write("\n")
    
                f.write("class %s:\n"%name)
                f.write("\tpublic %s\n"%options.base)
            
            f.write("{\n");
            f.write("public:\n");
            f.write("\t%s();\n"%name)
            f.write("\t~%s();\n"%name)
            f.write("protected:\n");
            f.write("private:\n");

            if options.noncopyable:
                f.write("\t%s(const %s &);\n"%(name,name))
                f.write("\t%s &operator=(const %s &);\n"%(name,name))
            
            f.write("};\n");
            f.write("\n");

            if not options.no_separators:
                sep2(f)
                f.write("\n")

        if options.extern_c:
            f.write("#ifdef __cplusplus\n")
            f.write("}\n")
            f.write("#endif//__cplusplus\n")
            f.write("\n")

        f.write("#endif//"+define+"\n")
        f.close()

        if options.inl:
            with open(inl_name,"wt") as f:
                print>>f
                

        f=open(cpp_name,"wt")

        if options.pch:
            f.write("#include \"pch.h\"\n")
        elif options.stdafx:
            f.write("#include \"stdafx.h\"\n")

        if not (options.pch and name.lower()=="pch"):
            f.write("#include \""+name+".h\"\n")

        if options._class:
            f.write("\n")
            
            if not options.no_separators:
                sep2(f)
                f.write("\n")
            
            f.write("%s::%s()\n{\n}\n"%(name,name))

            f.write("\n")
            
            if not options.no_separators:
                sep2(f)
                f.write("\n")
            
            f.write("%s::~%s()\n{\n}\n"%(name,name))
            
            f.write("\n")

            if not options.no_separators:
                sep2(f)
            
        f.close()

if __name__=="__main__":
    main()
