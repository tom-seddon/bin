#!/usr/bin/python3
import sys,os,os.path,argparse,subprocess,re,collections,fnmatch

##########################################################################
##########################################################################

g_verbose=False

def pv(x):
    if g_verbose:
        sys.stdout.write(x)
        sys.stdout.flush()

##########################################################################
##########################################################################

class Call:
    def __init__(self,fun,args,result,errno):
        self.fun=fun
        self.args=args
        self.result=result
        self.errno=errno
        self.annotation=None

##########################################################################
##########################################################################

class ParseException(Exception): pass

##########################################################################
##########################################################################

number_re=re.compile(r'''(?P<hex>0x([0-9A-Fa-f]+))|(?P<oct>0[0-9]+)|(?P<dec>[0-9]+)''')
symbol_re=re.compile(r'''[A-Za-z_][A-Za-z_0-9]*''')
list_count_re=re.compile(r'''\s*\((?P<size>[0-9]+)\)''')
pid_thrd_re=re.compile(r'''\s*(?P<pid>[0-9]+)/(?P<thrd>0x[0-9A-Fa-f]+):\s*''')

##########################################################################
##########################################################################

# record parsed type, so the values can round trip exactly.
# Number=collections.namedtuple('Number','value type name')
class Number:
    def __init__(self,value,type):
        assert type in 'dxo'
        self.value=value
        self.type=type
        self.string=None

    def __str__(self):
        if self.type=='d': s='%d'%self.value
        elif self.type=='x': s='0x%X'%self.value
        elif self.type=='o': s='0%o'%self.value
        else: assert False,self.type

        if self.string is not None: s+=' (%s)'%self.string

        return s

    def __repr__(self):
        return 'Number(value: %d; type: %s; string: %s)'%(self.value,
                                                          self.type,
                                                          self.string)

##########################################################################
##########################################################################

class Symbol:
    def __init__(self,name): self.name=name

##########################################################################
##########################################################################

ParseArgsResult=collections.namedtuple('ParseArgsResult','args index')

def parse_args(line,i,closer):
    args=[]
    pv('parse_args: i=%d; closer=%s: %s'%(i,closer,line[i:]))
    while True:
        if line[i].isdigit():
            # number: hex, octal, decimal
            m=number_re.match(line,i)
            if m is None: raise ParseException('invalid number',i)
            value=int(m.group(0),0)
            i=m.end()

            if m.group('hex') is not None: num=Number(value,'x')
            elif m.group('dec') is not None: num=Number(value,'d')
            elif m.group('oct') is not None: num=Number(value,'o')
            else: raise ParseException('oddity',i)

            args.append(num)
            
            pv('got number: %s'%repr(args[-1]))
        elif line[i].isalpha() or line[i]=='_':
            m=symbol_re.match(line,i)
            if m is None: raise ParseException('invalid symbol',i)
            args.append(Symbol(m.group(0)))
            i=m.end()
            if g_verbose: print('got symbol: %s'%args[-1].name)
        elif line[i]=='"':
            # string
            i+=1                # skip opening "
            string_begin=i
            while True:
                if line[i]=='\\': i+=2
                elif line[i]=='"': break
                else: i+=1
            args.append(line[string_begin:i])
            i+=1                # skip closing "
        elif line[i]=='[':
            # list
            result=parse_args(line,i+1,']')
            i=result.index

            # count follows.
            m=list_count_re.match(line,i)
            if m is None: raise ParseException('invalid sysctl args',i)
            size=int(m.group('size'))

            pv('got args: %s (%d)'%(result.args,size))
            
            args.append(result.args[:size])
            
            i=m.end()
        else: raise ParseException('unexpected argument char',i)

        if line[i]==closer:
            i+=1                # skip closer
            break

        if line[i]!=',': raise ParseException('unexpected char',i)
        i+=1                    # skip ,
        
        while line[i]==' ': i+=1

    return ParseArgsResult(args,i)
    
##########################################################################
##########################################################################

