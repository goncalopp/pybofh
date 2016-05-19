import subprocess
from cli import python_cli
from site_specific import decrypted_path
import blockdevice
import os, os.path

LUKS_SECTOR_SIZE= 512 #this seems hardcoded into luks, so hopefully it's safe to keep it there

class Encrypted(blockdevice.OuterLayer):
    def get_inner(self, *args, **kwargs):
        return Decrypted(self, *args, **kwargs)

    @property
    def size(self):
        raise NotImplementedError

    def resize_granularity(self):
        raise NotImplementedError

    def _resize(self, byte_size, minimum, maximum, interactive):
        raise NotImplementedError

class Decrypted(blockdevice.InnerLayer):
    '''A class that represents a decrypted block device.
    Use as a context manager'''
    def __init__(self, outer_layer, key_file=None):
        super(Decrypted,self).__init__(outer_layer)
        self.key_file= key_file

    def _open(self):
        path= open_encrypted( self.outer.blockdevice.path, key_file=self.key_file )
        return path
    
    def _close( self  ):
        close_encrypted( self.path )
    
def create_encrypted( device, key_file=None, interactive=True ):
    print "formatting new encrypted disk on {device}".format(**locals())
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
    print "opening encrypted disk {device}".format(**locals())
    name= luks_name( device )
    command= ['/sbin/cryptsetup', 'luksOpen']
    if key_file:
        command.extend(['--key-file', key_file])
    command.extend([device, name])
    subprocess.check_call(command)
    u_path= luks_path( name )
    assert os.path.exists(u_path)
    return u_path

def close_encrypted( path ):
    print "closing encrypted disk {path}".format(**locals())
    command= '/sbin/cryptsetup luksClose {0}'.format( path )
    subprocess.check_call( command, shell=True )

def resize( path, size_bytes=None, max=False ):
    assert size_bytes or max
    assert size_bytes % LUKS_SECTOR_SIZE == 0
    size= size_bytes / 512 if size_bytes else None
    command= '/sbin/cryptsetup resize {0} {1}'.format( size if size else "", path)
    subprocess.check_call( command )

def luks_name( blockdevice ):
    '''given a path to a blockdevice, returns the LUKS name used to identify it.
    This will be likely site-specific, and this function should be overriden'''
    return os.path.split(blockdevice)[-1]

def luks_path( luks_name ):
    '''Given a LUKS device name, returns its decrypted path.
    Usually /dev/mapper/NAME'''
    return '/dev/mapper/'+luks_name

blockdevice.register_data_class( "LUKS", Encrypted )

if __name__=="__main__":
    python_cli([create_encrypted, open_encrypted, close_encrypted])
