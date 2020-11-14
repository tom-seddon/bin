#!/usr/bin/python
import sys,os,os.path,argparse,stat,math,collections,uuid,numbers,struct

##########################################################################
##########################################################################

g_verbose=False

def set_verbose(value):
    if isinstance(value,bool): g_verbose=1
    elif isinstance(value,int): g_verbose=value
    else: raise TypeError

def pvn(level,x):
    if g_verbose>=level:
        sys.stdout.write(x)
        sys.stdout.flush()

def pv(x): pvn(1,x)

def dumpv(data,name=None):
    if not g_verbose: return
    
    def val(x):
        if isinstance(x,str):
            assert len(x)==1
            return ord(x)
        elif isinstance(x,numbers.Number): return int(x)
        else: assert False

    num_columns=16
    for row_offset in range(0,len(data)+num_columns-1,num_columns):
        row=[val(x) for x in data[row_offset:row_offset+num_columns]]

        if name is None: line=''
        else:
            if row_offset==0: line='%s: '%name
            else: line=' '*(len(name)+2)

        line+='%08x:'%row_offset
        
        for column_idx in range(0,num_columns):
            if column_idx<len(row): line+=' %02x'%row[column_idx]
            else: line+='   '

        line+='  '

        for column_idx in range(0,num_columns):
            if column_idx<len(row):
                c=row[column_idx]
                if c>=32 and c<=126: line+=chr(c)
                else: line+='.'
            else: line+=' '

        print line
        
# def get2(xs,i): return xs[i+0]<<0|xs[i+1]<<8
def get4(xs,i): return struct.unpack('<I',xs[i:i+4])[0] # return xs[i+0]<<0|xs[i+1]<<8|xs[i+2]<<16|xs[i+3]<<24
# def str_bytes(s): return [ord(c) for c in s]

##########################################################################
##########################################################################

class PDBError(Exception):
    def __init__(self,path,message):
        self._pdb_path=path
        self._pdb_message=message
        BaseException.__init__(self,'%s: %s'%(path,message))

    @property
    def pdb_path(self): return self._pdb_path

    @property
    def pdb_message(self): return self._pdb_message

##########################################################################
##########################################################################

# names of stuff in the PDB file as per
# https://llvm.org/docs/PDB/MsfFile.html, even when the style is
# inconsistent.

class MSFReader:
    def __init__(self,
                 path):
        self._path=path

    def __enter__(self):
        st=os.stat(self._path)
        self._f=open(self._path,'rb')

        header=self._read(0x20+6*64)
        if header[0:32]!="Microsoft C/C++ MSF 7.00\r\n\x1a\x44\x53\x00\x00\x00":
            self._fatal('no MSF header')

        # header_fields=struct.unpack('<IIIIII',header[32:32+24])

        # self._BlockSize=header_fields[0]
        # self._NumBlocks=header_fields[2]
        # self._NumDirectoryBytes=header_fields[3]
        # self._BlockMapAddr=header_fields[5]

        self._BlockSize=get4(header,32+0)
        self._NumBlocks=get4(header,32+8)

        # pv('BlockSize=%d NumBlocks=%d\n'%(self._BlockSize,self._NumBlocks))
        
        expected_size=self._NumBlocks*self._BlockSize
        if expected_size!=st.st_size:
            fatal('bad PDB file size: expected %d bytes, got %d bytes'%(expected,st.st_size))

        self._NumDirectoryBytes=get4(header,32+12)
        self._BlockMapAddr=get4(header,32+20)

        # size of block map, in blocks
        block_map_size_blocks=self._num_blocks(self._NumDirectoryBytes)

        # the block map is one block, with 1 4-byte entry per block;
        # so, the entire block map must be small enough to fit.
        if block_map_size_blocks*4>=self._BlockSize: self._fatal('stream directory doesn\'t fit in a block')

        pv('NumBlocks=%d\n'%self._NumBlocks)
        pv('BlockSize=%d\n'%self._BlockSize)
        pv('NumDirectoryBytes=%d\n'%self._NumDirectoryBytes)
        pv('BlockMapAddr=%d\n'%self._BlockMapAddr)
        pv('block_map_size_blocks=%d\n'%block_map_size_blocks)

        block_map=self._read_block(self._BlockMapAddr)

        stream_directory=''
        for i in range(block_map_size_blocks):
            block_index=get4(block_map,i*4)
            stream_directory+=self._read_block(block_index)

        offset=0
        
        NumStreams,=struct.unpack('<I',stream_directory[0:4])
        offset+=4

        pv('NumStreams=%d\n'%NumStreams)

        self._StreamSizes=[]
        for i in range(NumStreams):
            self._StreamSizes.append(get4(stream_directory,offset))
            offset+=4

        assert offset==4+NumStreams*4

        # n=sum(self._StreamSizes)
        # print n
        
        # for i in range(len(self._StreamSizes)): pv('StreamSizes[%d]=%d\n'%(i,self._StreamSizes[i]))

        self._StreamBlocks=[]
        for stream_index,stream_size in enumerate(self._StreamSizes):
            num_blocks=self._num_blocks(stream_size)
            self._StreamBlocks.append([])
            pvn(2,'@+%d Stream[%d]: StreamSize=%d (num_blocks=%d):'%(offset,stream_index,stream_size,num_blocks))
            for i in range(num_blocks):
                block=get4(stream_directory,offset)
                pvn(3,' %d'%block)
                self._StreamBlocks[-1].append(block)
                offset+=4
            pvn(2,'\n')

        #assert offset==self._NumDirectoryBytes,(offset,self._NumDirectoryBytes)

        pv('Stream Directory=%d bytes\n'%len(stream_directory))
        
        return self

    def __exit__(self,exc_type,exc_value,traceback):
        self._f.close()
        del self._f
        return False

    def _fatal(self,msg): raise PDBError(self._path,msg)

    def _read(self,n):
        pos=self._f.tell()
        data=self._f.read(n)
        if len(data)!=n: self._fatal('failed to read %d byte(s) from +0x%x'%(n,pos))

        return data

    def _read_block(self,index):
        if index>=self._NumBlocks: self._fatal('invalid block index: %d'%index)
        self._f.seek(index*self._BlockSize)
        return self._read(self._BlockSize)

    def read_stream_data(self,stream_index,stream_offset,num_bytes):
        if stream_index>=len(self._StreamSizes): fatal('invalid stream index: %d'%(stream_index))
        if stream_offset+num_bytes>self._StreamSizes[stream_index]:
            fatal('invalid read from stream %d (%d bytes): end=%d'%
                  (stream_index,
                   self._StreamSizes[stream_index],
                   stream_offset+num_bytes))

        block_index_index=stream_offset//self._BlockSize
        block_offset=stream_offset%self._BlockSize

        num_bytes_left=num_bytes

        data=''

        while num_bytes_left>0:
            block=self._read_block(self._StreamBlocks[stream_index][block_index_index])
            
            block=block[block_offset:]
            if len(block)>num_bytes_left: block=block[:num_bytes_left]

            data+=block

            num_bytes_left-=len(block)
            assert num_bytes_left>=0

            # all blocks past the first start at index 0.
            block_offset=0

        assert len(data)==num_bytes
        return data

    def _num_blocks(self,num_bytes): return (num_bytes+self._BlockSize-1)//self._BlockSize
    