def parse_call(line,extra_columns):
    i=0
    if 'PID/THRD' in extra_columns:
        m=pid_thrd_re.match(line,i)
        if m is None:
            raise ParseException('failed to parse PID/THRD prefix')

        pid=int(m.group('pid'),0)
        thrd=int(m.group('thrd'),0)

        i=m.end()

    fun_begin=i
    i=line.find('(',i)
    if i<0: raise ParseException("no '('")

    fun=line[fun_begin:i]
    i+=1                        # skip (
    args,i=parse_args(line,i,')')

    eq=line.find('=',i)
    if eq<0: raise ParseException("no '='",i)
    i=eq

    result=line[i+1:].lstrip()

    if result=='return':
        errno=None
    else:
        parts=result.split()

        # not very clever
        if parts[0].startswith('0x'):
            result=Number(int(parts[0],0),type='x')
        else: result=Number(int(parts[0]),type='d')

        err_prefix='Err#'
        if parts[1].startswith(err_prefix):
            errno=int(parts[1][len(err_prefix):])
        else: errno=int(parts[1])

    return Call(fun=fun,args=args,result=result,errno=errno)

##########################################################################
##########################################################################

# def _IO(g,n): return _IOC(IOC_VOID,g,n)
# def _IOR(g,n): return _IOC(IOC_OUT,g,n)
# def _IOW(g,n): return _IOC(IOC_IN,g,n)
# def _IOWR(

g_all_header_paths=[]

