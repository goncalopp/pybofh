import os
from functools import partial

DEVICE_DIR='/dev/'
NAMED_DEVICE_PREFIX='drbd_'
NUMBERED_DEVICE_PREFIX="drbd"

def devices_list(named=True, absolute_paths=True):
    assert NAMED_DEVICE_PREFIX.startswith(NUMBERED_DEVICE_PREFIX) #rewrite code carefully if this ever breaks
    def is_device(x):
        c1= x.startswith(NAMED_DEVICE_PREFIX) and x!=NAMED_DEVICE_PREFIX
        c2= x.startswith(NUMBERED_DEVICE_PREFIX) and x!=NUMBERED_DEVICE_PREFIX
        return c1 or c2
    def is_named(x):
        return  NAMED_DEVICE_PREFIX in x
    all_devices= filter( is_device, os.listdir(DEVICE_DIR))
    filter_= is_named if named else lambda x: not is_named(x)
    if absolute_paths:
        all_devices= [DEVICE_DIR+d for d in all_devices]
    return list(filter(filter_, all_devices))

def resources_list(named=True):
    def strip_prefix(x):
        prefix= NAMED_DEVICE_PREFIX if named else NUMBERED_DEVICE_PREFIX 
        return x[len(prefix):] 
    devices= devices_list(named=named, absolute_paths=False)
    resources= map(strip_prefix, devices)
    return resources
