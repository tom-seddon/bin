#!env python
import os,os.path,sys,tempfile,subprocess

##########################################################################
##########################################################################

got_msvcrt=True
try:
    import msvcrt
except:
    got_msvcrt=False

##########################################################################
##########################################################################

def main():
    data=sys.stdin.read()

    temp_fname=os.path.join(tempfile.gettempdir(),"pmacs.%d.dat"%os.getpid())
    with open(temp_fname,"wb") as f:
        f.write(data)

    # seems the safest way of ensuring elisp doesn't get anything wrong...
    fname_chars=""
    fname_bytes=[]
    for c in temp_fname:
        if c.isalnum() or c in "_.":
            fname_chars+=c
        else:
            fname_chars+="%c"
            fname_bytes.append(str(ord(c)))

    elisp=[
        r'(let ((bufname (let ((i 0)',
        r'                     bufname)',
        r'                 (while (progn',
        r'                          (setq bufname (concat "*pmacs"',
        r'                                                (if (= i 0)',
        r'                                                    ""',
        r'                                                  (int-to-string i))',
        r'                                                "*"))',
        r'                          (setq i (1+ i))',
        r'                          (get-buffer bufname)))',
        r'                 bufname)))',
        r'  (let ((fname (format "%s" %s)))'%(fname_chars," ".join(fname_bytes)),
        r'    (find-file fname)',
        r'    (fundamental-mode)',
        r'    (set-visited-file-name nil)',
        r'    (rename-buffer bufname)',
        r'    (delete-file fname)',
        r'    (message "got %d bytes" (- (point-max) (point-min)))))',
    ]

    #print elisp

    # hmm...
    if sys.platform=="darwin":
        emacsclient="/applications/emacs.app/contents/macos/bin/emacsclient"
    elif sys.platform=="win32":
        emacsclient="C:\\emacs\\bin\\emacsclient.exe"
    else:
        emacsclient="emacsclient"

    argv=[emacsclient,
          "-n",
          "-e",
          " ".join(elisp)]
    #print argv
    r=subprocess.call(argv)

    print "%d - %d byte(s) - %s"%(r,len(data),temp_fname)

##########################################################################
##########################################################################

if __name__=="__main__":
    if got_msvcrt:
        msvcrt.setmode(sys.stdin.fileno(),os.O_BINARY)
        
    main()