# generated by other/print_macos_ioctls
g_ioctl_name_by_value={
    0x80706e65:"NFSCLNT_LOCKDANS",
    0x80186e66:"NFSCLNT_LOCKDNOTIFY",
    0xc4206e67:"NFSCLNT_TESTIDMAP",
    0x40044266:"BIOCGBLEN",
    0xc0044266:"BIOCSBLEN",
    0x80104267:"BIOCSETF",
    0x20004268:"BIOCFLUSH",
    0x20004269:"BIOCPROMISC",
    0x4004426a:"BIOCGDLT",
    0x4020426b:"BIOCGETIF",
    0x8020426c:"BIOCSETIF",
    0x8010426d:"BIOCSRTIMEOUT",
    0x4010426e:"BIOCGRTIMEOUT",
    0x4008426f:"BIOCGSTATS",
    0x80044270:"BIOCIMMEDIATE",
    0x40044271:"BIOCVERSION",
    0x40044272:"BIOCGRSIG",
    0x80044273:"BIOCSRSIG",
    0x40044274:"BIOCGHDRCMPLT",
    0x80044275:"BIOCSHDRCMPLT",
    0x40044276:"BIOCGSEESENT",
    0x80044277:"BIOCSSEESENT",
    0x80044278:"BIOCSDLT",
    0xc00c4279:"BIOCGDLTLIST",
    0x8010427e:"BIOCSETFNR",
    0x40044101:"AUDITPIPE_GET_QLEN",
    0x40044102:"AUDITPIPE_GET_QLIMIT",
    0x80044103:"AUDITPIPE_SET_QLIMIT",
    0x40044104:"AUDITPIPE_GET_QLIMIT_MIN",
    0x40044105:"AUDITPIPE_GET_QLIMIT_MAX",
    0x40084106:"AUDITPIPE_GET_PRESELECT_FLAGS",
    0x80084107:"AUDITPIPE_SET_PRESELECT_FLAGS",
    0x40084108:"AUDITPIPE_GET_PRESELECT_NAFLAGS",
    0x80084109:"AUDITPIPE_SET_PRESELECT_NAFLAGS",
    0x400c410a:"AUDITPIPE_GET_PRESELECT_AUID",
    0x800c410b:"AUDITPIPE_SET_PRESELECT_AUID",
    0x8004410c:"AUDITPIPE_DELETE_PRESELECT_AUID",
    0x2000410d:"AUDITPIPE_FLUSH_PRESELECT_AUID",
    0x4004410e:"AUDITPIPE_GET_PRESELECT_MODE",
    0x8004410f:"AUDITPIPE_SET_PRESELECT_MODE",
    0x20004110:"AUDITPIPE_FLUSH",
    0x40044111:"AUDITPIPE_GET_MAXAUDITDATA",
    0x40084164:"AUDITPIPE_GET_INSERTS",
    0x40084165:"AUDITPIPE_GET_READS",
    0x40084166:"AUDITPIPE_GET_DROPS",
    0x40084167:"AUDITPIPE_GET_TRUNCATES",
    0x40045301:"AUDITSDEV_GET_QLEN",
    0x40045302:"AUDITSDEV_GET_QLIMIT",
    0x80045303:"AUDITSDEV_SET_QLIMIT",
    0x40045304:"AUDITSDEV_GET_QLIMIT_MIN",
    0x40045305:"AUDITSDEV_GET_QLIMIT_MAX",
    0x20005306:"AUDITSDEV_FLUSH",
    0x40045307:"AUDITSDEV_GET_MAXDATA",
    0x40045364:"AUDITSDEV_GET_ALLSESSIONS",
    0x80045365:"AUDITSDEV_SET_ALLSESSIONS",
    0x400853c8:"AUDITSDEV_GET_INSERTS",
    0x400853c9:"AUDITSDEV_GET_READS",
    0x400853ca:"AUDITSDEV_GET_DROPS",
    0x4004741a:"TIOCGETD",
    0x8004741b:"TIOCSETD",
    0x40047400:"OTIOCGETD",
    0x80047401:"OTIOCSETD",
    0x20007402:"TIOCHPCL",
    0x40067408:"TIOCGETP",
    0x80067409:"TIOCSETP",
    0x8006740a:"TIOCSETN",
    0x80067411:"TIOCSETC",
    0x40067412:"TIOCGETC",
    0x8004747f:"TIOCLBIS",
    0x8004747e:"TIOCLBIC",
    0x8004747d:"TIOCLSET",
    0x4004747c:"TIOCLGET",
    0x80067475:"TIOCSLTC",
    0x40067474:"TIOCGLTC",
    0x20007462:"OTIOCCONS",
    0x40047463:"TIOCGSID",
    0x20006601:"FIOCLEX",
    0x20006602:"FIONCLEX",
    0x4004667f:"FIONREAD",
    0x8004667e:"FIONBIO",
    0x8004667d:"FIOASYNC",
    0x8004667c:"FIOSETOWN",
    0x4004667b:"FIOGETOWN",
    0x4004667a:"FIODTYPE",
    0x40047600:"VGETSTATE",
    0x80047601:"VSETSTATE",
    0x80047300:"SIOCSHIWAT",
    0x40047301:"SIOCGHIWAT",
    0x80047302:"SIOCSLOWAT",
    0x40047303:"SIOCGLOWAT",
    0x40047307:"SIOCATMARK",
    0x80047308:"SIOCSPGRP",
    0x40047309:"SIOCGPGRP",
    0x8020690c:"SIOCSIFADDR",
    0x8020690e:"SIOCSIFDSTADDR",
    0x80206910:"SIOCSIFFLAGS",
    0xc0206911:"SIOCGIFFLAGS",
    0x80206913:"SIOCSIFBRDADDR",
    0x80206916:"SIOCSIFNETMASK",
    0xc0206917:"SIOCGIFMETRIC",
    0x80206918:"SIOCSIFMETRIC",
    0x80206919:"SIOCDIFADDR",
    0x8040691a:"SIOCAIFADDR",
    0xc0206921:"SIOCGIFADDR",
    0xc0206922:"SIOCGIFDSTADDR",
    0xc0206923:"SIOCGIFBRDADDR",
    0xc00c6924:"SIOCGIFCONF",
    0xc0206925:"SIOCGIFNETMASK",
    0xc0206926:"SIOCAUTOADDR",
    0x80206927:"SIOCAUTONETMASK",
    0xc0206928:"SIOCARPIPLL",
    0x80206931:"SIOCADDMULTI",
    0x80206932:"SIOCDELMULTI",
    0xc0206933:"SIOCGIFMTU",
    0x80206934:"SIOCSIFMTU",
    0xc0206935:"SIOCGIFPHYS",
    0x80206936:"SIOCSIFPHYS",
    0xc0206937:"SIOCSIFMEDIA",
    0xc02c6938:"SIOCGIFMEDIA",
    0x80206939:"SIOCSIFGENERIC",
    0xc020693a:"SIOCGIFGENERIC",
    0xc010693b:"SIOCRSLVMULTI",
    0x8020693c:"SIOCSIFLLADDR",
    0xc331693d:"SIOCGIFSTATUS",
    0x8040693e:"SIOCSIFPHYADDR",
    0xc020693f:"SIOCGIFPSRCADDR",
    0xc0206940:"SIOCGIFPDSTADDR",
    0x80206941:"SIOCDIFPHYADDR",
    0xc0206944:"SIOCGIFDEVMTU",
    0x80206945:"SIOCSIFALTMTU",
    0xc0206948:"SIOCGIFALTMTU",
    0x80206946:"SIOCSIFBOND",
    0xc0206947:"SIOCGIFBOND",
    0xc02c6948:"SIOCGIFXMEDIA",
    0x8020695a:"SIOCSIFCAP",
    0xc020695b:"SIOCGIFCAP",
    0xc020695c:"SIOCSIFMANAGEMENT",
    0xc0206978:"SIOCIFCREATE",
    0x80206979:"SIOCIFDESTROY",
    0xc020697a:"SIOCIFCREATE2",
    0x8028697b:"SIOCSDRVSPEC",
    0xc028697b:"SIOCGDRVSPEC",
    0x8020697e:"SIOCSIFVLAN",
    0xc020697f:"SIOCGIFVLAN",
    0xc0106981:"SIOCIFGCLONERS",
    0xc020697c:"SIOCGIFASYNCMAP",
    0x8020697d:"SIOCSIFASYNCMAP",
    0xc0206982:"SIOCGIFMAC",
    0x80206983:"SIOCSIFMAC",
    0x80206986:"SIOCSIFKPI",
    0xc0206987:"SIOCGIFKPI",
    0xc0206988:"SIOCGIFWAKEFLAGS",
    0xc02069ad:"SIOCGIFFUNCTIONALTYPE",
    0x802069c4:"SIOCSIF6LOWPAN",
    0xc02069c5:"SIOCGIF6LOWPAN",
    0xc02069de:"SIOCGIFDIRECTLINK",
    0x8120690c:"SIOCSIFADDR_IN6",
    0xc1206921:"SIOCGIFADDR_IN6",
    0x8120690e:"SIOCSIFDSTADDR_IN6",
    0x81206916:"SIOCSIFNETMASK_IN6",
    0xc1206922:"SIOCGIFDSTADDR_IN6",
    0xc1206925:"SIOCGIFNETMASK_IN6",
    0x81206919:"SIOCDIFADDR_IN6",
    0x8080691a:"SIOCAIFADDR_IN6",
    0x8080693e:"SIOCSIFPHYADDR_IN6",
    0xc120693f:"SIOCGIFPSRCADDR_IN6",
    0xc1206940:"SIOCGIFPDSTADDR_IN6",
    0xc1206949:"SIOCGIFAFLAG_IN6",
    0xc030696c:"OSIOCGIFINFO_IN6",
    0xc030694c:"SIOCGIFINFO_IN6",
    0xc120694d:"SIOCSNDFLUSH_IN6",
    0xc038694e:"SIOCGNBRINFO_IN6",
    0xc120694f:"SIOCSPFXFLUSH_IN6",
    0xc1206950:"SIOCSRTRFLUSH_IN6",
    0xc1206951:"SIOCGIFALIFETIME_IN6",
    0xc1206952:"SIOCSIFALIFETIME_IN6",
    0xc1206953:"SIOCGIFSTAT_IN6",
    0xc1206954:"SIOCGIFSTAT_ICMP6",
    0xc0186955:"SIOCSDEFIFACE_IN6",
    0xc0186956:"SIOCGDEFIFACE_IN6",
    0xc0486957:"SIOCSIFINFO_FLAGS",
    0x81206958:"SIOCSSCOPE6",
    0xc1206959:"SIOCGSCOPE6",
    0xc120695a:"SIOCGSCOPE6DEF",
    0x80406964:"SIOCSIFPREFIX_IN6",
    0xc0406965:"SIOCGIFPREFIX_IN6",
    0x80406966:"SIOCDIFPREFIX_IN6",
    0x80606967:"SIOCAIFPREFIX_IN6",
    0x80606968:"SIOCCIFPREFIX_IN6",
    0x80606969:"SIOCSGIFPREFIX_IN6",
    0x8048756c:"SIOCAADDRCTL_POLICY",
    0x8048756d:"SIOCDADDRCTL_POLICY",
    0x40046501:"SIOCGKEVID",
    0x800c6502:"SIOCSKEVFILT",
    0x400c6503:"SIOCGKEVFILT",
    0xc0cc6504:"SIOCGKEVVENDOR",
    0x400473d1:"IOCTL_VM_SOCKETS_GET_LOCAL_CID",
    0x20006400:"DTRACEIOC",
    0x20006802:"DTRACEHIOC_REMOVE",
    0x80086804:"DTRACEHIOC_ADDDOF",
    0x20006415:"DKIOCEJECT",
    0x80186416:"DKIOCSYNCHRONIZE",
    0x8010641a:"DKIOCFORMAT",
    0xc010641a:"DKIOCGETFORMATCAPACITIES",
    0x40046418:"DKIOCGETBLOCKSIZE",
    0x40086419:"DKIOCGETBLOCKCOUNT",
    0x4080641c:"DKIOCGETFIRMWAREPATH",
    0x40046417:"DKIOCISFORMATTED",
    0x4004641d:"DKIOCISWRITABLE",
    0x2000641e:"DKIOCREQUESTIDLE",
    0x8010641f:"DKIOCUNMAP",
    0x40406420:"DKIOCCORESTORAGE",
    0x40086421:"DKIOCGETLOCATION",
    0x40086440:"DKIOCGETMAXBLOCKCOUNTREAD",
    0x40086441:"DKIOCGETMAXBLOCKCOUNTWRITE",
    0x40086446:"DKIOCGETMAXBYTECOUNTREAD",
    0x40086447:"DKIOCGETMAXBYTECOUNTWRITE",
    0x40086442:"DKIOCGETMAXSEGMENTCOUNTREAD",
    0x40086443:"DKIOCGETMAXSEGMENTCOUNTWRITE",
    0x40086444:"DKIOCGETMAXSEGMENTBYTECOUNTREAD",
    0x40086445:"DKIOCGETMAXSEGMENTBYTECOUNTWRITE",
    0x4008644a:"DKIOCGETMINSEGMENTALIGNMENTBYTECOUNT",
    0x4008644b:"DKIOCGETMAXSEGMENTADDRESSABLEBITCOUNT",
    0x4004644c:"DKIOCGETFEATURES",
    0x4004644d:"DKIOCGETPHYSICALBLOCKSIZE",
    0x4004644e:"DKIOCGETCOMMANDPOOLSIZE",
    0xc028644f:"DKIOCGETPROVISIONSTATUS",
    0x40206450:"DKIOCGETERRORDESCRIPTION",
    0x20006416:"DKIOCSYNCHRONIZECACHE",
    0x40047403:"TIOCMODG",
    0x80047404:"TIOCMODS",
    0x2000740d:"TIOCEXCL",
    0x2000740e:"TIOCNXCL",
    0x80047410:"TIOCFLUSH",
    0x40487413:"TIOCGETA",
    0x80487414:"TIOCSETA",
    0x80487415:"TIOCSETAW",
    0x80487416:"TIOCSETAF",
    0x4004741a:"TIOCGETD",
    0x8004741b:"TIOCSETD",
    0x20007481:"TIOCIXON",
    0x20007480:"TIOCIXOFF",
    0x2000747b:"TIOCSBRK",
    0x2000747a:"TIOCCBRK",
    0x20007479:"TIOCSDTR",
    0x20007478:"TIOCCDTR",
    0x40047477:"TIOCGPGRP",
    0x80047476:"TIOCSPGRP",
    0x40047473:"TIOCOUTQ",
    0x80017472:"TIOCSTI",
    0x20007471:"TIOCNOTTY",
    0x80047470:"TIOCPKT",
    0x2000746f:"TIOCSTOP",
    0x2000746e:"TIOCSTART",
    0x8004746d:"TIOCMSET",
    0x8004746c:"TIOCMBIS",
    0x8004746b:"TIOCMBIC",
    0x4004746a:"TIOCMGET",
    0x40087468:"TIOCGWINSZ",
    0x80087467:"TIOCSWINSZ",
    0x80047466:"TIOCUCNTL",
    0x20007465:"TIOCSTAT",
    0x20007463:"TIOCSCONS",
    0x80047462:"TIOCCONS",
    0x20007461:"TIOCSCTTY",
    0x80047460:"TIOCEXT",
    0x2000745f:"TIOCSIG",
    0x2000745e:"TIOCDRAIN",
    0x8004745b:"TIOCMSDTRWAIT",
    0x4004745a:"TIOCMGDTRWAIT",
    0x40107459:"TIOCTIMESTAMP",
    0x40107458:"TIOCDCDTIMESTAMP",
    0x80047457:"TIOCSDRAINWAIT",
    0x40047456:"TIOCGDRAINWAIT",
    0x20007455:"TIOCDSIMICROCODE",
    0x20007454:"TIOCPTYGRANT",
    0x40807453:"TIOCPTYGNAME",
    0x20007452:"TIOCPTYUNLK",
    0x40044e02:"CTLIOCGCOUNT",
    0xc0644e03:"CTLIOCGINFO",
    0x20006400:"FASTTRAPIOC",
}

