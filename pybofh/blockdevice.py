# -*- encoding: utf-8 -*-

from pybofh.misc import file_type, lcm
from pybofh import shell
import os
import os.path
import weakref
from abc import ABCMeta, abstractmethod, abstractproperty
from functools import partial
import logging
import re

DM_DIR = '/dev/mapper/'
INITIALIZING_SENTINEL = 'initializing'

log = logging.getLogger(__name__)

#this is a lit of 2-tuples that is used for other modules to be able to register Data subclasses.
#each key (first tuple element) is a function that takes the block device instance and returns True iff the data of that block device can
#be represented using a certain Data subclass.
#The value (second tuple element) is a function that takes the block device instance and returns a instance
#of the Data subclass representing the data.
#example: lambda path: filetype(path)=='Ext2', Ext2Class
data_classes = []

def is_data_class_filetype(string_match, blockdevice):
    '''Checks if a blockdevice belongs to a data class by testing if a substring
    exists on its file type'''
    return string_match in file_type(blockdevice.path)

def register_data_class(match_obj, cls, priority=False):
    '''Registers a class that represents a Data subclass - Ext2, for example.
    If match_obj is a function, it should take a single argument - a block device - and return True iff cls is a appropriate representation of that block device content.
    If match_obj is a string, it checks the filetype of the block device matches that string instead'''
    if isinstance(match_obj, basestring):
        string_match = match_obj
        f = partial(is_data_class_filetype, string_match)
    elif callable(match_obj):
        f = match_obj
    else:
        raise ValueError("match_obj must be a string or a callable")
    tup = (f, cls)
    pos = 0 if priority else len(data_classes)
    data_classes.insert(pos, tup)

def get_data_class_for(blockdevice):
    for k, v in data_classes:
        if k(blockdevice):
            return v
    return None #data type not recognized

class NotReady(Exception):
    pass

class Resizeable(object):
    __metaclass__ = ABCMeta
    class ResizeError(Exception):
        pass
    class WrongSize(ResizeError):
        '''raised when asked to resize someting to a impossible sizei, or the current size is unexpected'''
        pass

    @abstractproperty
    def _size(self):
        '''Returns the size of this, in bytes'''
        pass

    @abstractproperty
    def resize_granularity(self):
        '''Returns the minimum size in bytes that this lass suports resizing on.
        Example: block size'''
        pass

    def _process_resize_size(self, byte_size=None, relative=False, approximate=True, round_up=True):
        if relative:
            byte_size += self.size
        if byte_size:
            gr = self.resize_granularity
            bad_size = (byte_size % gr) != 0
            if bad_size and not approximate:
                raise self.WrongSize("Can't resize to {}, as it's not a multiple of the resize granularity ({})".format(byte_size, gr))
            #round to resize_granularity
            byte_size = int(byte_size / gr) * gr
            if round_up and bad_size:
                byte_size += gr
        assert byte_size % self.resize_granularity == 0
        return byte_size

    def resize(self, byte_size=None, relative=False, minimum=False, maximum=False, interactive=True, approximate=True, round_up=True, **kwargs):
        '''byte_size is the new size of the filesytem.
        if relative == True, the new size will be current_size+byte_size.
        if minimum == True, will resize to the minimum size possible.
        if maximum == True, will resize to the maximum size possible.
        if approximate == True, will automatically round UP according to resize_granularity'''
        if not int(bool(byte_size)) + int(minimum) + int(maximum) == 1:
            raise Resizeable.ResizeError("""resize() arguments "byte_size", "minimum" and "maximum" are mutually exclusive""")
        if byte_size:
            byte_size = self._process_resize_size(byte_size, relative, approximate, round_up)
        log.info("Resizing {} from {} to {} bytes".format(self, self.size, byte_size))
        self._resize(byte_size, minimum, maximum, interactive, **kwargs)
        if byte_size:
            if not self.size == byte_size:
                raise Resizeable.ResizeError("After resizing {} to {} bytes, got a size of {} bytes instead".format(self, byte_size, self.size))
        return byte_size

    @abstractmethod
    def _resize(self, byte_size, minimum, maximum, interactive, **kwargs):
        pass

    @property
    def size(self):
        '''The size of this, in bytes'''
        s = self._size()
        try:
            gr = self.resize_granularity
        except Exception:
            gr = 1
        if s % gr != 0:
            raise Resizeable.WrongSize("Size of {} is {}, but expected it to be a multiple of granularity {}".format(self, s, gr))
        return s

