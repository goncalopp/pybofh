#!/usr/bin/python

XM='/usr/sbin/xm'

import os,subprocess
from functools import partial
import re

import lvm
from mount import mount, unmount
import encryption
from site_specific import getDomuConfigFile, getDomuDiskMountpoint, getAllDomuNames
from cli import python_cli

class DomuDisk(object):
    def __init__(self, protocol, device, domu_device, access):
        self.protocol= protocol
        self.device= device
        self.domu_device= domu_device
        self.access= access
    def __repr__(self):
        return "DomuDisk<{}:{},{},{}>".format(self.protocol, self.device, self.domu_device, self.access)

class DomuConfig(object):
    def __init__(self, path):
        if not os.path.exists(path):
            raise Exception("DomU configuration doesn't exist: "+path)
        self.filename= path

    @property
    def text(self):
        return open(self.filename).read()

    def _get_key(self, k):
        import shlex
        s= shlex.split( self.text )
        i= s.index(k)
        assert s[i+1]=="="
        i+=2
        if s[i]=="[":
            i2= s.index("]", i)
            return list(s[i+1:i2])
        else:
            return s[i]

    def getDisks( self ):
        def disk_string_to_disk(s):
            proto_device, domu_device, access= s.split(",")[:3]
            proto, device= proto_device.split(":")
            return DomuDisk( proto, device, domu_device, access ) 
        disks_strings= self._get_key("disk")
        disks= map( disk_string_to_disk, disks_strings )
        return disks

    def __getattr__(self, k): 
        '''provides DomuConfig.getName(), etc'''
        if k.startswith("get"):
            k= k[3:].lower()
            return lambda : self._get_key(k)
        raise AttributeError("DomuConfig object has no attribute "+k)

    def __repr__(self):
        return "DomuConfig<{}>".format(self.filename)



class Domu(object):
    class NoDomuConfig(Exception):
        pass
    
    def __init__(self, name, configfile_path_override=None):
        self.name=name
        self.configfile= configfile_path_override or getDomuConfigFile(name)
        if self.configfile:
            try:
                self._config= DomuConfig( self.configfile )
            except Exception as e:
                print "failed to get DomuConfig for {}:i {}".format(name, e)
                self._config= None
        self.sanity_check()
    
    @property
    def config(self):
        if not self._config:
            raise Domu.NoDomuConfig(self.name)
        return self._config
    
    def sanity_check(self):
        try:
            n1,n2= self.name, self.config.getName()
            if n1!=n2:
                print "Warning: domu configured name mismatch: {},{}".format(n1,n2)
        except Domu.NoDomuConfig(self):
            pass

    def start(self):
        print "starting domu {domu}".format(domu=self)
        cf= self.config.filename
        command= (XM, "create", cf)
        subprocess.check_call(command)

    @property
    def isRunning(self):
        return self.name in runningDomus( return_objects=False )

    def __repr__(self):
        return "Domu<{}>".format(self.name)

def allDomus():
    return map(Domu, getAllDomuNames())

def runningDomus( return_objects=True ):
    command= (XM, "list")
    out= subprocess.check_output(command)
    running= [line.split()[0] for line in out.split('\n')[1:-1]]
    running.remove('Domain-0') #Domain-0 is not a DomU!
    if return_objects:
        return map(Domu, running)
    else:
        return running

def getOpenedDomuDisks(domu_vg, domu):
    return encryption.get_opened_disks( getDomuDisks(domu_vg, domu) )

def mountedDomuDisks( domu_vg, domu, mountpoint ):
    '''mounts all domU disks (a root filesystem, possibly home, var, etc...)
    under a mountpoint'''
    print "mounting domu disks for domu {domu}".format(**locals())
    if domu.isRunning:
        raise Exception("domU is currently running. Refusing to mount disks to avoid data loss")
    d_disks= getOpenedDomuDisks(domu_vg, domu)
    disk_mounts= [(d, getDomuDiskMountpoint(d)) for d in d_disks]
    disk_mounts= sorted(disk_mounts, key=lambda x: len(x[1]))
    for d,dm in disk_mounts:
        if dm!="":
            assert dm.startswith("/")
            m= os.path.join(mountpoint, dm[1:])
            print "mounting "+d+" on "+m 
            mount(d,m)

def unmountDomuDisks( domu_vg, domu, mountpoint ):
    '''unmounts all domU disks (a root filesystem, possibly home, var, etc...)
    under a mountpoint'''
    print "unmounting domu disks for domu {domu}".format(**locals())
    d_disks= getOpenedDomuDisks(domu_vg, domu)
    disk_mounts= [(d, getDomuDiskMountpoint(d)) for d in d_disks]
    disk_mounts= sorted(disk_mounts, key=lambda x: -len(x[1]))    #sort 
    for d,dm in disk_mounts:
        if dm!="":
            assert dm.startswith("/")
            m= os.path.join(mountpoint, dm[1:])
            print "unmounting "+d+" on "+m 
            unmount(m)

if __name__=="__main__":
    python_cli(globals().values())
