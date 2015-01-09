#!/usr/bin/python

CFG_DIR='/etc/xen'
XM='/usr/sbin/xm'

import os,subprocess
from functools import partial

import lvm
import disks
from site_specific import getDomuDisks, getDomuDiskMountpoint
from cli import python_cli

def allDomus():
    all_files= os.listdir(CFG_DIR)
    cfg_files= filter( lambda x: x.endswith('.cfg'), all_files )
    domus= [x[:-4] for x in cfg_files]
    return domus

def startDomu(domu):
    print "starting domu {domu}".format(**locals())
    command='{0} create {1}/{2}.cfg'.format(XM,CFG_DIR,domu)
    p=subprocess.Popen(command, shell=True)
    p.wait()

def runningDomus():
    command='{0} list'.format(XM)
    out= subprocess.check_output(command, shell=True)
    running= [line.split()[0] for line in out.split('\n')[1:-1]]
    running.remove('Domain-0') #Domain-0 is not a DomU!
    return running

def isRunning(domu):
    return domu in runningDomus()

def getOpenedDomuDisks(domu_vg, domu):
    return disks.get_opened_disks( getDomuDisks(domu_vg, domu) )

def mountDomuDisks( domu_vg, domu, mountpoint ):
    '''mounts all domU disks (a root filesystem, possibly home, var, etc...)
    under a mountpoint'''
    print "mounting domu disks for domu {domu}".format(**locals())
    if domu in runningDomus():
        raise Exception("domU is currently running. Refusing to mount disks to avoid data loss")
    d_disks= getOpenedDomuDisks(domu_vg, domu)
    disk_mounts= [(d, getDomuDiskMountpoint(d)) for d in d_disks]
    disk_mounts= sorted(disk_mounts, key=lambda x: len(x[1]))
    for d,dm in disk_mounts:
        if dm!="":
            assert dm.startswith("/")
            m= os.path.join(mountpoint, dm[1:])
            print "mounting "+d+" on "+m 
            disks.mount(d,m)

def umountDomuDisks( domu_vg, domu, mountpoint ):
    '''unmounts all domU disks (a root filesystem, possibly home, var, etc...)
    under a mountpoint'''
    print "unmounting domu disks for domu {domu}".format(**locals())
    d_disks= getOpenedDomuDisks(domu_vg, domu)
    disk_mounts= [(d, getDomuDiskMountpoint(d)) for d in d_disks]
    disk_mounts= sorted(disk_mounts, key=lambda x: -len(x[1]))
    for d,dm in disk_mounts:
        if dm!="":
            assert dm.startswith("/")
            m= os.path.join(mountpoint, dm[1:])
            print "unmounting "+d+" on "+m 
            disks.umount(m)

if __name__=="__main__":
    python_cli(globals().values())