class Openable(object):
    '''Represents an object that can be "opened". The semantics of "opened" are
    left for subclasses to define.
    The object can be "externally opened". In that case we consider it open,
    and don't try to close it when the time comes'''
    __metaclass__ = ABCMeta

    class AlreadyOpen(Exception):
        pass

    def __init__(self, exclusive=False, reentrant=False, **kwargs):
        '''Exclusive: disallows open if it is opened externally
        Reentrant: allows open twice on the same object'''
        self.was_opened = False
        self.was_fake_opened = False
        self.exclusive = exclusive
        self.reentrant = reentrant
        self._init_args = kwargs
        if reentrant:
            raise NotImplementedError #this is not properly implemented yet

    @abstractmethod
    def _externally_open_data(self):
        '''If this Openable was opened by something this object doesn't control
        ("externally open"), returns the associated data (see _open()).
        Otherwise returns None'''
        raise NotImplementedError

    @property
    def is_open(self):
        '''Returns a boolean indicating if this Openable is open.
        "open" is defined as open() being called before'''
        return self.was_opened or self.was_fake_opened

    @property
    def is_externally_open(self):
        return self._externally_open_data() is not None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, e_type, e_value, e_trc):
        self.close()

    def _on_open(self, data, true_open):
        '''Callback executed after a open.
        Data is whatever is returned by _open(), or None if true_open == True.
        true_open indicates whether _open was actually called'''
        pass

    def _on_close(self, true_close):
        '''Similar to _on_open'''
        pass

    @abstractmethod
    def _open(self, **args):
        '''opens and returns data associated with the opened thing.
        Example: the path to the block device'''
        raise NotImplementedError

    @abstractmethod
    def _close(self):
        raise NotImplementedError

    def open(self, **kwargs):
        '''opens the object'''
        open_args = dict(self._init_args)  #get constructor args
        open_args.update(kwargs)          #and open() args
        externally_open_data = self._externally_open_data()
        is_externally_open = externally_open_data is not None
        true_open = not (self.was_opened or is_externally_open)
        if self.was_opened and not self.reentrant:
            raise self.AlreadyOpen("{} was opened before".format(self))
        if not true_open and self.exclusive:
            raise self.AlreadyOpen("{} is already opened (by an external mechanism)")
        log.info("Opening {} (fake_open={})".format(self, not true_open))
        if true_open:
            result = self._open(**open_args)
            self.was_opened = True
        else:
            result = externally_open_data
            assert result is not None
            self.was_fake_opened = True
        self._on_open(result, true_open)

    def close(self):
        true_close = self.was_opened
        log.info("Closing {} (fake_close={})".format(self, not true_close))
        if true_close:
            self._close()
            self.was_opened = False
        else:
            if not self.was_fake_opened:
                raise self.AlreadyOpen("Device is already closed")
            self.was_fake_opened = False
        self._on_close(true_close)

    def __del__(self):
        if self.was_opened:
            log.warning("Deleting object without closing: {}".format(self))

