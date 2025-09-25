#!/usr/bin/python3
import sys,os,os.path,argparse,struct,mmap,signal

##########################################################################
##########################################################################

g_verbose=False

def pv(msg):
    if g_verbose: sys.stderr.write(msg)

##########################################################################
##########################################################################

g_ctrl_c_counter=0

def handle_ctrl_c(signum,frame):
    global g_ctrl_c_counter

    g_ctrl_c_counter+=1

##########################################################################
##########################################################################

def main3(input_f,options):
    od_path=options.output_path+'.data'
    oc_path=options.output_path+'.chunks'

    pv('''Options: chunk_size_bytes: %d; max_size_bytes: %d\n'''%(options.chunk_size_bytes, options.max_size_bytes))
    chunk_size_bytes=min(options.chunk_size_bytes,
                         options.max_size_bytes)
    pv('''Chunk size bytes: %d\n'''%chunk_size_bytes)

    with (open(od_path,'wb') as od_f,open(oc_path,'wb') as oc_f):
        num_written=0

        def get_offset(): return num_written%options.max_size_bytes

        data=None
        while True:
            if g_ctrl_c_counter>0:
                # Ctrl+C pressed.
                pv('''Ctrl+C pressed\n''')
                break
            
            if data is None: data=input_f.read(chunk_size_bytes)
            if len(data)==0:
                # input exhausted.
                pv('''Input exhausted\n''')
                break

            offset=get_offset()
            overrun=offset+len(data)-options.max_size_bytes
            if overrun>0:
                rest=data[-overrun:]
                data=data[:-overrun]
            else: rest=None
            od_f.seek(offset,os.SEEK_SET)
            od_f.write(data)
            num_written+=len(data)
            data=rest
            
            if num_written>options.max_size_bytes:
                # the split point now needs recording.
                oc_f.seek(0,os.SEEK_SET)
                oc_f.write(struct.pack('<Q',get_offset()))
                oc_f.flush()
                os.fsync(oc_f.fileno())

    pv('''Num bytes written: %d\n'''%num_written)
    if num_written<options.max_size_bytes:
        os.replace(od_path,options.output_path)
        os.unlink(oc_path)
    else:
        with open(oc_path,'rb') as f:
            split_offset=struct.unpack('<Q',f.read())[0]

        pv('''Split offset: %d (0x%x)\n'''%(split_offset,split_offset))
            
        with (open(od_path,'rb') as in_f,
              open(options.output_path,'wb') as out_f):

            def copy_bytes(begin,end):
                in_f.seek(begin,os.SEEK_SET)
                assert begin<=end
                if begin<end:
                    num_bytes_left=end-begin
                    pv('''num_bytes_left: %d\n'''%num_bytes_left)
                    copy_chunk_size_bytes=1048576
                    while num_bytes_left>0:
                        n=min(num_bytes_left,copy_chunk_size_bytes)
                        data=in_f.read(n)
                        assert len(data)<=n
                        out_f.write(data)
                        num_bytes_left-=len(data)
                    assert num_bytes_left==0,(num_bytes_left)
            
            copy_bytes(split_offset,options.max_size_bytes)
            copy_bytes(0,split_offset)

        os.unlink(od_path)
        os.unlink(oc_path)
            
def main2(options):
    global g_verbose; g_verbose=options.verbose

    signal.signal(signal.SIGINT,handle_ctrl_c)

    if options.input_path is not None:
        with open(options.input_path,'rb') as f: main3(f,options)
    else: main3(sys.stdin.buffer,options)

##########################################################################
##########################################################################

def auto_int(x):
    try: return int(x,0)
    except ValueError:
        # attempt to handle stuff like "1e9"
        return int(float(x))

def main(argv):
    parser=argparse.ArgumentParser()

    parser.add_argument('-C','--chunk-size',dest='chunk_size_bytes',type=auto_int,default=1024*1024,metavar='N',help='''read in chunks of %(metavar)s bytes. Default: %(default)s''')
    parser.add_argument('-b','--bytes',dest='max_size_bytes',type=auto_int,metavar='N',required=True,help='''save max last %(metavar)s bytes''')
    parser.add_argument('-v','--verbose',action='store_true',help='''be more verbose''')
    parser.add_argument('output_path',metavar='FILE',help='''write data to %(metavar)s (and will be used as stem for temp files)''')
    parser.add_argument('-i','--input',dest='input_path',default=None,metavar='FILE',help='''read input from %(metavar)s (stdin if not specified)''')
    main2(parser.parse_args(argv))

##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv[1:])
