#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import struct
import time
from hashlib import md5
import sys
import os
import random
import binascii
import json
import uuid

# CONFIG
def _application_directory():
    """Return the directory beside the script or packaged executable."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


PROFILE_PATH = os.path.join(_application_directory(), "user_profile.json")


def load_profile():
    """Read the optional saved profile without creating a file."""
    if not os.path.isfile(PROFILE_PATH):
        return {}

    try:
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            profile = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}

    return profile if isinstance(profile, dict) else {}


def has_saved_credentials():
    """Whether a usable account and password have been saved."""
    profile = load_profile()
    return bool(profile.get("username") and profile.get("password"))


data = load_profile()
server = "192.168.255.249"
username = str(data.get("username") or "")
password = str(data.get("password") or "")
host_name = "LIYUANYUAN"
host_os = "8089D"
host_ip = "10.53.1.224"
PRIMARY_DNS = "10.200.4.1"
dhcp_server = "0.0.0.0"
mac = eval(hex(int((':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) for i in range(0, 8*6, 8)][::-1])).replace(':', ''), 16)))
CONTROLCHECKSTATUS = b'\x20'
ADAPTERNUM = b'\x01'
KEEP_ALIVE_VERSION = b'\xdc\x02'
AUTH_VERSION = b'\x0a\x00'
IPDOG = b'\x01'
ror_version = False
# CONFIG_END
'''
AUTH_VERSION:
    unsigned char ClientVerInfoAndInternetMode;
    unsigned char DogVersion;
'''

nic_name = '' #Indicate your nic, e.g. 'eth0.2'.nic_name
bind_ip = '0.0.0.0'

class ChallengeException (Exception):
    def __init__(self):
        pass

class LoginException (Exception):
    def __init__(self):
        pass

def bind_nic():
    try:
        import fcntl
        def get_ip_address(ifname):
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            return socket.inet_ntoa(fcntl.ioctl(
                s.fileno(),
                0x8915,  # SIOCGIFADDR
                struct.pack('256s', ifname[:15])
            )[20:24])
        return get_ip_address(nic_name)
    except ImportError as e:
        return '0.0.0.0'
    except IOError as e:
        return '0.0.0.0'
    finally:
        return '0.0.0.0'

if nic_name != '':
    bind_ip = bind_nic()

SALT = ''
AUTH_INFO = b''
s = None  # 将在 main() 中初始化
IS_TEST = True

# specified fields based on version
CONF = "/etc/drcom.conf"
UNLIMITED_RETRY = True
EXCEPTION = False
DEBUG = False #log saves to file
LOG_PATH = '/tmp/drcom_client.log'
if IS_TEST:
    DEBUG = False
    LOG_PATH = 'drcom_client.log'


def log(*args, **kwargs):
    pass

def md5sum(s):
    m = md5()
    m.update(s)
    return m.digest()

def dump(n):
    s = '%x' % n
    if len(s) & 1:
        s = '0' + s
    return binascii.unhexlify(bytes(s, 'ascii'))

def ror(md5, pwd):
    ret = ''
    for i in range(len(pwd)):
        x = ord(md5[i]) ^ ord(pwd[i])
        ret += struct.pack("B", ((x<<3)&0xFF) + (x>>5))
    return ret

def challenge(svr,ran):
    global s
    while True:
        t = struct.pack("<H", int(ran)%(0xFFFF))
        s.sendto(b"\x01\x02" + t + b"\x09" + b"\x00"*15, (svr, 61440))
        try:
            data, address = s.recvfrom(1024)
            log('[challenge] recv', str(binascii.hexlify(data))[2:][:-1])
        except Exception as e:
            raise(e)
            log('[challenge] timeout, retrying...')
            continue
        
        if address == (svr, 61440):
            break
        else:
            continue
    log('[DEBUG] challenge:\n' + str(binascii.hexlify(data))[2:][:-1])
    if data[:1] != b'\x02':
        raise ChallengeException
    log('[challenge] challenge packet sent.')
    return data[4:8]

def keep_alive_package_builder(number,random,tail,type=1,first=False):
    data = b'\x07'+ bytes([number]) + b'\x28\x00\x0B' + bytes([type])
    if first :
        data += b'\x0F\x27'
    else:
        data += KEEP_ALIVE_VERSION
    data += b'\x2F\x12' + b'\x00' * 6
    data += tail
    data += b'\x00' * 4
    #data += struct.pack("!H",0xdc02)
    if type == 3:
        foo = b''.join([bytes([int(i)]) for i in host_ip.split('.')]) # host_ip
        #CRC
        # edited on 2014/5/12, filled zeros to checksum
        # crc = packet_CRC(data+foo)
        crc = b'\x00' * 4
        #data += struct.pack("!I",crc) + foo + b'\x00' * 8
        data += crc + foo + b'\x00' * 8
    else: #packet type = 1
        data += b'\x00' * 16
    return data

# def packet_CRC(s):
#     ret = 0
#     for i in re.findall('..', s):
#         ret ^= struct.unpack('>h', i)[0]
#         ret &= 0xFFFF
#     ret = ret * 0x2c7
#     return ret

def keep_alive2(*args):
    global s
    #first keep_alive:
    #number = number (mod 7)
    #status = 1: first packet user sended
    #         2: first packet user recieved
    #         3: 2nd packet user sended
    #         4: 2nd packet user recieved
    #   Codes for test
    tail = ''
    packet = ''
    svr = server
    ran = random.randint(0, 0xFFFF)
    ran += random.randint(1, 10)   
    # 2014/10/15 add by latyas, maybe svr sends back a file packet
    svr_num = 0
    packet = keep_alive_package_builder(svr_num,dump(ran), b'\x00'*4, 1, True)
    while True:
        log('[keep-alive2] send1', str(binascii.hexlify(packet))[2:][:-1])
        s.sendto(packet, (svr, 61440))
        data, address = s.recvfrom(1024)
        log('[keep-alive2] recv1', str(binascii.hexlify(data))[2:][:-1])
        if data.startswith(b'\x07\x00\x28\x00') or data.startswith(b'\x07' + bytes([svr_num]) + b'\x28\x00'):
            break
        elif data[:1] == b'\x07' and data[2:3] == b'\x10':
            log('[keep-alive2] recv file, resending..')
            svr_num = svr_num + 1
            # packet = keep_alive_package_builder(svr_num,dump(ran),'\x00'*4,1, False)
            break
        else:
            log('[keep-alive2] recv1/unexpected', str(binascii.hexlify(data))[2:][:-1])
    #log('[keep-alive2] recv1', str(binascii.hexlify(data))[2:][:-1])
    
    ran += random.randint(1, 10)   
    packet = keep_alive_package_builder(svr_num, dump(ran), b'\x00'*4, 1, False)
    log('[keep-alive2] send2', str(binascii.hexlify(packet))[2:][:-1])
    s.sendto(packet, (svr, 61440))
    while True:
        data, address = s.recvfrom(1024)
        if data[:1] == b'\x07':
            svr_num = svr_num + 1
            break
        else:
            log('[keep-alive2] recv2/unexpected', str(binascii.hexlify(data))[2:][:-1])
    log('[keep-alive2] recv2', str(binascii.hexlify(data))[2:][:-1])
    tail = data[16:20]


    ran += random.randint(1, 10)   
    packet = keep_alive_package_builder(svr_num, dump(ran), tail, 3, False)
    log('[keep-alive2] send3', str(binascii.hexlify(packet))[2:][:-1])
    s.sendto(packet, (svr, 61440))
    while True:
        data, address = s.recvfrom(1024)
        if data[:1] == b'\x07':
            svr_num = svr_num + 1
            break
        else:
            log('[keep-alive2] recv3/unexpected', str(binascii.hexlify(data))[2:][:-1])
    log('[keep-alive2] recv3', str(binascii.hexlify(data))[2:][:-1])
    tail = data[16:20]
    log("[keep-alive2] keep-alive2 loop was in daemon.")
    
    i = svr_num
    while True:
        try:
            time.sleep(20)
            keep_alive1(*args)
            ran += random.randint(1, 10)   
            packet = keep_alive_package_builder(i, dump(ran), tail, 1, False)
            #log('DEBUG: keep_alive2,packet 4\n', str(binascii.hexlify(packet))[2:][:-1])
            log('[keep_alive2] send',str(i), str(binascii.hexlify(packet))[2:][:-1])
            s.sendto(packet, (svr, 61440))
            data, address = s.recvfrom(1024)
            log('[keep_alive2] recv', str(binascii.hexlify(data))[2:][:-1])
            tail = data[16:20]
            #log('DEBUG: keep_alive2,packet 4 return\n', str(binascii.hexlify(data))[2:][:-1])
        
            ran += random.randint(1, 10)   
            packet = keep_alive_package_builder(i+1, dump(ran), tail, 3, False)
            #log('DEBUG: keep_alive2,packet 5\n', str(binascii.hexlify(packet))[2:][:-1])
            s.sendto(packet, (svr, 61440))
            log('[keep_alive2] send', str(i+1), str(binascii.hexlify(packet))[2:][:-1])
            data, address = s.recvfrom(1024)
            log('[keep_alive2] recv', str(binascii.hexlify(data))[2:][:-1])
            tail = data[16:20]
            #log('DEBUG: keep_alive2,packet 5 return\n', str(binascii.hexlify(data))[2:][:-1])
            i = (i+2) % 127 #must less than 128 ,else the keep_alive2() couldn't receive anything.
        except:
            pass

def checksum(s):
    ret = 1234
    x = 0
    for i in [x*4 for x in range(0, -(-len(s)//4))]:
        ret ^= int(binascii.hexlify(s[i:i+4].ljust(4, b'\x00')[::-1]), 16)
    ret = (1968 * ret) & 0xffffffff
    return struct.pack('<I', ret)

def mkpkt(salt, usr, pwd, mac):
    '''
	struct  _tagLoginPacket
	{
	    struct _tagDrCOMHeader Header;
	    unsigned char PasswordMd5[MD5_LEN];
	    char Account[ACCOUNT_MAX_LEN];
	    unsigned char ControlCheckStatus;
	    unsigned char AdapterNum;
	    unsigned char MacAddrXORPasswordMD5[MAC_LEN];
	    unsigned char PasswordMd5_2[MD5_LEN];
	    unsigned char HostIpNum;
	    unsigned int HostIPList[HOST_MAX_IP_NUM];
	    unsigned char HalfMD5[8];
	    unsigned char DogFlag;
	    unsigned int unkown2;
	    struct _tagHostInfo HostInfo;
	    unsigned char ClientVerInfoAndInternetMode;
	    unsigned char DogVersion;
	};
    '''
    data = b'\x03\x01\x00' + bytes([len(usr) + 20])
    data += md5sum(b'\x03\x01' + salt + pwd.encode())
    data += (usr.encode() + 36*b'\x00')[:36]
    data += CONTROLCHECKSTATUS
    data += ADAPTERNUM
    data += dump(int(binascii.hexlify(data[4:10]), 16)^mac)[-6:] #mac xor md51
    data += md5sum(b'\x01' + pwd.encode() + salt + b'\x00'*4) #md52
    data += b'\x01' # number of ip
    data += b''.join([bytes([int(i)]) for i in host_ip.split('.')]) #x.x.x.x ->
    data += b'\00' * 4 #your ipaddress 2
    data += b'\00' * 4 #your ipaddress 3
    data += b'\00' * 4 #your ipaddress 4
    data += md5sum(data + b'\x14\x00\x07\x0B')[:8] #md53
    data += IPDOG
    data += b'\x00'*4 # unknown2
    '''
	struct  _tagOSVERSIONINFO
	{
	    unsigned int OSVersionInfoSize;
	    unsigned int MajorVersion;
	    unsigned int MinorVersion;
	    unsigned int BuildNumber;
	    unsigned int PlatformID;
	    char ServicePack[128];
	};
	struct  _tagHostInfo
	{
	    char HostName[HOST_NAME_MAX_LEN];
	    unsigned int DNSIP1;
	    unsigned int DHCPServerIP;
	    unsigned int DNSIP2;
	    unsigned int WINSIP1;
	    unsigned int WINSIP2;
	    struct _tagDrCOM_OSVERSIONINFO OSVersion;
	};
    '''
    data += (host_name.encode() + 32 * b'\x00')[:32] # _tagHostInfo.HostName
    data += b''.join([bytes([int(i)]) for i in PRIMARY_DNS.split('.')]) # _tagHostInfo.DNSIP1
    data += b''.join([bytes([int(i)]) for i in dhcp_server.split('.')]) # _tagHostInfo.DHCPServerIP
    data += b'\x00\x00\x00\x00' # _tagHostInfo.DNSIP2
    data += b'\x00' * 4 # _tagHostInfo.WINSIP1
    data += b'\x00' * 4 # _tagHostInfo.WINSIP2
    data += b'\x94\x00\x00\x00' # _tagHostInfo.OSVersion.OSVersionInfoSize
    data += b'\x05\x00\x00\x00' # _tagHostInfo.OSVersion.MajorVersion
    data += b'\x01\x00\x00\x00' # _tagHostInfo.OSVersion.MinorVersion
    data += b'\x28\x0A\x00\x00' # _tagHostInfo.OSVersion.BuildNumber
    data += b'\x02\x00\x00\x00' # _tagHostInfo.OSVersion.PlatformID
    # _tagHostInfo.OSVersion.ServicePack
    data += (host_os.encode() + 32 * b'\x00')[:32]
    data += b'\x00' * 96
    # END OF _tagHostInfo

    data += AUTH_VERSION
    if ror_version:
        '''
	struct  _tagLDAPAuth
	{
	    unsigned char Code;
	    unsigned char PasswordLen;
	    unsigned char Password[MD5_LEN];
	};
        '''
        data += b'\x00' # _tagLDAPAuth.Code
        data += bytes([len(pwd)]) # _tagLDAPAuth.PasswordLen
        data += ror(md5sum(b'\x03\x01' + salt + pwd), pwd) # _tagLDAPAuth.Password
    '''
	struct  _tagDrcomAuthExtData
	{
	    unsigned char Code;
	    unsigned char Len;
	    unsigned long CRC;
	    unsigned short Option;
	    unsigned char AdapterAddress[MAC_LEN];
	};
    '''
    data += b'\x02' # _tagDrcomAuthExtData.Code
    data += b'\x0C' # _tagDrcomAuthExtData.Len
    data += checksum(data + b'\x01\x26\x07\x11\x00\x00' + dump(mac)) # _tagDrcomAuthExtData.CRC
    data += b'\x00\x00' # _tagDrcomAuthExtData.Option
    data += dump(mac) # _tagDrcomAuthExtData.AdapterAddress
    # END OF _tagDrcomAuthExtData

    data += b'\x00' # auto logout / default: False
    data += b'\x00' # broadcast mode / default : False
    data += b'\xE9\x13' #unknown, filled numbers randomly =w=

    log('[mkpkt]', str(binascii.hexlify(data))[2:][:-1])
    return data

def login(usr, pwd, svr):
    global SALT
    global AUTH_INFO
    global s

    i = 0
    while True:
        salt = challenge(svr, time.time()+random.randint(0xF, 0xFF))
        SALT = salt
        packet = mkpkt(salt, usr, pwd, mac)
        log('[login] send', str(binascii.hexlify(packet))[2:][:-1])
        s.sendto(packet, (svr, 61440))
        data, address = s.recvfrom(1024)
        log('[login] recv', str(binascii.hexlify(data))[2:][:-1])
        log('[login] packet sent.')
        if address == (svr, 61440):
            if data[:1] == b'\x04':
                log('[login] loged in')
                AUTH_INFO = data[23:39]
                break
            else:
                log('[login] login failed.')
                if IS_TEST:
                    time.sleep(3)
                else:
                    time.sleep(30)
                continue
        else:
            if i >= 5 and UNLIMITED_RETRY == False :
                log('[login] exception occured.')
                sys.exit(1)
            else:
                continue

    log('[login] login sent')
    #0.8 changed:
    return data[23:39]
    #return data[-22:-6]

def logout(usr, pwd, svr, mac, auth_info):
    salt = challenge(svr, time.time()+random.randint(0xF, 0xFF))
    if salt:
        data = b'\x06\x01\x00' + bytes([len(usr) + 20])
        data += md5sum(b'\x03\x01' + salt + pwd.encode())
        data += (usr + 36*'\x00')[:36]
        data += CONTROLCHECKSTATUS
        data += ADAPTERNUM
        data += dump(int(binascii.hexlify(data[4:10]), 16)^mac)[-6:]
        # data += b'\x44\x72\x63\x6F' # Drco
        data += auth_info
        s.send(data)
        data, address = s.recvfrom(1024)
        if data[:1] == b'\x04':
            log('[logout_auth] logouted.')

def keep_alive1(salt, tail, pwd, svr):
    global s
    foo = struct.pack('!H',int(time.time())%0xFFFF)
    data = b'\xff' + md5sum(b'\x03\x01' + salt + pwd.encode()) + b'\x00\x00\x00'
    data += tail
    data += foo + b'\x00\x00\x00\x00'
    log('[keep_alive1] send', str(binascii.hexlify(data))[2:][:-1])

    s.sendto(data, (svr, 61440))
    while True:
        data, address = s.recvfrom(1024)
        if data[:1] == b'\x07':
            break
        else:
            log('[keep-alive1]recv/not expected', str(binascii.hexlify(data))[2:][:-1])
    log('[keep-alive1] recv', str(binascii.hexlify(data))[2:][:-1])

def empty_socket_buffer():
    global s
#empty buffer for some fucking schools
    log('starting to empty socket buffer')
    try:
        while True:
            data, address = s.recvfrom(1024)
            log('recived sth unexpected', str(binascii.hexlify(data))[2:][:-1])
            if s == '':
                break
    except:
        # get exception means it has done.
        log('exception in empty_socket_buffer')
        pass
    log('emptyed')
def daemon():
    with open('/var/run/jludrcom.pid','w') as f:
        f.write(str(os.getpid()))
        
def init_socket():
    """初始化 UDP Socket（全局）"""
    global s
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('0.0.0.0', 61440))
    s.settimeout(3)

def main():
    global s
    if not has_saved_credentials():
        print("未找到有效的 user_profile.json，未执行认证。请先通过 GUI 保存账号信息。")
        return
    if s is None:
        init_socket()
    if not IS_TEST:
        daemon()
        if os.path.exists(CONF):
            with open(CONF, "r", encoding="utf-8") as f:
                exec(f.read(), globals())
    log("auth svr: " + server + "\nusername: " + username + "\npassword: " + password + "\nmac: " + str(hex(mac))[:-1])
    log("bind ip: " + bind_ip)
    while True:
      try:
        package_tail = login(username, password, server)
      except LoginException:
        continue
      log('package_tail', str(binascii.hexlify(package_tail))[2:][:-1])
      #keep_alive1 is fucking bullshit!
      empty_socket_buffer()
      keep_alive1(SALT, package_tail, password, server)
      keep_alive2(SALT, package_tail, password, server)

if __name__ == "__main__":
    main()