class Parametrizable(object):
    '''Represents an object that accepts parameters - key-value pairs that change
    class behaviour'''
    __metaclass__ = ABCMeta
    def __init__(self, **kwargs):
        self._params = {}
        self.set_params(**kwargs)
    
    def set_params(self, **kwargs):
        in_params = set(kwargs.keys())
        accepted_keys = set(kwargs.keys()) & set(self.accepted_params)
        rejected_keys = in_params - accepted_keys 
        accepted = {k: kwargs[k] for k in accepted_keys}
        self._params.update(accepted)

    @abstractproperty
    def accepted_params(self):
        '''returns a iterable of param keys accepted by this class'''
        raise NotImplementedError

class BaseBlockDevice(Resizeable):
    __metaclass__=ABCMeta
    def __init__(self, device_path, skip_validation=False):
        if not skip_validation:
            if not os.path.exists(device_path):
                raise Exception("Blockdevice path {} does not exist".format(device_path))
        self._set_path(device_path)
        self._last_data = None
        self._last_data_class = None

    def _size(self):
        return size(self.path)

    def _set_path(self, device_path):
        if device_path and not os.path.exists(device_path):
            raise Exception("Failed to find block device {}".format(device_path))
        self._path = device_path

    @property
    def path(self):
        '''The path to the file representing the block device'''
        if self._path is None:
            raise NotReady("Block device is not ready (path not set)")
        if not os.path.exists(self._path):
            raise NotReady("Block device path doesn't exist")
        return self._path

    def __repr__(self):
        try:
            path = self.path
        except NotReady:
            path = None
        return "{}<{}>".format(self.__class__.__name__, path)

 
    @property
    def data(self):
        '''returns an object representing the block device data.
        This will usually be a filesystem (but also a LUKS device, etc)'''
        current_data_class = get_data_class_for(self)
        if current_data_class != self._last_data_class:
            self._last_data_class = current_data_class
            self._last_data = current_data_class(self)
        return self._last_data

    def resize(self, byte_size=None, relative=False, minimum=False, maximum=False, interactive=True, approximate=True, round_up=False, **kwargs):
        '''The no_data argument is needed to resize a blockdevice, to make sure the user knows the data won't be resized along with it'''
        dont_resize_data_arg = 'no_data'
        if not kwargs.get(dont_resize_data_arg, False):
            raise Resizeable.ResizeError("DATA LOSS WARNING! Resizing a blockdevice doesn't resize its data! If you know what you're doing, provide {}=True argument to resize()".format(dont_resize_data_arg))
        Resizeable.resize(self, byte_size, relative, minimum, maximum, interactive, approximate, round_up)

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
    def __init__(self, blockdevice_or_path):
        self.device = blockdevice(blockdevice_or_path)

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, self.device)

class OuterLayer(Data):
    '''A outer layer on a layered block device.
    Example: the encrypted part of a LUKS device
    Resizing a OuterLayer also resizes the corresponding InnerLayer'''
    __metaclass__=ABCMeta

    def __init__(self, blockdevice, **kwargs):
        Data.__init__(self, blockdevice)
        ilc = self._inner_layer_class
        self._inner = INITIALIZING_SENTINEL
        self._inner = ilc(self, **kwargs)
        try:
            #this is repeated on InnerLayer._on_open, in case NotReady is raised
            self._sanity_check()
        except NotReady:
            pass
    
    def _sanity_check(self):
        assert self.size == self.device.size #be careful if you need to remove this, it's an unwritten assumption throughout layer code
        assert self.inner.size == self.size - self.overhead #note overhead is calculated as the difference between them right now

    @property
    def inner(self):
        '''returns the InnerLayer.''' 
        return self._inner

    @property
    def overhead(self):
        try:
            inner_size = self.inner.size
        except NotReady:
            raise NotReady("The inner layer is not open")
        oh = self.size - inner_size
        assert oh >= 0
        assert oh < 16 * 2**20 #16MB, just a sanity check, may need to be raised
        return oh   

    @abstractproperty
    def _inner_layer_class(self):
        raise NotImplementedError

