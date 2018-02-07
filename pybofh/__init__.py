import settingsmodule
# forward declaration, so package modules can use it
settings = settingsmodule.Settings()

from functools import partial

import blockdevice
import mount
import filesystem
import btrfs
import xen
import lvm
import drbd
from atomic_operations import AtomicContext