##########################################################################
##########################################################################

PDBHeader=collections.namedtuple('PDBHeader','Version Signature Age Guid')

def get_pdb_header(path):
    with MSFReader(path) as r:
        # https://llvm.org/docs/PDB/PdbStream.html
        PdbStreamHeader=r.read_stream_data(1,0,28)
        dumpv(PdbStreamHeader,'PdbStreamHeader')
        #print PdbStreamHeader

        Version=get4(PdbStreamHeader,0)
        Signature=get4(PdbStreamHeader,4)
        Age=get4(PdbStreamHeader,8)
        Guid=0
        for i in range(12,28): Guid=(Guid<<8)|ord(PdbStreamHeader[i])
        Guid=uuid.UUID(int=Guid)

        VC70=20000404
        if Version!=VC70:
            # "While the meaning of this field appears to be obvious,
            # in practice we have never observed a value other than
            # VC70, even with modern versions of the toolchain, and it
            # is unclear why the other values exist"
            raise PDBError(path,
                           'not a VC70 PDB - expected %d, got %d'%(VC70,
                                                                   Version))

        pv('Signature: %08x\n'%Signature)
        pv('GUID: %s\n'%Guid)
        #pv('GUID: {%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-%02x%02x%02x%02x%02x%02x}\n'%tuple(Guid))

        return PDBHeader(Version,Signature,Age,Guid)

##########################################################################
##########################################################################

def pdb_info(options):
    global g_verbose;g_verbose=options.verbose

    try: header=get_pdb_header(options.pdb_path)
    except PDBError,e:
        print>>sys.stderr,'FATAL: %s'%e.message
        sys.exit(1)

    n=0
    if options.age: n+=1
    if options.guid: n+=1
    if options.timestamp: n+=1

    def format_attr(key,value):
        if n>1: return '%s=%s'%(key,value)
        else: return value

    def spacing(line):
        if len(line)==0: return ''
        else: return ' '

    line=''
    if options.timestamp or n==0: line+=format_attr('timestamp','0x%08x'%header.Signature)
    if options.age: line+='%s%s'%(spacing(line),format_attr('age','0x%08x'%header.Age))
    if options.guid: line+='%s%s'%(spacing(line),format_attr('guid',header.Guid))

    line+=': %s'%options.pdb_path

    print line
    
##########################################################################
##########################################################################

def main(argv):
    parser=argparse.ArgumentParser()

    parser.add_argument('-a','--age',action='store_true',help='print PDB timestamp age')
    parser.add_argument('-g','--guid',action='store_true',help='print PDB GUID')
    parser.add_argument('-t','--timestamp',action='store_true',help='print PDB timestamp/signature')
    parser.add_argument('-v','--verbose',action='count',help='be more verbose')
    parser.add_argument('pdb_path',metavar='FILE',help='read from PDB file %(metavar)s')

    pdb_info(parser.parse_args(argv))

if __name__=='__main__': main(sys.argv[1:])
