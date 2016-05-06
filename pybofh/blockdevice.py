from pybofh.misc import file_type
import subprocess
import os
from abc import ABCMeta, abstractmethod

#this is a lit of 2-tuples that is used for other modules to be able to register Data subclasses.
#each key (first tuple element) is a function that takes the block device instance and returns True iff the data of that block device can
#be represented using a certain Data subclass. 
#The value (second tuple element) is a function that takes the block device instance and returns a instance
#of the Data subclass representing the data.
#example: lambda path: filetype(path)=='Ext2', Ext2Class
data_classes=[] 
 
def register_data_class( string_match, cls, priority=False ):
    '''registers a certain string such that, if the result of calling (the command) file of a block device
    contains the string, we should use cls(path) to represent the block device data'''
    k= lambda bd: string_match in file_type(bd.path)
    tup= (k,cls)
    if priority:
        data_classes.insert(0, tup)
    else:
        data_classes.append( tup )
 
class BlockDevice( object ):
    def __init__(self, device_path):
        self._set_path( device_path )

    @property
    def size(self):
        '''return the of the block device in bytes'''
        return int(subprocess.check_output(['blockdev', '--getsize64', self.path]))

    def _set_path(self, device_path):
        if device_path and not os.path.exists(device_path):
            raise Exception("Failed to find block device {}".format(device_path))
        self._path= device_path

    @property
    def path(self):
        '''The path to the file representing the block device'''
        if self._path is None:
            raise Exception("Block device is not ready (path not set)")
        return self._path

    def resize(self, byte_size=None, relative=False, minimum=False, maximum=False, interactive=True):
        '''byte_size is the new size of the filesytem.
        if relative==True, the new size will be current_size+byte_size.
        if minimum==True, will resize to the minimum size possible.
        if maximum==True, will resize to the maximum size possible.'''
        raise NotImplementedError  #implementation up to subclasses

    def __repr__(self):
        return "{}< {} >".format(self.__class__.__name__, self.path)
 
    @property
    def data(self):
        '''returns an object representing the block device data.
        This will usually be a filesystem (but also a LUKS device, etc)'''
        for k,v in data_classes:
            if k(self):
                return v(self)
        return None #data type not recognized
 
class Data(object):
    __metaclass__=ABCMeta
    '''A representation of the data of a block device.
    Example: the data of a LV could be LUKS'''
    def __init__(self, blockdevice):
        if not isinstance(blockdevice, BlockDevice):
            raise Exception("You tried to initialize a new Data object without providing a parent block device")
        self.blockdevice= blockdevice

class OuterLayer(Data):
    '''A outer layer on a layered block device.
    Example: the encrypted part of a LUKS device
    This acts as a context manager'''
    __metaclass__=ABCMeta
    
    @property
    @abstractmethod
    def inner(self):
        '''returns the InnerLayer''' 
        pass

class InnerLayer(BlockDevice):
    '''A inner layer on a layered block device.
    Example: the decrypted part of a LUKS device.''' 
    __metaclass__=ABCMeta
    class AlreadyOpen(Exception):
        pass

    def __init__(self, outer_layer):
        self.outer= outer_layer
        self.was_opened= False
        super(InnerLayer, self).__init__(None)

    def __enter__(self):
        if (self.is_open and not self.allow_enter_if_open) or self.was_opened:
            raise self.AlreadyOpen("block device was already opened (by an unknown mechanism)")
        if not self.is_open:
            self.open()
            self.was_opened= True
        return self
    
    def __exit__( self, e_type, e_value, e_trc ):
        if self.was_opened:
            self.close()
            self.was_opened= False

    @property
    @abstractmethod
    def is_open(self):
        pass
    
    def open( self ):
        p= self._open()
        self._set_path( p )

    def close( self ):
        self._close()
        self._set_path( None )

    @abstractmethod
    def _open( self ):
        '''opens and returns the path to the block device'''
        pass

    @abstractmethod
    def _close( self ):
        pass


