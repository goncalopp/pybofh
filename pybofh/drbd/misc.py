import os
from functools import partial

DEVICE_DIR='/dev/'
NAMED_DEVICE_PREFIX='drbd_'
NUMBERED_DEVICE_PREFIX="drbd"
CONFIG_DIR='/etc/drbd.d'
RESOURCE_CONFIGFILE_EXT='.res'

def devices_list(named=True, absolute_paths=True, include_prefix=True):
    '''list system block devices provided by drbd (typically /dev/drbdX).
    Note this will not list any unavailable resources'''
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
    all_devices= filter( is_device, os.listdir(DEVICE_DIR))
    filter_naming= is_named if named else lambda x: not is_named(x)
    devices= filter(filter_naming, all_devices)
    if not include_prefix:
        devices= map(remove_prefix, devices)
    if absolute_paths:
        devices= [DEVICE_DIR+d for d in devices]
    return list(devices)

def resources_list():
    '''Lists the names of all resourses provided by configuration files in CONF_DIR'''
    def get_resource_name( cfgtxt ):
        i1= cfgtxt.index('resource ')+len('resource ')
        i2= cfgtxt.index(' ', i1)
        return cfgtxt[i1:i2]
    filenames= filter(lambda x:x.endswith( RESOURCE_CONFIGFILE_EXT ), os.listdir(CONFIG_DIR))
    cfgtxts= [open(os.path.join(CONFIG_DIR,fn)).read() for fn in filenames]
    return map(get_resource_name, cfgtxts)

