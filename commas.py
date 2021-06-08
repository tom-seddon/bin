import sys

##########################################################################
##########################################################################

def main(argv):
    number=''
    dot=False
    
    while True:
        c=sys.stdin.read(1)
        if len(c)==0: break

        if c.isdigit(): number+=c
        else:
            if len(number)>0:
                if dot or len(number)<=3: sys.stdout.write(number)
                else:
                    parts=[]
                    for right in range(len(number)%3,len(number)+1,3):
                        left=right-3
                        if left<0: left=0
                        parts.append(number[left:right])
                    sys.stdout.write(','.join(parts))
                number=''
            dot=c=='.'
            sys.stdout.write(c)

##########################################################################
##########################################################################
        
if __name__=='__main__': main(sys.argv[1:])
