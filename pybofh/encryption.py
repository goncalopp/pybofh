"""LUKS utilities"""

import logging
import os, os.path
import struct
from pybofh import shell
from pybofh import blockdevice
from pybofh import misc

LUKS_SECTOR_SIZE = 512 #this seems hardcoded into luks, so hopefully it's safe to keep it there
CRYPTSETUP = '/sbin/cryptsetup'

log = logging.getLogger(__name__)

class Encrypted(blockdevice.OuterLayer, blockdevice.Parametrizable):
    """A LUKS encrypted blockdevice"""
    def __init__(self, bd, **kwargs):
        blockdevice.OuterLayer.__init__(self, bd)
        blockdevice.Parametrizable.__init__(self, **kwargs)

    @property
    def _inner_layer_class(self):
        return Decrypted

    def _size(self):
        try:
            header_size = luks_data_offset(self.device.path)
            return header_size + self.inner.size # can be different from self.device.size, if it's been resized
        except blockdevice.NotReady:
            #there's no way to know, just return the enclosing blockdevice size
            return self.device.size

    @property
    def resize_granularity(self):
        return LUKS_SECTOR_SIZE

    def _resize(self, byte_size, minimum, maximum, interactive):
        if byte_size:
            byte_size -= self.overhead
        self.inner._resize(byte_size, minimum, maximum, interactive)

    @property
    def accepted_params(self):
        return ['key_file']

class Decrypted(blockdevice.InnerLayer, blockdevice.Parametrizable):
    """Represents a decrypted block device.
    Use as a context manager.
    """
    def __init__(self, outer_layer, **kwargs):
        blockdevice.InnerLayer.__init__(self, outer_layer)
        blockdevice.Parametrizable.__init__(self, **kwargs)

    def _open(self, **kwargs):
        params = dict(self._params)
        params.update(kwargs)
        key_file = params.get('key_file', None)
        path = open_encrypted(self.outer.device.path, key_file=key_file)
        return path

    def _close(self):
        close_encrypted(self.path)

    def _resize(self, byte_size, minimum, maximum, interactive):
        if minimum:
            raise Exception("The minimum size of a LUKS device would be 0")
        resize(self.path, byte_size, maximum)

    @property
    def resize_granularity(self):
        return LUKS_SECTOR_SIZE

    @property
    def accepted_params(self):
        return ['key_file']

    def _on_open(self, path, true_open):
        blockdevice.InnerLayer._on_open(self, path, true_open)
        inner_size = self.size
        outer_size = self.outer.device.size
        header_size = luks_data_offset(self.outer.device.path)
        assert (outer_size - inner_size) == header_size

def create_encrypted(device, key_file=None, interactive=True):
    log.info("formatting new encrypted disk on {}".format(device))
    command = [CRYPTSETUP, 'luksFormat']
    if key_file:
        command.extend(['--key-file', key_file])
    if not interactive:
        command.extend(['--batch-mode', '--verify-passphrase'])
    command.append(device)
    shell.get().check_call(command)

def open_encrypted(device, key_file=None):
    '''decrypt and return path to decrypted disk device'''
    log.info("opening encrypted disk {}".format(device))
    name = luks_name(device)
    u_path = luks_path(name)
    command = [CRYPTSETUP, 'luksOpen']
    if key_file:
        command.extend(['--key-file', key_file])
    command.extend([device, name])
    shell.get().check_call(command)
    assert os.path.exists(u_path)
    return u_path

def close_encrypted(path):
    log.info("closing encrypted disk {}".format(path))
    command = (CRYPTSETUP, 'luksClose', path)
    shell.get().check_call(command)

def resize(path, size_bytes=None, max=False):
    assert bool(size_bytes) or max
    command = [CRYPTSETUP, 'resize']
    if size_bytes:
        assert size_bytes % LUKS_SECTOR_SIZE == 0
        size = size_bytes / LUKS_SECTOR_SIZE
        command += ["--size", str(size)]
    command.append(path)
    shell.get().check_call(command)

def luks_name(bd_path):
    '''given a path to a blockdevice, returns the LUKS name used to identify it.
    This will be likely site-specific, and this function should be overriden'''
    return os.path.split(bd_path)[-1]

def luks_path(name):
    '''Given a LUKS device name, returns its decrypted path.
    Usually /dev/mapper/NAME'''
    return '/dev/mapper/' + name

def luks_data_offset(bd_path):
    '''Given a path to a LUKS encrypted blockdevice, detects the offset of the
    encrypted data (in bytes) - that is, where the LUKS header "ends".
    Info extracted from the LUKS On-Disk Format Specification Version 1.2.2'''
    data = misc.read_file(bd_path, 108)
    if data[0:6] != 'LUKS\xba\xbe':
        raise Exception("Not a LUKS device (no LUKS magic detected)")
    luks_version = struct.unpack('>H', data[6:8])[0]
    assert luks_version == 1
    offset_sectors = struct.unpack('>I', data[104:108])[0]
    offset = offset_sectors * LUKS_SECTOR_SIZE
    assert 592 <= offset <= 4*2**20
    return offset

blockdevice.register_data_class("LUKS", Encrypted)
