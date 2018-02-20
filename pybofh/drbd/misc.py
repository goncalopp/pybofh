import re
import os
from functools import partial
import pybofh.misc

DEVICE_DIR='/dev/'
NAMED_DEVICE_PREFIX='drbd_'
NUMBERED_DEVICE_PREFIX="drbd"
CONFIG_DIR='/etc/drbd.d'
RESOURCE_CONFIGFILE_EXT='.res'

def devices_list(named=True, absolute_paths=True, include_prefix=True):
    '''list system block devices provided by drbd (typically /dev/drbdX).
    The list is obtained through directory listing /dev, so the result will not contain any unavailable resources, and may contain resources for which there is no configuration.
    If named is True (default), only returns named devices (e.g.: drbd_myname) - otherwise only
    numbered devices are returned (e.g.: drbd0).
    If include_prefix is False, the prefix (e.g.: "drbd" or "drbd_") is not included in the output.
    '''
    assert NAMED_DEVICE_PREFIX.startswith(NUMBERED_DEVICE_PREFIX) #rewrite code carefully if this ever breaks
    assert not(absolute_paths and not include_prefix)
    def is_device(x):
        c1= x.startswith(NAMED_DEVICE_PREFIX) and x!=NAMED_DEVICE_PREFIX
        c2= x.startswith(NUMBERED_DEVICE_PREFIX) and x!=NUMBERED_DEVICE_PREFIX
        return c1 or c2
    def is_named(x):
        return  x.startswith(NAMED_DEVICE_PREFIX)
    def remove_prefix(x):
        prefix= NAMED_DEVICE_PREFIX if named else NUMBERED_DEVICE_PREFIX
        assert x.startswith(prefix)
        return x[len(prefix):]
    all_devices= filter( is_device, pybofh.misc.list_dir(DEVICE_DIR))
    filter_naming= is_named if named else lambda x: not is_named(x)
    devices= filter(filter_naming, all_devices)
    if not include_prefix:
        assert not absolute_paths #with removed prefixes, they are no longer valid paths
        devices= map(remove_prefix, devices)
    if absolute_paths:
        devices= [DEVICE_DIR+d for d in devices]
    return list(devices)

def config_files():
    '''Returns the list of resource configuration files'''
    names= filter(lambda x:x.endswith( RESOURCE_CONFIGFILE_EXT ), pybofh.misc.list_dir(CONFIG_DIR))
    paths= [os.path.join(CONFIG_DIR,name) for name in names]
    return paths

def config_addresses(resource_file):
    '''returns the addresses in a resource config file'''
    data = pybofh.misc.read_file(resource_file)
    addresses = re.findall('address +(.*?);', data)
    addresses = map(str.strip, addresses)
    return addresses

def config_minor(resource_file):
    '''returns the minor number in a resource config file'''
    data = pybofh.misc.read_file(resource_file)
    minors = re.findall('minor ([0-9]+)', data)
    assert len(minors) == 1
    return int(minors[0])

def highest_port():
    '''returns the highest port used in the config files
    Useful for allocating a new one, if it's a continuous group.
    Assumes the same port is used in the local and remote hosts'''
    files = config_files()
    address_pairs = map(config_addresses, files)
    addresses = [ap[0] for ap in address_pairs]
    ports = [addr.split(":")[1] for addr in addresses]
    ports = map(int, ports)
    return max(ports)

def highest_minor():
    '''returns the highest minor number used in the config files
    Useful for allocating a new one, if it's a continuous group.'''
    files = config_files()
    minors = map(config_minor, files)
    return max(minors)

def resources_list():
    '''Lists the names of all resourses provided by configuration files in CONF_DIR'''
    def get_resource_name( cfgtxt ):
        i1= cfgtxt.index('resource ')+len('resource ')
        i2= cfgtxt.index(' ', i1)
        return cfgtxt[i1:i2]
    filenames= config_files()
    cfgtxts= [pybofh.misc.read_file(fn) for fn in filenames]
    return map(get_resource_name, cfgtxts)

def metadata_size(resource_size_bytes):
    '''Calculates the approximated upper-bound of the drbd resource metadata size
    The result is in bytes
    Based on http://www.drbd.org/en/doc/users-guide-83/ch-internals
    I believe this assumes 512 bytes sectors, but that might be internal to DRBD.'''
    mb = 2**20
    metadata_size_bytes = (int(resource_size_bytes / mb / 32768 ) + 1) * mb
    return metadata_size_bytes
