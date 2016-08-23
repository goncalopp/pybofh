import struct
import subprocess
import os, os.path
import time
from cli import python_cli
from pybofh.site_specific import decrypted_path
from pybofh.my_logging import get_logger
from pybofh import blockdevice

LUKS_SECTOR_SIZE= 512 #this seems hardcoded into luks, so hopefully it's safe to keep it there

log = get_logger(__name__)

class Encrypted(blockdevice.OuterLayer, blockdevice.Parametrizable):
    def __init__(self, bd, **kwargs):
        blockdevice.OuterLayer.__init__(self, bd)
        blockdevice.Parametrizable.__init__(self, **kwargs)

    @property
    def _inner_layer_class(self):
        return Decrypted

    @property
    def size(self):
        try:
            header_size= luks_data_offset(self.blockdevice.path)
            return header_size + self.inner.size
        except blockdevice.NotReady:
            #there's no way to know, just return the enclosing blockdevice size
            return self.blockdevice.size

    @property
    def resize_granularity(self):
        return LUKS_SECTOR_SIZE

    def _resize(self, byte_size, minimum, maximum, interactive):
        if byte_size:
            byte_size-= self.overhead
        self.inner._resize(byte_size, minimum, maximum, interactive)

    @property
    def accepted_params(self):
        return ['key_file']

class Decrypted(blockdevice.InnerLayer, blockdevice.Parametrizable):
    '''A class that represents a decrypted block device.
    Use as a context manager'''
    def __init__(self, outer_layer, **kwargs):
        blockdevice.InnerLayer.__init__(self, outer_layer)
        blockdevice.Parametrizable.__init__(self, **kwargs)

    def _open(self, **kwargs):
        params= dict(self._params)
        params.update(kwargs)
        key_file= params.get('key_file', None)
        path= open_encrypted( self.outer.blockdevice.path, key_file=key_file )
        return path
    
    def _close(self):
        close_encrypted( self.path )

    def _resize(self, byte_size, minimum, maximum, interactive):
        if minimum:
            raise Exception("The minimum size of a LUKS device would be 0")
        resize(self.path, byte_size, maximum )

    @property
    def resize_granularity(self):
        return LUKS_SECTOR_SIZE

    @property
    def accepted_params(self):
        return ['key_file']

    def _on_open(self, path, true_open):
        blockdevice.InnerLayer._on_open(self, path, true_open)
        inner_size= self.size
        outer_size= self.outer.blockdevice.size
        header_size= luks_data_offset(self.outer.blockdevice.path)
        assert (outer_size - inner_size) == header_size

def create_encrypted( device, key_file=None, interactive=True ):
    log.info("formatting new encrypted disk on {}".format(device))
    assert os.path.exists(device) 
    command= ['/sbin/cryptsetup', 'luksFormat']
    if key_file:
        command.extend(['--key-file', key_file])
    if not interactive:
        command.extend(['--batch-mode', '--verify-passphrase'])
    command.append(device)
    subprocess.check_call( command )

def open_encrypted( device, key_file=None ):
    '''decrypt and return path to decrypted disk device'''
    log.info("opening encrypted disk {}".format(device))
    name= luks_name( device )
    u_path= luks_path( name )
    if os.path.exists(u_path):
        raise Exception("target device path already exists")
    command= ['/sbin/cryptsetup', 'luksOpen']
    if key_file:
        command.extend(['--key-file', key_file])
    command.extend([device, name])
    subprocess.check_call(command)
    assert os.path.exists(u_path)
    return u_path

def close_encrypted( path ):
    log.info("closing encrypted disk {}".format(path))
    command= '/sbin/cryptsetup luksClose {0}'.format( path )
    subprocess.check_call( command, shell=True )

def resize( path, size_bytes=None, max=False ):
    assert bool(size_bytes) or max
    command= ['/sbin/cryptsetup', 'resize']
    if size_bytes:
        assert size_bytes % LUKS_SECTOR_SIZE == 0
        size= size_bytes / LUKS_SECTOR_SIZE
        command+= ["--size", str(size)]
    command.append(path)
    subprocess.check_call( command )

def luks_name( blockdevice ):
    '''given a path to a blockdevice, returns the LUKS name used to identify it.
    This will be likely site-specific, and this function should be overriden'''
    return os.path.split(blockdevice)[-1]

def luks_path( luks_name ):
    '''Given a LUKS device name, returns its decrypted path.
    Usually /dev/mapper/NAME'''
    return '/dev/mapper/'+luks_name

def luks_data_offset( blockdevice ):
    '''Given a path to a LUKS encrypted blockdevice, detects the offset of the
    encrypted data (in bytes) - that is, where the LUKS header "ends".
    Info extracted from the LUKS On-Disk Format Specification Version 1.2.2'''
    data= open(blockdevice).read(108)
    if data[0:6] != 'LUKS\xba\xbe':
        raise Exception("Not a LUKS device (no LUKS magic detected)")
    luks_version= struct.unpack('>H', data[6:8])[0]
    assert luks_version == 1
    offset_sectors= struct.unpack('>I', data[104:108])[0]
    offset= offset_sectors * LUKS_SECTOR_SIZE
    assert 592 <= offset <= 4*2**20
    return offset

blockdevice.register_data_class( "LUKS", Encrypted )

if __name__=="__main__":
    python_cli([create_encrypted, open_encrypted, close_encrypted])
