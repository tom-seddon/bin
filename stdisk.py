#!/usr/bin/python3
import sys,os,os.path,argparse,collections,time

##########################################################################
##########################################################################

g_verbose=False

def pv(x):
    if g_verbose:
        sys.stdout.write(x)
        sys.stdout.flush()

##########################################################################
##########################################################################

def fatal(x):
    sys.stderr.write('FATAL: %s\n'%x)
    sys.exit(1)

##########################################################################
##########################################################################

def load(path):
    try:
        with open(path,'rb') as f:
            data=f.read()
            pv('Loaded: %s (%d bytes)\n'%(path,len(data)))
            return data
    except IOError as e: fatal(e)

##########################################################################
##########################################################################

# https://info-coach.fr/atari/software/FD-Soft.php

DirEntry=collections.namedtuple('DirEntry','path name attrib time scluster size')

def info_cmd(options):
    data=load(options.path)

    if len(data)%512!=0:
        fatal('not a multiple of sector length: %s'%(options.path))

    def db(sector,offset):
        assert offset>=0 and offset<512
        i=sector*512+offset
        return 0 if i>=len(data) else data[i]

    def dw(sector,offset):
        h=db(sector,offset+0)
        l=db(sector,offset+1)
        return h*256+l

    def dwle(sector,offset):
        l=db(sector,offset+0)
        h=db(sector,offset+1)
        return h*256+l

    def dlle(sector,offset):
        b0=db(sector,offset+0)
        b1=db(sector,offset+1)
        b2=db(sector,offset+2)
        b3=db(sector,offset+3)

        return b0|b1<<8|b2<<16|b3<<24

    def dname(sector,offset):
        name=''
        for i in range(8): name+=chr(db(sector,offset+i))
        name=name.rstrip()

        ext=''
        for i in range(3): ext+=chr(db(sector,offset+8+i))
        ext=ext.rstrip()

        if ext!='': name+='.'+ext
        
        return name

    empty_sector=bytes(512)

    def dsector(sector):
        i=sector*512
        if i>=len(data): return empty_sector
        else: return data[i:i+512]

    def dsectors(sector,num_sectors):
        result=bytes()
        for i in range(num_sectors): result+=dsector(sector+i)
        return result
    
    print('Boot Sector')
    print()

    print('  Jump instruction: %02x %02x'%(db(0,0),db(0,1)))

    name=''
    for i in range(6): name+=chr(db(0,2+i))
    print('  Name: %s'%name)

    print('  Serial: %02x %02x %02x'%(db(0,8),db(0,9),db(0,10)))

    bps=dwle(0,0xb)
    spc=db(0,0xd)
    ressec=dwle(0,0xe)
    nfats=db(0,0x10)
    ndirs=dwle(0,0x11)
    nsects=dwle(0,0x13)
    media=db(0,0x15)
    spf=dwle(0,0x16)
    spt=dwle(0,0x18)
    nheads=dwle(0,0x1a)
    nhid=dwle(0,0x1c)
    execflag=dw(0,0x1e)
    ldmode=dw(0,0x20)
    ssect=dwle(0,0x22)
    sectcnt=dwle(0,0x24)
    ldaaddr=dwle(0,0x26)
    fatbuf=dwle(0,0x2a)
    fname=dname(0,0x2e)
    reserved=dw(0,0x39)

    media_types={
        0xf8:'3.5" 1 side x 80 tracks x 9 sectors',
    }

    def sector_str(n):
        s=n%spt
        h=(n//spt)%nheads
        t=(n//spt//nheads)

        offset=n*bps
        
        return '%d (0x%x) (H%d T%d S%d) (+0x%x)'%(n,n,h,t,s,offset)
    
    print('  Bytes/sector: %d (0x%04x)'%(bps,bps))
    print('  Sectors/cluster: %d (0x%02x)'%(spc,spc))
    print('  Num reserved sectors: %d'%(ressec))
    print('  Num FATs: %d'%(nfats))
    print('  Max root entries: %d'%(ndirs))
    root_dir_size_bytes=ndirs*32
    print('    (Root dir size: %d (0x%x))'%(root_dir_size_bytes,root_dir_size_bytes))
    if root_dir_size_bytes%bps!=0:
        print('    WARNING: root dir size not a multiple of sector size')
    print('  Total sectors: %d (0x%04x)'%(nsects,nsects))
    print('  Media descriptor: %d (0x%02x)'%(media,media))
    if media in media_types: print('    %s'%media_types[media])
    print('  Sectors/FAT: %d (0x%02x)'%(spf,spf))
    print('  Sectors/track: %d'%(spt))
    print('  Heads: %d'%(nheads))
    print('  Num hidden sectors: %d'%(nhid))
    print('  cmdload: 0x%04x'%execflag)
    print('  load mode: %s'%('fname' if ldmode==0 else 'sectors'))
    print('  start sector: %s'%sector_str(ssect))
    print('  num sectors: %d'%(sectcnt))
    print('  load address: 0x%04x'%ldaaddr)
    print('  FAT buffer: 0x%04x'%fatbuf)
    print('  Boot fname: %s'%fname)

    print('  Checksum offset: 0x%04x'%dw(0,510))
    
    checksum=0
    for i in range(512,2): checksum+=dw(0,i)
    print('  Checksum: $%04x'%checksum)

    print()
    print('Disk Layout')
    print()
    
    fat0_sector=ressec
    fat1_sector=fat0_sector+spf
    root_sector=fat1_sector+spf
    print('  FAT0 sector: %s'%sector_str(fat0_sector))
    print('  FAT1 sector: %s'%sector_str(fat1_sector))

    fat0_data=dsectors(fat0_sector,spf)
    fat1_data=dsectors(fat1_sector,spf)
    if fat0_data==fat1_data: print('  FATs match')
    else: print('  WARNING: FATs do not match')

    fat0_word0=fat0_data[0]|fat0_data[1]<<8
    print('  FAT entry 0: $%03x'%(fat0_word0&0xfff))
    print('  FAT entry 1: $%03x'%(fat0_word0>>12&0xfff))
    
    print('  Root dir sector: %s'%sector_str(root_sector))

    first_cluster_sector=root_sector+(root_dir_size_bytes//(bps*spc))

    print()
    print('Files')
    print()

    def file_data(scluster):
        data=bytes()
        cluster=scluster
        while cluster<0xff0:
            sector=first_cluster_sector+cluster*spc
            print('sector=%d offset=0x%04x'%(sector,sector*512))
            # print('cluster=%d (+0x%x)'%(cluster,
            #                             (first_cluster_sector*spc)*bps))
            for i in range(spc): data+=dsector(sector+i)
            
            fat_offset=(cluster>>1)*3
            fat_pair=(fat0_data[fat_offset]|
                      fat0_data[fat_offset+1]<<8|
                      fat0_data[fat_offset+2]<<16)
            if cluster&1: fat_pair>>=12
            else: fat_pair&=0xfff

            cluster=fat_pair

        return data

    def recurse(dir,path,files):
        print('Processing: %s'%path)
        subdirs=[]
        offset=0
        while offset<len(dir):
            if dir[offset+0]==0:
                # end of table
                break
            elif dir[offset+0]==0xe5:
                # deleted entry
                offset+=32
                continue

            name=''
            for i in range(8): name+=chr(dir[offset+0+i])
            name=name.rstrip()

            ext=''
            for i in range(3): ext+=chr(dir[offset+8+i])
            ext=ext.rstrip()

            if ext!='': name+='.'+ext

            ftime=dir[offset+22]|dir[offset+23]<<8
            fdate=dir[offset+24]|dir[offset+25]<<8

            time_struct=time.struct_time(((fdate>>9&127)+1980, # tm_year
                                          fdate>>5&15,         # tm_mon
                                          fdate&31,            # tm_day
                                          ftime>>11&31,        # tm_hour
                                          ftime>>5&63,         # tm_min
                                          (ftime&31)*0,        # tm_sec
                                          0,                   # tm_wday
                                          1,                   # tm_yday
                                          -1))                 # tm_isdst

            entry=DirEntry(path=path,
                           name=name,
                           attrib=dir[offset+11],
                           time=time.mktime(time_struct),
                           scluster=dir[offset+26]|dir[offset+27]<<8,
                           size=(dir[offset+28]|
                                 dir[offset+29]<<8|
                                 dir[offset+30]<<16|
                                 dir[offset+31]<<24))

            if entry.attrib&0x10:
                if entry.name=='.' or entry.name=='..': pass
                else: subdirs.append(entry)
            elif entry.attrib&0x08: pass
            else: files.append(entry)

            offset+=32

        for subdir in subdirs:
            print(subdir)
            recurse(file_data(subdir.scluster),
                    os.path.join(path,subdir.name),
                    files)

    files=[]
    recurse(dsectors(root_sector,root_dir_size_bytes//bps),
            '',
            files)

    print(files)

##########################################################################
##########################################################################

def main2(options):
    global g_verbose
    g_verbose=options.verbose

    options.fun(options)

##########################################################################
##########################################################################

def main(argv):
    parser=argparse.ArgumentParser()
    parser.add_argument('-v','--verbose',action='store_true',help='be more verbose')
    parser.set_defaults(fun=None)

    subparsers=parser.add_subparsers()

    info_parser=subparsers.add_parser('info',help='''show disk info''')
    info_parser.add_argument('path',metavar='FILE',help='''load disk from %(metavar)s''')
    info_parser.set_defaults(fun=info_cmd)

    options=parser.parse_args(argv)
    if options.fun is None:
        parser.print_help()
        sys.exit(1)

    main2(options)
    
##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv[1:])
