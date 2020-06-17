import sys,argparse,os,subprocess,re,fnmatch,collections

##########################################################################
##########################################################################

g_verbose=False

def v(msg):
    if g_verbose:
        sys.stdout.write(msg)
        sys.stdout.flush()

##########################################################################
##########################################################################

def run(args,
        stdin_data=''):
    v('RUN: %s\n'%args)
    process=subprocess.Popen(args=args,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    output=process.communicate(stdin_data)
    if process.returncode!=0:
        sys.stderr.write(''.join(output))
        raise Exception('%s failed with exit code %d'%(args[0],process.returncode))
    output=[x.strip() for x in output[0].splitlines()]
    return output

##########################################################################
##########################################################################

def get_interfaces():
    lines=run('netsh interface ipv4 show interfaces')

    info_by_name={}

    for line in lines[3:]:
        if line.strip()=='': continue
        idx,met,mtu,state,name=line.split(None,4)
        if name in info_by_name: raise Exception('duplicated interface: %s'%name)
        info_by_name[name]={
            'Idx':int(idx),
            'Met':int(met),
            'MTU':int(mtu),
            'State':state,
            'Name':name,
        }

    lines=run('netsh interface ipv4 show addresses')

    interface_re=re.compile(r'^Configuration for interface "(?P<name>.*)"$')
    attr_re=re.compile(r'^[ \t]*(?P<key>.*):[ \t]*(?P<value>.*)$')

    for line in lines:
        m=interface_re.match(line)
        if m is not None:
            interface=m.group('name')
            continue

        m=attr_re.match(line)
        if m is not None:
            info_by_name.setdefault(interface,{})[m.group('key')]=m.group('value')

    return info_by_name
        
##########################################################################
##########################################################################

def cmd_list(options):
    interfaces=get_interfaces()
    
    for name in sorted(interfaces.keys()):
        addr=interfaces[name].get('IP Address')
        if addr is None: continue
        
        idx=interfaces[name].get('Idx')

        print '%s: IP: %s'%(name,addr)
        print '%s: Idx: %s'%(name,idx)

##########################################################################
##########################################################################

def get_single_match(map,what,glob):
    item=None
    for k,v in map.iteritems():
        if fnmatch.fnmatch(k,glob):
            if item is not None: raise Exception('name matches more than one %s: %s'%(what,glob))
            item=v

    if item is None: raise Exception('%s not found: %s'%(what,glob))

    return item
    
##########################################################################
##########################################################################

def get_byte(parts,i):
    value=int(parts[i],0)
    if value<0 or value>255: raise Exception('bad byte: %s'%parts[i])
    return value

##########################################################################
##########################################################################

def get_ipv4_value(addr):
    parts=addr.split('.')
    if len(parts)!=4: raise Exception('bad IPv4 address: %s'%addr)
    return (get_byte(parts,0)<<24|
            get_byte(parts,1)<<16|
            get_byte(parts,2)<<8|
            get_byte(parts,3)<<0)

##########################################################################
##########################################################################

def get_ipv4_str(addr):
    return '%d.%d.%d.%d'%(addr>>24&0xff,
                          addr>>16&0xff,
                          addr>>8&0xff,
                          addr>>0&0xff)

##########################################################################
##########################################################################

def get_implied_ipv4_mask(addr):
    if (addr&0x00ffffff)==0: return 0xff000000
    if (addr&0x0000ffff)==0: return 0xffff0000
    if (addr&0x000000ff)==0: return 0xffffff00
    raise Exception('implausible implied IPv4 mask for address: %s'%get_ipv4_str(addr))

##########################################################################
##########################################################################

SubnetInfo=collections.namedtuple('SubnetInfo','addr mask')

def get_subnet_info(info):
    prefix=info.get('Subnet Prefix')
    if prefix is None: return None

    parts=prefix.split()

    if len(parts)!=3: return None
    if parts[1]!='(mask': return None

    mask=parts[2]
    if mask.endswith(')'): mask=mask[:-1]

    addr=parts[0]
    if '/' in addr: addr=addr.split('/')[0]

    return SubnetInfo(get_ipv4_value(addr),
                      get_ipv4_value(mask))

##########################################################################
##########################################################################

def cmd_fix(options):
    interfaces=get_interfaces()
    
    lan_interface=get_single_match(interfaces,'network interface',options.lan_adapter)
    vpn_interface=get_single_match(interfaces,'network interface',options.vpn_adapter)

    lan_subnet=get_subnet_info(lan_interface)
    vpn_subnet=get_subnet_info(vpn_interface)

    # Remove VPN routes for LAN.
    run(['route',
         'delete',
         get_ipv4_str(lan_subnet.addr&lan_subnet.mask),
         'if',str(vpn_interface.get('Idx'))])

    # Remove VPN routes for internet.
    run(['route',
         'delete',
         '0.0.0.0',
         'if',str(vpn_interface.get('Idx'))])

    # (don't bother doing this next bit - the mask is 0xfffffff...)

    # # Reinstate VPN routes for VPN.
    # run(['route',
    #      'add',
    #      get_ipv4_str(vpn_subnet.addr&vpn_subnet.mask),
    #      'mask',get_ipv4_str(vpn_subnet.mask),
    #      vpn_interface.get('Default Gateway'),
    #      'if',str(vpn_interface.get('Idx'))])

    # Add additional VPN routes as required.
    for vpn_addr in options.vpn_addrs:
        vpn_addr=get_ipv4_value(vpn_addr)
        run(['route',
             'add',
             get_ipv4_str(vpn_addr),
             'mask',get_ipv4_str(get_implied_ipv4_mask(vpn_addr)),
             vpn_interface.get('IP Address'),
             'if',str(vpn_interface.get('Idx'))])
    
##########################################################################
##########################################################################

def main(options):
    global g_verbose
    g_verbose=options.verbose

    options.func(options)

##########################################################################
##########################################################################

def fix_vpn_route_table(argv):
    parser=argparse.ArgumentParser()
    parser.add_argument('-v','--verbose',action='store_true',help='be more verbose')
    subparsers=parser.add_subparsers()
    
    list_parser=subparsers.add_parser('list')
    list_parser.set_defaults(func=cmd_list)

    fix_parser=subparsers.add_parser('fix')
    fix_parser.add_argument('--vpn',dest='vpn_addrs',default=[],action='append',metavar='ADDR',help='assign %(metavar)s range to the VPN, trailing 0s implying (bytewise) address mask')
    fix_parser.add_argument('lan_adapter',metavar='LAN-ADAPTER',help='glob pattern matching LAN adapter')
    fix_parser.add_argument('vpn_adapter',metavar='VPN-ADAPTER',help='glob pattern matching VPN adapter')
    fix_parser.set_defaults(func=cmd_fix)

    main(parser.parse_args(argv))

##########################################################################
##########################################################################
    
if __name__=='__main__': fix_vpn_route_table(sys.argv[1:])