class InnerLayer(BaseBlockDevice, Openable):
    '''A inner layer on a layered block device.
    Example: the decrypted part of a LUKS device.
    This is Openable.
    Resizing a InnerLayer also resizes the corresponding OuterLayer''' 
    __metaclass__=ABCMeta

    def __init__(self, outer_layer, **kwargs):
        BaseBlockDevice.__init__(self, None, skip_validation=True)
        Openable.__init__(self, **kwargs)
        if outer_layer.inner is not INITIALIZING_SENTINEL:
            raise Exception("InnerLayer instances should not be created directly - use OuterLayer.inner instead")
        self._outer = weakref.ref(outer_layer)  #avoid GC cyclic reference for __del__, see http://eli.thegreenplace.net/2009/06/12/safely-using-destructors-in-python/

    @property
    def outer(self):
        o = self._outer() # get from weakref
        if o is None:
            raise Exception("The outer layer has been GC'd - did you drop all references to it?")
        return o

    def _externally_open_data(self):
        outer_path = self.outer.device.path
        return get_blockdevice_child(outer_path)

    def _on_open(self, path, true_open):
        assert os.path.exists(path)
        self._set_path(path)
        self.outer._sanity_check()

    def _on_close(self, true_close):
        self._set_path(None)


def get_device_path(device_or_path):
    '''given either a device object or a device path, returns device path'''
    try:
        path = device_or_path.path
    except AttributeError:
        path = device_or_path
    assert os.path.exists(path)
    return path

