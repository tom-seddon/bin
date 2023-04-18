#!/usr/bin/python3
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

def find_emacsclient(paths):
    for path in paths:
        if os.path.isfile(path): return path

    for path in paths: sys.stderr.write('Not found: %s\n'%path)
    sys.stderr.write('FATAL: failed to find emacsclient\n')
    sys.exit(1)

def main(options):
    if sys.version_info[0]<3: data=sys.stdin.read()
    else: data=sys.stdin.buffer.read()

    temp_fname=os.path.join(tempfile.gettempdir(),"pmacs.%d.txt"%os.getpid())
    with open(temp_fname,"wb") as f: f.write(data)

    if options.verbose: sys.stderr.write("saved %d byte(s) to %s\n"%(len(data),temp_fname))

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
    elisp+=[r'    (let ((num-chars (- (point-max) (point-min))))']
    # elisp+=[r'      (fundamental-mode)']
    elisp+=[r'      (set-visited-file-name nil)']
    elisp+=[r'      (rename-buffer bufname)']
    elisp+=[r'      (delete-file fname)']

    if options.mode is not None: elisp+=[r'      (%s-mode)'%options.mode]

    for command in options.commands: elisp+=['      (command-execute \'%s)'%command]

    # elisp+=[r'      (message "%d char(s) in buffer" num-chars)']

    elisp+=[r'  )))']

    # if options.verbose:
    #     print>>sys.stderr,elisp

    # hmm...
    if sys.platform=="darwin":
        emacsclient=find_emacsclient([
            "/applications/emacs.app/contents/macos/bin/emacsclient",
        ])
    elif sys.platform=="win32":
        emacsclient=find_emacsclient([
            "C:\\emacs\\bin\\emacsclient.exe",
            "O:\\emacs\\bin\\emacsclient.exe",
        ])
    else: emacsclient="emacsclient"

    argv=[emacsclient]
    argv+=["--no-wait"]
    if not options.verbose: argv+=['--suppress-output']
    argv+=["--eval"," ".join(elisp)]
    #print argv
    r=subprocess.call(argv)

    if options.verbose or r!=0: sys.stderr.write("emacsclient exit code: %d\n"%r)
    sys.exit(r)

##########################################################################
##########################################################################

def pmacs(argv):
    parser=argparse.ArgumentParser()

    parser.add_argument('-v','--verbose',action='store_true',help='be more verbose')
    parser.add_argument('-x',action='append',default=[],dest='commands',metavar='COMMAND',help='do (in effect) M-x %(metavar)s once file is loaded and mode (if any) selected')
    parser.add_argument('-m','--mode',default=None,metavar='MODE',help='select major mode %(metavar)s-mode')

    main(parser.parse_args(argv))

##########################################################################
##########################################################################

if __name__=="__main__":
    if got_msvcrt:
        msvcrt.setmode(sys.stdin.fileno(),os.O_BINARY)

    pmacs(sys.argv[1:])

