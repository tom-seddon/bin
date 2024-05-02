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

BPB=collections.namedtuple('BPB','bps spc ressec nfats ndirs nsects media spf spt nheads nhid')
Bootable=collections.namedtuple('Bootable','execflag ldmode ssect sectcnt ldaaddr fatbuf fname')
# DirEntry=collections.namedtuple('DirEntry','path name attrib time scluster size')



##########################################################################
##########################################################################

def wordb(d,i): return d[i+0]<<8|d[i+1]
def wordl(d,i): return d[i+0]|d[i+1]<<8
def longl(d,i): return d[i+0]|d[i+1]<<8|d[i+2]<<16|d[i+3]<<24
def longb(d,i): return d[i+0]<<24|d[i+1]<<16|d[i+2]<<8|d[i+3]
def fname(d,i):
    name=''
    for j in range(8): name+=chr(d[i+j])
    name=name.rstrip()

    ext=''
    for j in range(3): ext+=chr(d[i+8+j])
    ext=ext.rstrip()

    if ext=='': return name
    else: return name+'.'+ext

##########################################################################
##########################################################################

class File:
    def __init__(self,parent,data):
        assert len(data)>=32

        self.name=fname(data,0)
        self.parent=parent
        self.path=os.path.join(self.parent,self.name)

        ftime=wordl(data,22)
        fdate=wordl(data,24)
        self.time=time.struct_time(((fdate>>9&127)+1980, # tm_year
                                    fdate>>5&15,         # tm_mon
                                    fdate&31,            # tm_day
                                    ftime>>11&31,        # tm_hour
                                    ftime>>5&63,         # tm_min
                                    (ftime&31)*0,        # tm_sec
                                    0,                   # tm_wday
                                    1,                   # tm_yday
                                    -1))                 # tm_isdst
        self.attrib=data[11]
        self.scluster=wordl(data,26)
        self.size=longl(data,28)
        self.data=None

    @property
    def is_readonly(self): return self._attr(0x01)

    @property
    def is_hidden(self): return self._attr(0x02)

    @property
    def is_system(self): return self._attr(0x04)

    @property
    def is_label(self): return self._attr(0x08)

    @property
    def is_dir(self): return self._attr(0x10)

    def _attr(self,mask): return (self.attrib&mask)!=0

##########################################################################
##########################################################################

