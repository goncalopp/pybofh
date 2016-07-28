# -*- encoding: utf-8 -*-

from pybofh.misc import file_type
import subprocess
import os
import os.path
from abc import ABCMeta, abstractmethod, abstractproperty
from functools import partial
import re

DM_DIR= '/dev/mapper/'

#this is a lit of 2-tuples that is used for other modules to be able to register Data subclasses.
#each key (first tuple element) is a function that takes the block device instance and returns True iff the data of that block device can
#be represented using a certain Data subclass. 
#The value (second tuple element) is a function that takes the block device instance and returns a instance
#of the Data subclass representing the data.
#example: lambda path: filetype(path)=='Ext2', Ext2Class
data_classes=[] 
 
def is_data_class_filetype( string_match, blockdevice ):
    '''Checks if a blockdevice belongs to a dat a class by testing if a substring
    exists on its file type'''
    return string_match in file_type(blockdevice.path)

def register_data_class( match_obj, cls, priority=False ):
    '''Registers a class that represents a Data subclass - Ext2, for example.
    If match_obj is a function, it should take a single argument - a block device path - and return True iff cls is a appropriate representation of that block device content.
    If match_obj is a string, it checks the filetype of the bock device matches that string instead'''
    if isinstance(match_obj, basestring):
        string_match= match_obj
        f= partial(is_data_class_filetype, string_match)
    elif callable(match_obj):
        f= match_obj
    else:
        raise ValueError("match_obj must be a string or a callable")
    tup= (f,cls)
    pos= 0 if priority else len(data_classes)
    data_classes.insert(pos, tup)
 
class Resizeable(object):
    __metaclass__=ABCMeta
    class WrongSize(Exception):
        '''raised when asked to resize someting to a impossible size'''
        pass

    @abstractproperty
    def size(self):
        '''returns the size of this, in bytes'''
        pass

    def _process_resize_size(self, byte_size=None, relative=False, approximate=True, round_up=False):
        if relative:
            byte_size+= self.size
        if byte_size:
            gr= self.resize_granularity
            bad_size= (byte_size % gr)!=0
            if bad_size and not approximate:
                raise self.WrongSize("Can't resize to {}, as it's not a multiple of the resize granularity ({})".format(byte_size, gr))
            #round to resize_granularity
            byte_size= int(byte_size / gr) * gr
            if round_up and bad_size:
                byte_size+= gr
        assert byte_size % self.resize_granularity == 0
        return byte_size

    def resize(self, byte_size=None, relative=False, minimum=False, maximum=False, interactive=True, approximate=True, round_up=False, **kwargs ):
        '''byte_size is the new size of the filesytem.
        if relative==True, the new size will be current_size+byte_size.
        if minimum==True, will resize to the minimum size possible.
        if maximum==True, will resize to the maximum size possible.
        if approximate==True, will automatically round DOWN according to resize_granularity'''
        assert int(bool(byte_size)) + int(minimum) + int(maximum) == 1
        byte_size= self._process_resize_size(byte_size, relative, approximate, round_up)
        self._resize(byte_size, minimum, maximum, interactive, **kwargs)
        assert self.size == byte_size

    @abstractmethod
    def _resize(self, byte_size, minimum, maximum, interactive):
        pass


    @abstractproperty
    def resize_granularity(self):
        '''Returns the minimum size in bytes that this lass suports resizing on.
        Example: block size'''
        pass


class BaseBlockDevice( Resizeable ):
    __metaclass__=ABCMeta
    def __init__(self, device_path, skip_validation=False):
        if not skip_validation:
            if not os.path.exists(device_path):
                raise Exception("Blockdevice path {} does not exist".format(device_path))
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

    def __repr__(self):
        return "{}<{}>".format(self.__class__.__name__, self.path)
 
    @property
    def data(self):
        '''returns an object representing the block device data.
        This will usually be a filesystem (but also a LUKS device, etc)'''
        for k,v in data_classes:
            if k(self):
                return v(self)
        return None #data type not recognized

class BlockDevice(BaseBlockDevice):
    @property
    def resize_granularity(self):
        raise NotImplementedError

    def _resize(self, *args, **kwargs):
        raise NotImplementedError
 
class Data(Resizeable):
    __metaclass__=ABCMeta
    '''A representation of the data of a block device.
    Example: the data of a LV could be LUKS'''
    def __init__(self, blockdevice):
        if isinstance(blockdevice, basestring):
            path= blockdevice #assume this is a path to a blockdevice
            blockdevice= BlockDevice(path)
        if not isinstance(blockdevice, BaseBlockDevice):
            raise Exception("You tried to initialize a new Data object without providing a parent block device")
        self.blockdevice= blockdevice