class BlockDeviceStack(Resizeable, Openable):
    '''Represents a stack of blockdevices / Data.
    Example: Ext4 on top of LUKS on top of DRBD on top of a LV'''
    def __init__(self, outermost_layer, **kwargs):
        Resizeable.__init__(self)
        Openable.__init__(self, **kwargs)
        if isinstance(outermost_layer, InnerLayer):
            outermost_layer = self.get_outer(outermost_layer).device
        elif isinstance(outermost_layer, Data):
            outermost_layer = outermost_layer.device
        else:
            outermost_layer = blockdevice(outermost_layer) 
        self._outermost = outermost_layer
        self._layers = None

    def _open(self, **kwargs):
        open_args = kwargs
        return self._compute_and_open_layers(open_args)

    def _close(self):
        for layer in reversed(self.layers[1:]):
            #process in innermost to outermost order, ignore innermost layer
            layer.close()

    def _on_open(self, layers, true_open):
        self._layers = layers
        self._sanity_check()

    def _on_close(self, true_close):
        self._layers = None

    def _externally_open_data(self):
        return None # this can never be opened externally

    def _sanity_check(self):
        for layer in self.layers[:-1]:
            layer.data._sanity_check()
        assert self.innermost.size == self.innermost.data.size
        
    @property
    def layers(self):  # could be a path
        '''Returns the layers of this stack. This is simply a iterable of 
        BaseBlockDevice, ordered from outermost to innermost'''
        if self._layers is None:
            raise NotReady("BlockDeviceStack wasn't opened yet")
        return self._layers

    def _compute_and_open_layers(self, open_args):
        layers =[] #outermost to innermost order
        current_layer = self._outermost
        while current_layer is not None:
            layers.append(current_layer)
            current_layer = self._next_layer(current_layer, open_args)
        return layers
 
    @staticmethod
    def _next_layer(layer, open_args):
        assert isinstance(layer, BaseBlockDevice)
        if layer.data is None:
            return None
        if not isinstance(layer.data, OuterLayer):
            return None
        outer = layer.data
        inner = outer.inner
        inner.open(**open_args)
        return inner

    @property
    def outermost(self):
        return self._outermost

    @property
    def innermost(self):
        return self.layers[-1]

    @property
    def resize_granularity(self):
        granularities = [l.resize_granularity for l in self.layers]
        return lcm(*granularities)

    def _size(self):
        return self.outermost.size

    @property
    def total_overhead(self):
        return sum(l.data.overhead for l in self.layers[:-1])

    def _resize(self, byte_size, minimum, maximum, interactive):
        if maximum or minimum:
            raise NotImplementedError("maximum or minimum options not available for BlockDeviceStack")
        granularity = self.resize_granularity
        expansion = True if maximum else False if minimum else byte_size>=self.outermost.size
        target_size = byte_size
        common_args = {"minimum": minimum, "maximum": maximum, "interactive": interactive}
        if expansion:
            common_args["round_up"]= False
            #resize outermost blockdevice...
            self.outermost.resize(byte_size=target_size, no_data=True, **common_args)
            for layer in self.layers[:-1]:
                #and all the data (Outerlayer) of each layer, which also resizes the InnerLayer (next layer)
                inner_size = layer.data.inner.size
                assert layer.data.inner.size == layer.data.size - layer.data.overhead
                layer.data.resize(byte_size=target_size, **common_args)
                assert layer.data.inner.size > inner_size #make sure the OuterLayer resized the InnerLayer
                assert layer.data.inner.size == layer.data.size - layer.data.overhead
                log.debug("blabla over {}, gran {}, target {}".format(layer.data.overhead, granularity, target_size))
                target_size = layer.data.inner.size
                log.debug(target_size)
            #finally, resize the data of the innermost layer (which is not an OuterLayer)
            self.innermost.data.resize(byte_size=self.innermost.size, **common_args)
        else: #reduction
            common_args["round_up"]= True
            target_size = target_size - self.total_overhead
            #resize innermost data...
            target_size = self.innermost.data.resize(target_size, **common_args)
            for layer in list(reversed(self.layers))[:-1]:
                #and all blockdevices(InnerLayer), from the innermost to outermost, which also resizes the OuterLayer
                outer_size = layer.outer.size
                assert layer.size == layer.outer.size - layer.outer.overhead
                layer.resize(target_size, no_data=True, **common_args)
                assert layer.outer.size < outer_size #make sure the Innerlayer resized the OuterLayer
                assert layer.size == layer.outer.size - layer.outer.overhead
                target_size = layer.size + layer.outer.overhead
            #finally, resize the outermost layer (which is not an InnerLayer)
            self.outermost.resize(self.outermost.data.size, no_data=True, **common_args)
        self._sanity_check()

    def layer_and_data_sizes(self):
        sizes = []
        for layer in self.layers:
            sizes.append(layer.size)
            sizes.append(layer.data.size)
        return sizes


    def __repr__(self):
        return "{}<{}>".format(self.__class__.__name__, self.outermost.path)

    def __str__(self):
        LAYER_SEP="\n  "
        def layer_to_str(l):
            bd_s =   "{:<40} size={}".format(l, l.size)
            data_s = "{:<40} size={}".format(l.data, l.data.size if l.data!=None else "?")
            return LAYER_SEP.join((data_s, bd_s))
        try:
            substrings = map(layer_to_str, reversed(self.layers))
            header = repr(self) + " with layers:"
            return LAYER_SEP.join([header] + substrings)
        except NotReady:
            return self.__repr__()


def devicemapper_info(device_or_path):
    REGEX = r'(.*): +(.*)\n'
    ALL_KEYS= ['Major, minor', 'Name', 'Tables present', 'UUID', 'Read Ahead', 'Number of targets', 'State', 'Open count', 'Event number']
    MIN_KEYS= ['Major, minor', 'Name', 'UUID', 'State', 'Open count']
    def convert_value(x):
        try: 
            return int(x)
        except ValueError:
            return x
    path = get_device_path(device_or_path)
    command = ['/sbin/dmsetup', 'info', path]
    output = shell.get().check_output(command)
    kv_pairs = re.findall(REGEX, output)
    d = {k: convert_value(v) for k, v in kv_pairs}
    assert set(d.keys()) > set(MIN_KEYS)
    return d