def get_ioctl_name_by_value(value):
    g=chr(value>>8&0xff)

    if g=='u':
        # sys/ttycom.h
        return 'UIOCCMD(0x%x)'%(value&0xff)
    else: return g_ioctl_name_by_value.get(value)

##########################################################################
##########################################################################

g_fcntl_name_by_value={
    0:"F_DUPFD",
    1:"F_GETFD",
    2:"F_SETFD",
    3:"F_GETFL",
    4:"F_SETFL",
    5:"F_GETOWN",
    6:"F_SETOWN",
    7:"F_GETLK",
    8:"F_SETLK",
    9:"F_SETLKW",
    10:"F_SETLKWTIMEOUT",
    40:"F_FLUSH_DATA",
    41:"F_CHKCLEAN",
    42:"F_PREALLOCATE",
    43:"F_SETSIZE",
    44:"F_RDADVISE",
    45:"F_RDAHEAD",
    48:"F_NOCACHE",
    49:"F_LOG2PHYS",
    50:"F_GETPATH",
    51:"F_FULLFSYNC",
    52:"F_PATHPKG_CHECK",
    53:"F_FREEZE_FS",
    54:"F_THAW_FS",
    55:"F_GLOBAL_NOCACHE",
    59:"F_ADDSIGS",
    61:"F_ADDFILESIGS",
    62:"F_NODIRECT",
    63:"F_GETPROTECTIONCLASS",
    64:"F_SETPROTECTIONCLASS",
    65:"F_LOG2PHYS_EXT",
    66:"F_GETLKPID",
    70:"F_SETBACKINGSTORE",
    71:"F_GETPATH_MTMINFO",
    72:"F_GETCODEDIR",
    73:"F_SETNOSIGPIPE",
    74:"F_GETNOSIGPIPE",
    75:"F_TRANSCODEKEY",
    76:"F_SINGLE_WRITER",
    77:"F_GETPROTECTIONLEVEL",
    78:"F_FINDSIGS",
    83:"F_ADDFILESIGS_FOR_DYLD_SIM",
    85:"F_BARRIERFSYNC",
    90:"F_OFD_SETLK",
    91:"F_OFD_SETLKW",
    92:"F_OFD_GETLK",
    93:"F_OFD_SETLKWTIMEOUT",
    97:"F_ADDFILESIGS_RETURN",
    98:"F_CHECK_LV",
    99:"F_PUNCHHOLE",
    100:"F_TRIM_ACTIVE_FILE",
    101:"F_SPECULATIVE_READ",
    102:"F_GETPATH_NOFIRMLINK",
    103:"F_ADDFILESIGS_INFO",
    104:"F_ADDFILESUPPL",
    105:"F_GETSIGSINFO",
    106:"F_SETLEASE",
    107:"F_GETLEASE",
    110:"F_TRANSFEREXTENTS",
    111:"F_ATTRIBUTION_TAG",
    112:"F_NOCACHE_EXT",
    113:"F_ADDSIGS_MAIN_BINARY",
}
    
