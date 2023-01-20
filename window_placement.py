import os,os.path,argparse,ctypes,ctypes.wintypes,sys,fnmatch,collections,base64

##########################################################################
##########################################################################

g_verbose=False

def pv(msg):
    if g_verbose:
        sys.stdout.write(msg)
        sys.stdout.flush()

##########################################################################
##########################################################################

def fatal(msg):
    sys.stderr.write('FATAL: %s\n'%msg)
    sys.exit(1)
        
##########################################################################
##########################################################################

Window=collections.namedtuple('Window','hwnd title pid placement')

##########################################################################
##########################################################################

class WINDOWPLACEMENT(ctypes.Structure):
    _fields_=[
        ("length",ctypes.c_uint),
        ("flags",ctypes.c_uint),
        ("showCmd",ctypes.c_uint),
        ("ptMinPosition",ctypes.wintypes.POINT),
        ("ptMaxPosition",ctypes.wintypes.POINT),
        ("rcNormalPosition",ctypes.wintypes.RECT),
        ("rcDevice",ctypes.wintypes.RECT),
    ]

ctypes.windll.user32.GetWindowTextLengthW.argtypes=[
    ctypes.wintypes.HWND,
]

ctypes.windll.user32.GetWindowTextW.argtypes=[
    ctypes.wintypes.HWND,
    ctypes.c_wchar_p,
    ctypes.c_int,
]

ctypes.windll.user32.GetWindowThreadProcessId.argtypes=[
    ctypes.wintypes.HWND,
    ctypes.POINTER(ctypes.c_int),
]

WNDENUMPROC=ctypes.WINFUNCTYPE(ctypes.c_int,
                               ctypes.wintypes.HWND,
                               ctypes.c_void_p)

ctypes.windll.user32.EnumWindows.argtypes=[
    WNDENUMPROC,
    ctypes.c_void_p,
]

ctypes.windll.user32.GetWindowPlacement.argtypes=[
    ctypes.wintypes.HWND,
    ctypes.POINTER(WINDOWPLACEMENT),
]

ctypes.windll.user32.SetWindowPlacement.argtypes=[
    ctypes.wintypes.HWND,
    ctypes.POINTER(WINDOWPLACEMENT),
]

ctypes.windll.user32.IsWindowVisible.argtypes=[
    ctypes.wintypes.HWND,
]

ctypes.windll.user32.GetWindowRect.argtypes=[
    ctypes.wintypes.HWND,
    ctypes.POINTER(ctypes.wintypes.RECT),
]

##########################################################################
##########################################################################

def get_string_from_placement(placement):
    return bytes.decode(base64.b64encode(bytes(placement)),
                        'ascii')

def get_placement_from_string(placement_str):
    data=base64.b64decode(placement_str)
    return WINDOWPLACEMENT.from_buffer_copy(data)

##########################################################################
##########################################################################

def get_all_windows():
    windows=[]
    
    title_buffer=ctypes.create_unicode_buffer(65536)

    def enum_callback(hwnd,context):
        # Skip invisible windows - of which there seem to be typically
        # plenty.
        if not ctypes.windll.user32.IsWindowVisible(hwnd):
            return 1

        # Some visible windows are 0x0 at (0,0), so invisible. Skip
        # those, too.
        rect=ctypes.wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(hwnd,ctypes.byref(rect))
        if (rect.left==0 and
            rect.top==0 and
            rect.right==0 and
            rect.bottom==0):
            return 1
        
        result=ctypes.windll.user32.GetWindowTextW(hwnd,
                                                   title_buffer,
                                                   len(title_buffer))
        if result>0: title=title_buffer.value
        else: title=''

        pid=ctypes.c_int()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd,
                                                      ctypes.byref(pid))

        placement=WINDOWPLACEMENT()
        placement.length=ctypes.sizeof(WINDOWPLACEMENT)
        ctypes.windll.user32.GetWindowPlacement(hwnd,
                                                ctypes.byref(placement))

        windows.append(Window(hwnd=hwnd,
                              title=title,
                              pid=pid.value,
                              placement=placement))

        return 1

    ctypes.windll.user32.EnumWindows(WNDENUMPROC(enum_callback),None)

    return windows

##########################################################################
##########################################################################

def get_windows_of_interest(windows,options):
    result=[]

    for window in windows:
        matches=True
        
        if options.title is not None:
            if window.title is not None:
                if options.title_literal:
                    matches=(matches and
                             window.title==options.title)
                else:
                    matches=(matches and
                             fnmatch.fnmatch(window.title,options.title))
            
        if options.pid is not None:
            matches=(matches and
                     window.pid==options.pid)

        if matches: result.append(window)

    return result

##########################################################################
##########################################################################

# https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-enumwindows

def main2(options):
    global g_verbose;g_verbose=options.verbose

    pv('%d\n'%ctypes.sizeof(WINDOWPLACEMENT))
    
    windows=get_all_windows()
    pv('Total windows: %d\n'%len(windows))

    windows=get_windows_of_interest(windows,options)

    if options.cmd=='list':
        for window in windows:
            print('%s {{ PID: %d ; HWND: 0x%x ; placement: %s }}'%(
                window.title,
                window.pid,
                window.hwnd,
                get_string_from_placement(window.placement)))
    elif options.cmd=='set':
        placement=get_placement_from_string(options.placement)
        
        windows=get_windows_of_interest(windows,options)
        if len(windows)==0: fatal('No matching windows found')
        elif len(windows)>1: fatal('Found %d matching windows'%len(windows))

        result=ctypes.windll.user32.SetWindowPlacement(windows[0].hwnd,
                                                       placement)
        if result!=0:
            error=ctypes.get_last_error()
            fatal('SetWindowPlacement failed: %s'%(ctypes.FormatError(error)))

##########################################################################
##########################################################################

def main(argv):
    def auto_int(x): return int(x,0)
    
    parser=argparse.ArgumentParser()

    parser.add_argument('-v','--verbose',action='store_true',help='''be more verbose''')
    parser.add_argument('--title',metavar='TITLE',default=None,help='''search by window title''')
    parser.add_argument('--title-literal',action='store_true',help='''treat window title as literal rather than fnmatch pattern''')
    parser.add_argument('--pid',metavar='PID',type=auto_int,default=None,help='''search by PID''')
    parser.set_defaults(fun=None)

    subparsers=parser.add_subparsers(title='sub-command help',dest='cmd')

    set_parser=subparsers.add_parser('set',help='''set placement for window''')
    set_parser.add_argument('placement',metavar='PLACEMENT',help='''placement data for window, as previously reported by get''')
    # set_parser.add_argument('--wait',metavar='N',default=0,type=auto_int,help='''if 0 windows found, keep retrying for up to %(metavar)s second(s)''')

    list_parser=subparsers.add_parser('list',help='''list top-level windows and their attributes''')

    options=parser.parse_args(argv)
    if options.cmd is None:
        parser.print_help()
        sys.exit(1)

    main2(options)

##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv[1:])
