from abc import ABCMeta, abstractmethod
import subprocess
from pybofh import blockdevice


class BaseFilesystem(blockdevice.Data):
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

    @abstractmethod
    def fsck(self):
        raise NotImplementedError

    @classmethod
    def create(cls, device, *args, **kwargs):
        path= device.path if isinstance(device, blockdevice.BaseBlockDevice) else device
        cls._create(path, *args, **kwargs)

    @classmethod
    def _create(cls, path, *args, **kwargs):
        raise NotImplementedError


class ExtX(BaseFilesystem):
    __metaclass__= ABCMeta

    @property
    def resize_granularity(self):
        #this is the smallest that seems to work in practice,
        #although the resize2fs promises better...
        return 4*1024 #1K is the smallest we can promise

    def _resize(self, byte_size, minimum, maximum, interactive):
        self.fsck() #otherwise resize2fs refuses to proceed
        path= self.device.path
        kb_size= byte_size / 1024
        args=[]
        if interactive:
            args+= ["-p"]
        if maximum:
            pass #no more arguments
        elif minimum:
            args+=["-M", path]
        else:
            args+= [path, str(kb_size)+"K" ]
        subprocess.check_call( ["resize2fs"]+args )

    def _get_size(self):
        info= self.get_ext_info()
        bc,bs= info["Block count"], info["Block size"]
        return int(bc)*int(bs)

    def fsck(self):
        path= self.device.path
        subprocess.check_call( ["e2fsck", "-f", path] )

    def get_ext_info(self):
        out= subprocess.check_output(["dumpe2fs","-h", self.device.path])
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

    @classmethod
    def _create(cls, path, *args, **kwargs):
        command= "mkfs.{}".format(cls.NAME)
        subprocess.check_call([command, path])


class Ext2(ExtX):
    NAME="ext2"

class Ext3(ExtX):
    NAME="ext3"

class Ext4(ExtX):
    NAME="ext4"

blockdevice.register_data_class("ext2", Ext2)
blockdevice.register_data_class("ext3", Ext3)
blockdevice.register_data_class("ext4", Ext4)