##########################################################################
##########################################################################

class Flags:
    def __init__(self,value):
        self.value=value
        self._names=[]

    def append(self,value): self._names.append(value)

    def flag(self,name,bit):
        if self.value&bit: self._names.append(name)

    def __str__(self): return '|'.join(self._names)

##########################################################################
##########################################################################

def get_open_flags_string(value):
    f=Flags(value)

    f.append(['O_RDONLY','O_WRONLY','O_RDWR','O_ACCMODE'][f.value&3])
    
    f.flag('O_NONBLOCK',0x00000004)
    f.flag('O_APPEND',0x00000008)
    f.flag('O_SHLOCK',0x00000010)
    f.flag('O_EXLOCK',0x00000020)
    f.flag('O_ASYNC',0x00000040)
    f.flag('O_FSYNC',0x80)
    f.flag('O_NOFOLLOW',0x00000100)
    f.flag('O_CREAT',0x00000200)
    f.flag('O_TRUNC',0x00000400)
    f.flag('O_EXCL',0x00000800)
    f.flag('O_RESOLVE_BENEATH',0x00001000)
    f.flag('O_UNIQUE',0x00002000)
    f.flag('O_EVTONLY',0x00008000)
    f.flag('O_NOCTTY',0x00020000)
    f.flag('O_DIRECTORY',0x00100000)
    f.flag('O_SYMLINK',0x00200000)
    f.flag('O_CLOEXEC',0x01000000)
    f.flag('O_NOFOLLOW_ANY',0x20000000)
    f.flag('O_EXEC',0x40000000)
    
    return str(f)

