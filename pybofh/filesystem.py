from abc import ABCMeta, abstractmethod
import subprocess
from blockdevice import Resizeable


class BaseFilesystem(Resizeable):
    __metaclass__= ABCMeta
    def __init__(self, device):
        self.device= device

    @property
    def size(self):
        '''the size of the filesystem in bytes'''
        return self._get_size()

    @abstractmethod
    def _get_size(self):
        raise NotImplementedError

class Ext2(BaseFilesystem):
    NAME="ext2"
    def resize(self, byte_size=None, relative=False, minimum=False, maximum=False, interactive=True):
        if byte_size is not None and byte_size%1024!=0:
            raise Exception("Can only resize ext filesystem in multiples of 1KB")
        if relative:
            byte_size+= self.size
        kb_size= byte_size / 1024
        args=[]
        if interactive:
            args+= ["-p"]
        if maximum:
            pass #no more arguments
        elif minimum:
            args+=["-M", self.device]
        else:
            args+= [self.device, str(kb_size)+"K" ]
        subprocess.check_call( ["resize2fs"]+args )

    def _get_size(self):
        info= self.get_ext_info()
        bc,bs= info["Block count"], info["Block size"]
        return int(bc)*int(bs)

    def get_ext_info(self):
        out= subprocess.check_output(["dumpe2fs","-h", self.device])
        data={}
        for line in out.splitlines():
            try:
                k,v=line[:26].strip(),line[26:].strip()
                assert k.endswith(":")
                k=k[:-1]
                assert len(v)>0
                data[k]=v
            except AssertionError:
                pass
        return data

class Ext3(Ext2):
    NAME="ext3"

class Ext4(Ext3):
    NAME="ext4"

def Filesystem(device):
    out= subprocess.check_output(["file", "-Ls", device])
    for fsc in filesystem_classes:
        if fsc.NAME in out:
            return fsc(device)
    raise Exception("no filesystem class found for "+out)

filesystem_classes=[Ext2, Ext3, Ext4]
