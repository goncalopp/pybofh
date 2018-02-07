from . import settingsmodule
# forward declaration, so package modules can use it
settings = settingsmodule.Settings()

from functools import partial

from . import blockdevice
from . import mount
from . import filesystem
from . import btrfs
from . import xen
from . import lvm
from . import drbd
from .atomic_operations import AtomicContext