def get_f_setfl_string(value):
    f=Flags(value)

    f.flag('O_NONBLOCK',0x00000004)
    f.flag('O_APPEND',0x00000008)
    f.flag('O_ASYNC',0x00000040)

    return str(f)

##########################################################################
##########################################################################

g_fd_index_by_fun={
    'close':0,
    'close_nocancel':0,
    'getdirentries64':0,
    'fstatfs64':0,
    'lseek':0,
    'read_nocancel':0,
    'ioctl':0,
    'fcntl':0,
    'fstat64':0,
    'read':0,
    'write':0,
}

##########################################################################
##########################################################################

def symify(things,options):
    path_by_fd={}
    
    for thing_index,t in enumerate(things):
        if isinstance(t,Call):
            def check_args(s):
                assert len(s)<=len(t.args)
                for i in range(len(s)):
                    if s[i]=='i':
                        assert isinstance(t.args[i],Number),type(t.args[i])
                    elif s[i]=='s':
                        assert isinstance(t.args[i],str),type(t.args[i])
                    elif s[i]=='?': pass
                    else: assert False,s[i]

            def annotate_fd(arg_index):
                assert isinstance(t.args[arg_index],Number),type(t.args[arg_index])
                fd=t.args[arg_index].value
                if fd in path_by_fd:
                    t.args[0].string='"%s"'%path_by_fd[fd]

            # handle open: add path to the FDs list.
            if t.fun=='open' or t.fun=='open_nocancel':
                check_args('sii')
                if t.result.value>=0:
                    assert t.result.value not in path_by_fd,(thing_index+1,t.result.value)
                    path_by_fd[t.result.value]=t.args[0]

            # handle calls that have FD arguments.
            fd_args=g_fd_index_by_fun.get(t.fun)
            if fd_args is not None:
                if isinstance(fd_args,int): annotate_fd(fd_args)
                else: assert False,type(fd_args)

            # handle other types of argument.
            if t.fun=='ioctl':
                t.args[1].string=get_ioctl_name_by_value(t.args[1].value)
            elif t.fun=='open' or t.fun=='open_nocancel':
                t.args[1].string=get_open_flags_string(t.args[1].value)
            elif t.fun=='fcntl':
                t.args[1].string=g_fcntl_name_by_value.get(t.args[1].value)
                if t.args[1].string=='F_SETFL':
                    t.args[2].string=get_f_setfl_string(t.args[2].value)
                
            # handle close: remove path from the FDs list.
            if t.fun=='close' or t.fun=='close_nocancel':
                check_args('i')
                if t.args[0].value in path_by_fd:
                    del path_by_fd[t.args[0].value]
                fd=annotate_fd(0)
                if fd is not None: del path_by_fd[fd]

