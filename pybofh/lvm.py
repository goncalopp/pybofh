import os
import subprocess
from misc import sfilter, rsplit
from pybofh.blockdevice import BlockDevice


REMOVED= '[REMOVED]'

class PV(BlockDevice):
    def __init__(self, device):
        self.device= device

    def create(self, **kwargs):
        createPV(self.device, **kwargs)

    def createVG(self, name, **kwargs):
        createVG(name, self.device, **kwargs)
        return VG(name)

    def remove(self):
        removePV(self.device)
        self.device= REMOVED

class VG(object):
    def __init__(self, vg_name):
        self.name= vg_name
        if not self.name in getVGs():
            raise Exception("VG {} does not exist".format(name))

    @property
    def path(self):
        return "/dev/{}/".format(self.name)

    def getLVs(self):
        names= getLVs(self.name, full_path=False)
        lvs= [ LV(self, name) for name in names ]
        return lvs


    def createLV( self, name, *args, **kwargs ):
        createLV( self.name, name, *args, **kwargs)
        return LV( self, name )

    def lv(self, lv_name):
        return LV(self, lv_name)

    def __repr__(self):
        return "{}<{}>".format(self.__class__.__name__, self.name)

    def remove(self):
        removeVG(self.name)
        self.name= REMOVED

class LV(BlockDevice):
    def __init__( self, vg, lv_name ):
        if not isinstance(vg, VG):
            vg= VG(vg)
        if not lv_name in getLVs(vg.name, full_path=False):
            raise Exception("LV {} does not exist on VG {}".format(lv_name, vg.name))
        self.vg= vg
        self.name= lv_name
        super(LV, self).__init__(self.path)

    @property
    def path(self):
        return os.path.join(self.vg.path, self.name)
    
    def __repr__(self):
        return "{}<{},{}>".format(self.__class__.__name__, self.vg, self.name)

    def remove( self, *args, **kwargs ):
        removeLV( self.vg.name, self.name, *args, **kwargs)
        self.vg= REMOVED
        self.name= REMOVED

    def resize(self, byte_size=None, relative=None, minimum=None, maximum=None, interactive=True):
        if minimum or maximum or not interactive:
            raise Exception("Options not supported: minimum, maximum, not interactive")
        if byte_size % (1024*1024) != 0:
            raise Exception("size must be a multiple of 1 megabyte")
        byte_size= byte_size / (1024*1024)
        prefix= "" if not relative else "+" if byte_size>=0 else "-"
        if prefix=="-":
            byte_size= abs(byte_size)
        subprocess.check_call( ["lvresize", "--size", prefix+str(byte_size)], self.path)


def getVGs():
    out= subprocess.check_output("vgdisplay")
    vg_lines= sfilter('VG Name', out)
    vgs= [rsplit(x)[2] for x in vg_lines]
    return vgs

def getLVs(vg, full_path=True):
    dir="/dev/"+vg
    disks= os.listdir(dir)
    if full_path:
        return [os.path.join(dir, x) for x in disks]
    else:
        return disks

def createLV(vg, name, size="1GB"):
    print "creating LV {name} with size={size}".format(**locals())
    command="/sbin/lvcreate {vg} --name {name} --size {size}".format(**locals())
    subprocess.check_call(command, shell=True)

def removeLV(vg, name, force=True):
    print "deleting LV {name}".format(**locals())
    force_flag= "-f" if force else ""
    command="/sbin/lvremove {force_flag} {vg}/{name}".format(**locals())
    subprocess.check_call(command, shell=True)
 
def createPV(device, force=True):
    print "creating PV {device}".format(**locals())
    force_flag= "-f" if force else ""
    command="/sbin/pvcreate {force_flag} {device}".format(**locals())
    subprocess.check_call(command, shell=True)

def createVG(name, pvdevice):
    print "creating VG {name} with PV {pvdevice}".format(**locals())
    command="/sbin/vgcreate {name} {pvdevice}".format(**locals())
    subprocess.check_call(command, shell=True)

def removeVG(name):
    print "deleting VG {name}".format(**locals())
    command="/sbin/vgremove {name}".format(**locals())
    subprocess.check_call(command, shell=True)

def removePV(device):
    print "deleting PV {device}".format(**locals())
    command="/sbin/pvremove {device}".format(**locals())
    subprocess.check_call(command, shell=True)
