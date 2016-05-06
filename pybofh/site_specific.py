#his file contains site-specific values or functions with such knowledge

import os
from functools import partial
import drbd


#------DISKS-------------------------------------------------------------

def decrypted_path( encrypted_disk_path ):
    decrypted_name= os.path.basename(encrypted_disk_path )
    return "/dev/mapper/"+decrypted_name

#-------XEN-----------------------------------------------------------------

CFG_DIR='/etc/xen'
CFG_EXT='.cfg'

def getAllDomuNames():
    '''returns all the DomU configuration files available to this machine'''
    all_files= os.listdir(CFG_DIR)
    cfg_files= filter( lambda x: x.endswith(CFG_EXT), all_files )
    names= map( lambda f: f[:-len(CFG_EXT)], cfg_files )
    return names

def getDomuDiskMountpoint(domu_disk):
    '''Given a DomuDisk,
    returns its mountpoint in the DomU root filestem (/home, /var, ...)'''
    MOUNTPOINT_MAP={"root":"/","home":"/home","swap":"","media":"/media"}
    d=os.path.basename( domu_disk.device )
    mountpoint_part= d.split("_")[-1]
    mountpoint_part= mountpoint_part.split("-")
    suffix, args= mountpoint_part[0],mountpoint_part[1:]
    mountpoint= MOUNTPOINT_MAP[suffix]
    print args
    if args:
        mountpoint= os.path.join(mountpoint, *args)
    return mountpoint

def getDomuConfigFile(domu):
    '''Given the DomU name, returns its configuration file'''
    p= os.path.join( CFG_DIR, domu + CFG_EXT )
    return p