class Disk:
    def __init__(self,data):
        self._data=data

        if len(self._data)<512: raise RuntimeError('disk image too small for boot sector')

        self._oem=self._data[2:8]
        self._serial=longl(self._data,8)
        self._bpb=BPB(bps=wordl(self._data,0xb),
                      spc=self._data[0xd],
                      ressec=wordl(self._data,0xe),
                      nfats=self._data[0x10],
                      ndirs=wordl(self._data,0x11),
                      nsects=wordl(self._data,0x13),
                      media=self._data[0x15],
                      spf=wordl(self._data,0x16),
                      spt=wordl(self._data,0x18),
                      nheads=wordl(self._data,0x1a),
                      nhid=wordl(self._data,0x1c))
        sum=0
        for i in range(0,512,2): sum+=wordb(self._data,i)
        if self._oem==b'Loader' and sum==0x1234:
            self._bootable=Bootable(execflag=wordb(self._data,0x1e),
                                    ldmode=wordb(self._data,0x20),
                                    ssect=wordl(self._data,0x22),
                                    sectcnt=wordl(self._data,0x24),
                                    ldaaddr=wordl(self._data,0x26),
                                    # 0x28?
                                    fatbuf=wordl(self._data,0x2a),
                                    fname=fname(self._data,0x2e))
        else: self._bootable=None

        if self._bpb.bps!=512:
            raise RuntimeError('disk image has unsupported bytes/sector: %d'%(self._bpb.bps))

        root_dir_size_bytes=self._bpb.ndirs*32
        if root_dir_size_bytes%self._bpb.bps!=0:
            raise RuntimeError('root dir size (%d; 0x%x) not a multiple of sector size (%d; 0x%x)'%(root_dir_size_bytes,root_dir_size_bytes,self._bpb.bps,self._bpb.bps))
        self._root_dir_size_sectors=root_dir_size_bytes//self._bpb.bps

        if (self._bpb.ressec+self._bpb.nfats*self._bpb.spf)*self._bpb.bps>len(self._data):
            raise RuntimeError('disk image too small for FATs')

        self._fats=[]
        for i in range(self._bpb.nfats):
            begin=self._bpb.ressec+i*self._bpb.spf
            end=begin+self._bpb.spf
            self._fats.append(self._data[begin*self._bpb.bps:
                                         end*self._bpb.bps])

        self._fat=[]
        for i in range(0,len(self._fats[0])//3*3,3):
            value=(self._fats[0][i]|
                   self._fats[0][i+1]<<8|
                   self._fats[0][i+2]<<16)
            self._fat.append(value&0xfff)
            self._fat.append(value>>12)

        # print(self._fat)
        # print(len(self._fat))

        self._root_dir_sector=self._bpb.ressec+self._bpb.nfats*self._bpb.spf
        self._first_cluster_sector=self._root_dir_sector+self._root_dir_size_sectors
        # first usable cluster must be index 2...
        self._first_cluster_sector-=2*self._bpb.spc
        #print(f'fcs: {self._first_cluster_sector}')

        self._files=None

    @property
    def bpb(self): return self._bpb

    @property
    def bootable(self): return self._bootable

    @property
    def fats(self): return self._fats

    # def fat_value(self,index):
    #     print(index)
    #     offset=(index>>1)*3
    #     value=(self._fats[0][offset]|
    #            self._fats[0][offset+1]<<8|
    #            self._fats[0][offset+2]<<16)
    #     if index&1: return value>>12
    #     else: return value&0xfff

    def root_dir_data(self):
        begin=self._bpb.ressec+self._bpb.nfats*self._bpb.spf
        end=begin+self._root_dir_size_sectors
        return self._data[begin*self._bpb.bps:end*self._bpb.bps]

    def file_clusters(self,scluster):
        seen_clusters=set()
        clusters=[]
        cluster=scluster
        while cluster<0xff0:
            if cluster in seen_clusters: raise RuntimeError('loop in FAT')
            seen_clusters.add(cluster)
            clusters.append(cluster)
            cluster=self._fat[cluster]

        return clusters

    def _file_data(self,scluster):
        data=bytes()

        for cluster in self.file_clusters(scluster):
            sector=self._first_cluster_sector+cluster*self._bpb.spc
            begin=sector*self._bpb.bps
            end=begin+self._bpb.spc*self._bpb.bps
            data+=self._data[begin:end]

        return data
        
        # cluster=scluster
        # while cluster<0xff0:
        #     sector=self._first_cluster_sector+cluster*self._bpb.spc
        #     begin=sector*self._bpb.bps
        #     end=begin+self._bpb.spc*self._bpb.bps
        #     #print(f'  cluster: {cluster}; range={hex(begin)} to {hex(end)}')
        #     data+=self._data[begin:end]

        #     cluster=self._fat[cluster]

        # return data

    @property
    def files(self):
        if self._files is None:
            files=[]
            
            def recurse(dir,path):
                subdirs=[]
                offset=0
                index=len(files)
                
                for offset in range(0,len(dir),32):
                    if dir[offset+0]==0: break # end of table
                    elif dir[offset+0]==0xe5: continue # deleted entry

                    file=File(path,dir[offset+0:offset+32])
                    if file.name=='.' or file.name=='..': continue

                    if not file.is_label:
                        file.data=self._file_data(file.scluster)

                        if not file.is_dir:
                            file.data=file.data[:file.size]

                    files.append(file)

                for i in range(index,len(files)):
                    if files[i].is_dir:
                        recurse(files[i].data,
                                os.path.join(path,files[i].name))

            recurse(self.root_dir_data(),'')
            self._files=files

        return self._files

##########################################################################
##########################################################################

# https://info-coach.fr/atari/software/FD-Soft.php

def info2_cmd(options):
    disk=Disk(load(options.path))

    def sector_str(n):
        s=n%disk.bpb.spt
        h=(n//disk.bpb.spt)%disk.bpb.nheads
        t=(n//disk.bpb.spt//disk.bpb.nheads)

        offset=n*disk.bpb.bps
        
        return '%d (0x%x) (H%d T%d S%d) (+0x%x)'%(n,n,h,t,s,offset)

    print('BPB')
    print()
    print(f'  Bytes/sector: {disk.bpb.bps} ({hex(disk.bpb.bps)})')
    print(f'  Sectors/cluster: {disk.bpb.spc} ({hex(disk.bpb.spc)})')
    print(f'  Num reserved sectors: {disk.bpb.ressec}')
    print(f'  Num FATs: {disk.bpb.nfats}')
    print(f'  Max root entries: {disk.bpb.ndirs}')
    print(f'  Total sectors: {disk.bpb.nsects} ({hex(disk.bpb.nsects)})')
    print(f'  Media descriptor: {disk.bpb.media} ({hex(disk.bpb.media)})')
    print(f'  Sectors/FAT: {disk.bpb.spf} ({hex(disk.bpb.spf)})')
    print(f'  Sectors/track: {disk.bpb.spt}')
    print(f'  Heads: {disk.bpb.nheads}')
    print(f'  Num hidden sectors: {disk.bpb.nhid}')
    print()

    print('Bootable')
    print()
    if disk.bootable is None: print('  Boot sector not bootable')
    else:
        print(f'  execflag: {hex(disk.bootable.execflag)}')
        print(f'  ldmode: {hex(disk.bootable.ldmode)}')
        if disk.bootable.ldmode!=0:
            print(f'  ssect: {sector_str(disk.bootable.ssect)}')
            print(f'  sectcnt: {disk.bootable.sectcnt}')
        else:
            print(f'  ldaaddr: {hex(disk.bootable.ldaaddr)}')
            print(f'  fatbuf: {hex(disk.bootable.fatbuf)}')
            print(f'  fname: {disk.bootable.fname})')
    print()

    print('FAT/Root dir')
    print()
    fats_match=True
    for i in range(disk.bpb.nfats):
        print(f'  FAT %d sector: %s'%(i,disk.bpb.ressec+i*disk.bpb.spf))
        if disk.fats[i]!=disk.fats[0]: fats_match=False

    if fats_match: print('  All FATs match')
    else: print('  WARNING: FATs do not all match')

    print(f'  Root dir sector: {sector_str(disk._root_dir_sector)}')
    print(f'  Cluster 0 sector: {sector_str(disk._first_cluster_sector)}')

##########################################################################
##########################################################################

def files_cmd(options):
    disk=Disk(load(options.path))

    for file in disk.files:
        if file.is_dir: size_str='<<DIR>>'
        elif file.is_label: size_str='<<LABEL>>'
        else: size_str='{:,}'.format(file.size)

        # 
        time_str=time.strftime('%Y-%m-%d %H:%M:%S',file.time)

        attr_str=(('R' if file.is_readonly else '_')+
                  ('H' if file.is_hidden else '_')+
                  ('S' if file.is_system else '_'))
        
        print('%13s  %-19s  %-3s  %s'%(size_str,
                                       time_str,
                                       attr_str,
                                       file.path))

##########################################################################
##########################################################################

def extract_cmd(options):
    disk=Disk(load(options.src_path))

    if options.dest_path is not None:
        for file in disk.files:
            file_path=file.path
            if options.tolower: file_path=file_path.lower()
            dest_path=os.path.join(options.dest_path,file_path)
            if file.is_label:
                pass
            elif file.is_dir:
                if not os.path.isdir(dest_path):
                    os.makedirs(dest_path)
            else:
                with open(dest_path,'wb') as f: f.write(file.data)    

##########################################################################
##########################################################################

def chkdsk_cmd(options):
    disk=Disk(load(options.path))

    def warn(msg): sys.stderr.write(f'{msg}\n')

    # check file attributes.
    for file in disk.files:
        if (file.attrib&~0x3f)!=0:
            warn(f'file has invalid attributes (0x%x): %s'%(file.attrib,
                                                            file.path))

    # check labels.
    found_label=False
    for file in disk.files:
        if file.is_label:
            if file.parent=='':
                if found_label: warn('disk has multiple labels')
                else: found_label=True
            else:
                warn(f'found label outside root dir: {file.path}')

    cluster_map={}
    for file in disk.files:
        for cluster in disk.file_clusters(file.scluster):
            cluster_map.setdefault(cluster,[]).append(file)

    for cluster,files in cluster_map.items():
        if len(files)>1:
            warn('cluster %d (0x%x) is multiply linked:'%(cluster,cluster))
            for file in files: print('  %s'%file.path)

    # # validate FAT.
    # num_clusters=disk.bpb.nsects-(disk.bpb.ressec+
    #                               disk.bpb.nfats*disk.bpb.spf+
    #                               disk._root_dir_size_sectors)
    
    # for fat_idx,fat in enumerate(disk._fats):
    #     for cluster_idx,cluster in enumerate(fat):
    #         if (cluster==0 or
    #             cluster==1 or
    #             cluster>=0xff0 and cluster<=0xff7):
    #             warn('FAT %d cluster %d: invalid value: %d (0x%x)'%
    #                  (fat_idx,cluster_idx,cluster,cluster))
    #         elif cluster>=num_clusters+2:
    #             warn('FAT %d cluster %d: out of range value: %d (0x%x)'%
    #                  (fat_idx,cluster_idx,cluster,cluster))
                
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

    chkdsk_parser=subparsers.add_parser('chkdsk',help='''validate disk''')
    chkdsk_parser.add_argument('path',metavar='FILE',help='''load disk from %(metavar)s''')
    chkdsk_parser.set_defaults(fun=chkdsk_cmd)

    extract_parser=subparsers.add_parser('extract',help='''extract files into folder''')
    extract_parser.add_argument('-o',dest='dest_path',metavar='FOLDER',help='''write file(s) to %(metavar)s, creating folder structure as necessary''')
    extract_parser.add_argument('--tolower',action='store_true',help='''make all file names lower case''')
    extract_parser.add_argument('src_path',metavar='FILE',help='''load disk from %(metavar)s''')
    extract_parser.set_defaults(fun=extract_cmd)

    files_parser=subparsers.add_parser('files',help='''list all files on disk''')
    files_parser.add_argument('path',metavar='FILE',help='''load disk from %(metavar)s''')
    files_parser.set_defaults(fun=files_cmd)

    info_parser=subparsers.add_parser('info',help='''show disk info''')
    info_parser.add_argument('path',metavar='FILE',help='''load disk from %(metavar)s''')
    info_parser.set_defaults(fun=info2_cmd)

    options=parser.parse_args(argv)
    if options.fun is None:
        parser.print_help()
        sys.exit(1)

    main2(options)
    
##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv[1:])