class LsblkNode(object):
    def __init__(self, name, major, minor, size, ro, type, mountpoint, parent=None):
        assert mountpoint != '' # if it's not mounted, should be None
        if not type in ('disk', 'part', 'lvm', 'crypt', 'loop', 'raid1', "md", None):
            raise Exception("Unexpected lsblk node type: {}".format(type))
        self.children = []
        self.name = name
        self.major, self.minor = int(major), int(minor)
        self.size = size #string. example: 43G
        self.ro = bool(int(ro))
        self.type = type
        self.mountpoint = mountpoint
        self.parent = parent

    def add_child(self, node):
        self.children.append(node)
        node.parent = self

    def iterate(self):
        #Returns all the tree nodes in depth-first-search order
        yield self
        for c in self.children:
            for sub in c.iterate():
                yield sub

    def find_node(self, node_name, return_one=True):
        '''finds nodes in the tree that mach the given name'''
        l = (self,) if self.name==node_name else ()
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
            i = line.index(TREE_SYMBOL)
            assert i%2==1 #each indent is two spaces, plus an extra tree char
            return (i+1)/2
        except ValueError:
            return 0
    def parse_line(line):
        try:
            text = line[line.index(TREE_SYMBOL)+len(TREE_SYMBOL):]
        except ValueError:
            text = line #this is probably a 0-indentation line
        data = text.split()
        if len(data)==6:
            #mountpoint might be missing
            data.append(None)
        assert len(data) == 7
        assert ":" in data[1] #major:minor
        name, majmin, rm, size, ro, type, mountpoint = data
        maj, min = majmin.split(":")
        return name, maj, min, size, ro, type, mountpoint
    command = ['/bin/lsblk']
    output = shell.get().check_output(command)
    output = output.decode('utf-8') #TODO: get system encoding
    #split lines and verify format
    lines = output.splitlines()
    assert lines[0].split()==FIELDS
    lines =lines[1:] #remove header
    #parse tree
    root = LsblkNode.create_root()
    current_dev_at_indent = {-1:root}
    for line in lines:
        indent = indent_level(line)
        data = parse_line(line)
        node = LsblkNode(*data)
        parent = current_dev_at_indent[indent-1]
        parent.add_child(node)
        current_dev_at_indent[indent]= node
    return root

def dm_get_child(blockdevice_path):
    '''Given a devicemapper block device, returns its child, if any (according to lsblk)'''
    root = lsblk()
    path = os.path.realpath(blockdevice_path)
    assert os.path.exists(path)
    outer_dir, outer_name = os.path.split(path)
    assert outer_dir == DM_DIR
    outer_node = root.find_node(outer_name)
    if len(outer_node.children)==0:
        return None
    assert len(outer_node.children)==1 #a device should have at most 1 child...?
    c1= outer_node.children[0]
    path = DM_DIR + c1.name
    assert os.path.exists(path)
    return path  

def size(blockdevice_path):
    '''return the of the block device in bytes'''
    return int(shell.get().check_output(('/sbin/blockdev', '--getsize64', blockdevice_path)))

def get_blockdevice_child(path):
        root = lsblk()
        path = os.path.realpath(path)
        try:
            dm_name = devicemapper_info(path)['Name']
        except Exception as e:
            #might not be a devicemapper device
            dm_name = path.split("/")[-1]
        outer_node = root.find_node(dm_name)
        if not len(outer_node.children):
            return None
        c1= outer_node.children[0]
        path = DM_DIR + c1.name
        assert os.path.exists(path)
        return path

def blockdevice_from_path(path):
    return BlockDevice(path)

def blockdevice(path_or_object):
    '''Returns a generic BlockDevice for a path.
    If the provided argument is already a BlockDevice, return it unchanged'''
    if isinstance(path_or_object, basestring):
        return blockdevice_from_path(path_or_object)
    elif isinstance(path_or_object, BaseBlockDevice):
        return path_or_object
    else:
        raise Exception("Can't get a blockdevice from {}".format(path_or_object))
