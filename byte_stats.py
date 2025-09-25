#!/usr/bin/python3
import sys,os,os.path,argparse,fnmatch,collections

##########################################################################
##########################################################################

class ByteStats:
    def __init__(self):
        self.count=0
        self.files=set()

##########################################################################
##########################################################################

def chstr(x):
    if x>=32 and x<127: return '%d (\'%c\')'%(x,x)
    else: return str(x)

def main2(options):
    paths=[]
    for dirpath,dirnames,filenames in os.walk('.'):
        for filename in filenames:
            for pattern in options.patterns:
                if fnmatch.fnmatch(filename,pattern):
                    paths.append(os.path.join(dirpath,filename))
                    break
    print('found %d file(s)'%len(paths))

    bytes=[]
    for i in range(256): bytes.append(ByteStats())

    total_num_bytes=0
    
    for path_index,path in enumerate(paths):
        with open(path,'rb') as f: data=f.read()

        total_num_bytes+=len(data)

        bytes_in_file=[False]*256
        
        for byte in data:
            bytes[byte].count+=1
            bytes_in_file[byte]=True

        for i in range(256):
            if bytes_in_file[i]: bytes[i].files.add(path_index)

    print('Total num bytes: %d'%total_num_bytes)

    never_seen=''
    a=0
    while a<256:
        if bytes[a].count>0: a+=1
        else:
            b=a
            while b<256 and bytes[b].count==0: b+=1
            if len(never_seen)>=0: never_seen+='; '
            if a==b-1: never_seen+=chstr(a)
            else: never_seen+='%s-%s'%(chstr(a),chstr(b-1))
            a=b

    print('Bytes never seen: %s'%never_seen)

##########################################################################
##########################################################################

def main(argv):
    parser=argparse.ArgumentParser()

    parser.add_argument('patterns',nargs='+',metavar='PATTERN',help='''glob pattern to match (searched recursively)''')

    main2(parser.parse_args(argv))

##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv[1:])