class OuterLayer(Data):
    '''A outer layer on a layered block device.
    Example: the encrypted part of a LUKS device
    This acts as a context manager'''
    __metaclass__=ABCMeta
    
    @property
    def inner(self):
        '''returns the InnerLayer. 
        This is a convenience property to call get_inner without arguments''' 
        return self.get_inner()

    @abstractmethod
    def get_inner(self, *args, **kwargs):
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
        super(InnerLayer, self).__init__(None, skip_validation=True)

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
    def is_open(self):
        root= lsblk()
        path= os.path.realpath(self.outer.blockdevice.path)
        dm_name= devicemapper_info(path)['Name']
        outer_node= root.find_node(dm_name)
        if not len(outer_node.children):
            return None
        c1= outer_node.children[0]
        path= DM_DIR + c1.name
        assert os.path.exists(path)
        return path
    
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

def get_device_path(device_or_path):
    '''given either a device object or a device path, returns device path'''
    try:
        path= device_or_path.path
    except AttributeError:
        path= device_or_path
    assert os.path.exists(path)
    return path


def devicemapper_info(device_or_path):
    REGEX= r'(.*): +(.*)\n'
    ALL_KEYS= ['Major, minor', 'Name', 'Tables present', 'UUID', 'Read Ahead', 'Number of targets', 'State', 'Open count', 'Event number']
    MIN_KEYS= ['Major, minor', 'Name', 'UUID', 'State', 'Open count']
    def convert_value(x):
        try:
            return int(x)
        except ValueError:
            return x
    path= get_device_path(device_or_path)
    command= ['/sbin/dmsetup', 'info', path]
    output= subprocess.check_output(command)
    kv_pairs= re.findall(REGEX, output)
    d= {k: convert_value(v) for k,v in kv_pairs}
    assert set(d.keys()) > set(MIN_KEYS)
    return d

class LsblkNode(object):
    def __init__(self, name, major, minor, size, ro, type, mountpoint, parent=None):
        assert mountpoint!='' #if it's not mounted, should be None
        assert type in ('disk', 'part', 'lvm', 'crypt', None)
        self.children= []
        self.name= name
        self.major, self.minor= int(major), int(minor)
        self.size= size #string. example: 43G
        self.ro= bool(int(ro))
        self.type= type
        self.mountpoint= mountpoint
        self.parent= parent

    def add_child(self, node):
        self.children.append(node)
        node.parent= self

    def iterate(self):
        #Returns all the tree nodes in depth-first-search order
        yield self
        for c in self.children:
            for sub in c.iterate():
                yield sub

    def find_node(self, node_name, return_one=True):
        '''finds nodes in the tree that mach the given name'''
        l= (self,) if self.name==node_name else ()
        for c in self.children:
            l+= c.find_node(node_name, return_one=False)
        if return_one:
            if len(l)!=1:
                raise Exception("node not found: {} (or multiple matches)".format(node_name))
            return l[0]
        return l

    def __repr__(self):
        return "{}<{}, {}>".format(self.__class__.__name__, self.name, self.type)

    @staticmethod
    def create_root():
        return LsblkNode("lsblk_root", -1, -1, None, 1, None, None)

def lsblk():
    '''Parses the lsblk command output to get block device dependencies/state
    Outputs (the root node of) a tree.'''
    TREE_SYMBOL= u'─'
    FIELDS=['NAME', 'MAJ:MIN', 'RM', 'SIZE', 'RO', 'TYPE', 'MOUNTPOINT']
    def indent_level(line):
        try:
            i= line.index(TREE_SYMBOL)
            assert i%2==1 #each indent is two spaces, plus an extra tree char
        except ValueError:
            return 0
        return i/2
    def parse_line(line):
        try:
            text= line[line.index(TREE_SYMBOL)+len(TREE_SYMBOL):]
        except ValueError:
            text= line #this is probably a 0-indentation line
        data= text.split()
        if len(data)==6:
            #mountpoint might be missing
            data.append(None)
        assert len(data) == 7
        assert ":" in data[1] #major:minor
        name, majmin, rm, size, ro, type, mountpoint= data
        maj,min= majmin.split(":")
        return name, maj, min, size, ro, type, mountpoint
    command= ['/bin/lsblk']
    output= subprocess.check_output(command)
    output= output.decode('utf-8') #TODO: get system encoding
    #split lines and verify format
    lines= output.splitlines()
    assert lines[0].split()==FIELDS
    lines=lines[1:] #remove header
    #parse tree
    root= LsblkNode.create_root()
    current_dev_at_indent= {-1:root}
    for line in lines:
        indent= indent_level(line)
        data= parse_line(line)
        node= LsblkNode(*data)
        parent= current_dev_at_indent[indent-1]
        parent.add_child(node)
        current_dev_at_indent[indent]= node
    return root

def dm_get_child(blockdevice_path):
    '''Given a devicemapper block device, returns its child, if any (according to lsblk)'''
    root= lsblk()
    path= os.path.realpath(blockdevice_path)
    assert os.path.exists(path)
    outer_dir, outer_name= os.path.split(path)
    assert outer_dir==DM_DIR
    outer_node= root.find_node(outer_name)
    if len(outer_node.children)==0:
        return None
    assert len(outer_node.children)==1 #a device should have at most 1 child...?
    c1= outer_node.children[0]
    path= DM_DIR + c1.name
    assert os.path.exists(path)
    return path  
