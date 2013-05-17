#!env python
import glob,os,os.path,sys

prefix="#XcodeMenuName: "
scripts_folder=os.path.expanduser("~/Library/Application Support/Developer/Shared/Xcode/Scripts")

scripts=[]

for py_name in glob.glob("*.py"):
    f=open(py_name,"rt")
    lines=[x.strip() for x in f.readlines()]
    f.close()
    del f

    name=None
    for line in lines:
        if line.startswith(prefix):
            name=line[len(prefix):]
            break
            
    if name is None:
        continue

    scripts.append((os.path.join(os.getcwd(),
                                 py_name),
                    os.path.join(scripts_folder,
                                 name)))

bad=0
    
for py_name,link_name in scripts:
    if os.path.lexists(link_name) and not os.path.islink(link_name):
        sys.stderr.write("FATAL: \"%s\" already exists.\n"%link_name)
        bad=1

if bad:
    sys.exit(1)

for py_name,link_name in scripts:
    if os.path.lexists(link_name):
        os.unlink(link_name)

    src_folder,src_name=os.path.split(py_name)
    dest_folder,dest_name=os.path.split(link_name)

    os.symlink(os.path.join(os.path.relpath(src_folder,
                                            dest_folder),
                            src_name),
               link_name)
    
