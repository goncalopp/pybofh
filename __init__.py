from functools import partial

import disks
import btrfs
import domus
import lvm

def reverse_operation( f, args, kwargs ):
    if f==lvm.createLV:
        return lvm.removeLV, args[:2], {} #vg, lv_name
    raise Exception("Reverse operation not found for "+str(f))

from atomic_operations import AtomicOperationSequence
Atomic= partial( AtomicOperationSequence, reverse_operation ) 
