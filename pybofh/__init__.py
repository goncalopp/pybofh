from functools import partial

import my_logging as logging
import blockdevice
import mount
import filesystem
import btrfs
import xen
import lvm
import drbd
import settingsmodule

def reverse_operation( f, args, kwargs ):
    if f==lvm.createLV:
        return lvm.removeLV, args[:2], {} #vg, lv_name
    raise Exception("Reverse operation not found for "+str(f))

from atomic_operations import AtomicContext

settings = settingsmodule.Settings()
__all__=[ blockdevice, mount, filesystem, btrfs, xen, lvm, drbd, AtomicContext ]