##########################################################################
##########################################################################

def main2(options):
    global g_verbose;g_verbose=options.verbose

    paths=set()
    for include_path in options.include_paths:
        for dirpath,dirnames,filenames in os.walk(include_path):
            for filename in filenames:
                if fnmatch.fnmatch(filename,'*.h'):
                    path=os.path.abspath(os.path.join(dirpath,filename))
                    paths.add(path)

    global g_all_header_paths
    g_all_header_paths=list(paths)

    lines=None
    def input(f):
        nonlocal lines
        lines=[line.rstrip() for line in f.readlines()]
    if options.input_path=='-': input(sys.stdin)
    else:
        with open(options.input_path,'rt') as f: input(f)

    things=[]
    line_idx=0
    extra_columns=set()
    while line_idx<len(lines):
        line=lines[line_idx]
        line_idx+=1

        # the ^C case isn't very nice, but I've had it crop up.
        if (line.startswith('dtrace:') or
            (line.startswith('Waiting for ') and
             line.endswith(', hit Ctrl-C to stop waiting...')) or
            line=='^C' or
            line==''):
            things.append(line)
        elif line.endswith("SYSCALL(args) \t\t = return"):
            parts=line.split()
            assert parts[-1]=='return'
            assert parts[-2]=='='
            assert parts[-3]=='SYSCALL(args)'
            extra_columns=set(parts[:-3])
        elif line=='             0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f  0123456789abcdef':
            # hex dump - append as strings
            things.append(line)
            while line_idx<len(lines) and lines[line_idx]!='':
                things.append(lines[line_idx])
                line_idx+=1

            if line_idx<len(lines):
                # and copy the terminator too
                things.append(lines[line_idx])
                line_idx+=1
        else:
            try: things.append(parse_call(line,extra_columns))
            except ParseException as pe:
                if len(pe.args)>1: column=pe.args[1]
                else: column=None

                if column is None:
                    print('    %s'%line)
                else:
                    begin=max(column-40,0)
                    end=min(len(line),column+40)
                    region=line[begin:end]

                    print('    %s'%line[begin:end])
                    print('    %s^'%((column-begin)*' '))

                sys.stderr.write('%s:%d:'%(options.input_path,line_idx))
                if column is not None: sys.stderr.write('%d:'%column)

                sys.stderr.write('%s\n'%pe.args[0])
                sys.exit(1)

    symify(things,options)

    def output(f):
        def write_args(args):
            for arg_idx,arg in enumerate(args):
                if arg_idx>0: f.write(', ')
                if isinstance(arg,Number): f.write(str(arg))
                elif isinstance(arg,Symbol): f.write(arg.name)
                elif isinstance(arg,list):
                    f.write('[')
                    write_args(arg)
                    for _ in range(len(arg),6): f.write(', 0')
                    f.write('] (%d)'%len(arg))
                elif isinstance(arg,str):
                    f.write('"')
                    f.write(arg)
                    f.write('"')
                else: assert False,type(arg)
        
        for i,thing in enumerate(things):
            if isinstance(thing,str): f.write(thing)
            elif isinstance(thing,Call):
                f.write('%s('%thing.fun)
                write_args(thing.args)
                f.write(')\t\t = ')

                if isinstance(thing.result,str):
                    f.write(thing.result)
                elif isinstance(thing.result,Number):
                    f.write(str(thing.result))
                else: assert False,type(thing.result)

                if thing.errno is not None:
                    f.write(' ')
                    if thing.errno==0: f.write('0')
                    else: f.write('Err#%d'%thing.errno)
                
            else: assert False
            f.write('\n')

    if options.output_path is None: output(sys.stdout)
    else:
        with open(options.output_path,'wt') as f: output(f)

##########################################################################
##########################################################################

def main(argv):
    parser=argparse.ArgumentParser()
    parser.add_argument('-v','--verbose',action='store_true',help='''be more verbose''')
    parser.add_argument('-o','--output',metavar='FILE',dest='output_path',default=None,help='''write output to %(metavar)s (stdout if not specified)''')
    parser.add_argument('-I',metavar='PATH',dest='include_paths',default=[],action='append',help='''add %(metavar)s to list of paths to search for includes''')
    parser.add_argument('input_path',metavar='FILE',help='''read input from %(metavar)s. Specify - for stdin''')
    main2(parser.parse_args(argv))
    
##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv[1:])
