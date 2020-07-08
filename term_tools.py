import ctypes,collections,os

##########################################################################
##########################################################################

TextColours=collections.namedtuple('Colours','fg bg')

##########################################################################
##########################################################################

if os.name=='nt':
    import ctypes

    # https://www.burgaud.com/bring-colors-to-the-windows-console-with-python
    class COORD(ctypes.Structure):
      """struct in wincon.h."""
      _fields_ = [("X",ctypes.c_short),("Y",ctypes.c_short)]

    class SMALL_RECT(ctypes.Structure):
      """struct in wincon.h."""
      _fields_ = [("Left",ctypes.c_short),("Top",ctypes.c_short),("Right",ctypes.c_short),("Bottom",ctypes.c_short)]

    class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
      """struct in wincon.h."""
      _fields_ = [("dwSize",COORD),("dwCursorPosition",COORD),("wAttributes",ctypes.c_ushort),("srWindow",SMALL_RECT),("dwMaximumWindowSize",COORD)]

    GetStdHandle=ctypes.windll.kernel32.GetStdHandle
    SetConsoleTextAttribute=ctypes.windll.kernel32.SetConsoleTextAttribute
    GetConsoleScreenBufferInfo=ctypes.windll.kernel32.GetConsoleScreenBufferInfo
    SetConsoleTitleA=ctypes.windll.kernel32.SetConsoleTitleA

    def get_stdout_handle(): return GetStdHandle(-11) # STD_OUTPUT_HANDLE

    def get_colour_from_attr(attr):
        colour=0
        if attr&8: colour|=8
        if attr&1: colour|=4
        if attr&2: colour|=2
        if attr&4: colour|=1
        return colour
        
    def get_attr_from_colour(x): return get_colour_from_attr(x)
    
    def get_text_colours():
        csbi=CONSOLE_SCREEN_BUFFER_INFO()
        GetConsoleScreenBufferInfo(get_stdout_handle(),ctypes.byref(csbi))

        fg_attr=(csbi.wAttributes>>0)&15
        bg_attr=(csbi.wAttributes>>4)&15

        fg_colour=get_colour_from_attr(fg_attr)
        bg_colour=get_colour_from_attr(bg_attr)

        return TextColours(fg=fg_colour,
                           bg=bg_colour)

    def set_text_colours(fg,bg):
        if fg is None or bg is None:
            colours=get_text_colours()
            if fg is None: fg=colours.fg
            if bg is None: bg=colours.bg

        fg_attr=get_attr_from_colour(fg)
        bg_attr=get_attr_from_colour(bg)

        attr=fg_attr<<0|bg_attr<<4
        SetConsoleTextAttribute(get_stdout_handle(),attr)

    def set_title(title): SetConsoleTitleA(title)
else:        
    def get_text_colours(): return TextColours(0,15)
    def set_text_colours(fg,bg): pass
    def set_title(title): pass

##########################################################################
##########################################################################

class TextColourChanger:
    def __init__(self,fg,bg):
        self._fg=fg
        self._bg=bg

    def __enter__(self):
        self._old_colours=get_text_colours()
        set_text_colours(self._fg,self._bg)
        return self

    def __exit__(self,type,value,traceback):
        set_text_colours(self._old_colours.fg,
                         self._old_colours.bg)
                 
##########################################################################
##########################################################################

class TextColourInverter(TextColourChanger):
    def __init__(self):
        colours=get_text_colours()
        TextColourChanger.__init__(self,colours.bg,colours.fg)

##########################################################################
##########################################################################

