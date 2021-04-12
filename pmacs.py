#!/usr/bin/python
import os,os.path,sys,tempfile,subprocess,argparse

##########################################################################
##########################################################################

got_msvcrt=True
try:
    import msvcrt
except:
    got_msvcrt=False

##########################################################################
##########################################################################

def main(options):
    if sys.version_info[0]<3: data=sys.stdin.read()
    else: data=sys.stdin.buffer.read()

    temp_fname=os.path.join(tempfile.gettempdir(),"pmacs.%d.dat"%os.getpid())
    with open(temp_fname,"wb") as f: f.write(data)

    # seems the safest way of ensuring elisp doesn't get anything wrong...
    fname_chars=""
    fname_bytes=[]
    for c in temp_fname:
        if c.isalnum() or c in "_.":
            fname_chars+=c
        else:
            fname_chars+="%c"
            fname_bytes.append(str(ord(c)))

    elisp=[]
    elisp+=[r'(let ((bufname (let ((i 0)']
    elisp+=[r'                     bufname)']
    elisp+=[r'                 (while (progn']
    elisp+=[r'                          (setq bufname (concat "*pmacs"']
    elisp+=[r'                                                (if (= i 0)']
    elisp+=[r'                                                    ""']
    elisp+=[r'                                                  (int-to-string i))']
    elisp+=[r'                                                "*"))']
    elisp+=[r'                          (setq i (1+ i))']
    elisp+=[r'                          (get-buffer bufname)))']
    elisp+=[r'                 bufname)))']
    elisp+=[r'  (let ((fname (format "%s" %s)))'%(fname_chars," ".join(fname_bytes))]
    elisp+=[r'    (find-file fname)']
    elisp+=[r'    (fundamental-mode)']
    elisp+=[r'    (set-visited-file-name nil)']
    elisp+=[r'    (rename-buffer bufname)']
    elisp+=[r'    (delete-file fname)']
    elisp+=[r'    (message "got %d bytes" (- (point-max) (point-min)))']

    for command in options.commands:
        elisp+=['    (command-execute \'%s)'%command]

    elisp+=[r'  ))']

    # if options.verbose:
    #     print>>sys.stderr,elisp

    # hmm...
    if sys.platform=="darwin":
        emacsclient="/applications/emacs.app/contents/macos/bin/emacsclient"
    elif sys.platform=="win32":
        emacsclient="C:\\emacs\\bin\\emacsclient.exe"
    else:
        emacsclient="emacsclient"

    sys.stderr.write("saved %d byte(s) to %s\n"%(len(data),temp_fname))

    argv=[emacsclient,
          "-n",
          "-e",
          " ".join(elisp)]
    #print argv
    r=subprocess.call(argv)

    sys.stderr.write("emacsclient: %d\n"%r)

##########################################################################
##########################################################################

def pmacs(argv):
    parser=argparse.ArgumentParser()

    parser.add_argument('-v','--verbose',action='store_true',help='be more verbose')
    parser.add_argument('-x',action='append',default=[],dest='commands',metavar='COMMAND',help='do (in effect) M-x %(metavar)s once file is loaded')

    main(parser.parse_args(argv))

##########################################################################
##########################################################################

if __name__=="__main__":
    if got_msvcrt:
        msvcrt.setmode(sys.stdin.fileno(),os.O_BINARY)

    pmacs(sys.argv[1:])

