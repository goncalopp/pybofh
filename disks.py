#!/usr/bin/python
import os,subprocess
from cli import python_cli

class MountedFile(object):
    '''A class that represents a mounted file.
    Use as a context manager: 
        with MountedFile(filepath, mountpoint) as mountpoint:'''
    
    def __init__(self, file, mountpoint, options=""):
        self.file, self.mountpoint= file, mountpoint
        self.mounted= False
        
    def __enter__(self):
        if is_mountpoint(mountpoint):
            raise Exception("Mountpoint already mounted: "+mountpoint)
        mount(self.file, self.mountpoint, self.options)
        self.mounted= True
        return self.mountpoint

    def __exit__( self, e_type, e_value, e_trc ):
        if self.mounted:
            unmount( self.mountpoint )
            self.mounted=False
            try:
                self.exit_callback()
            except AttributeError:
                pass #not set


class UnencryptedFile(object):
    '''A class that represents a unencrypted file.
    Use as a context manager'''
    
    def __init__(self, file, allow_nullop=True):
        '''if allow_nullop is True, don't error out if the file is not encrypted, 
        and return the file itself on entering the context manager'''
        self.file= file
        self.allow_nullop= allow_nullop
        self.decrypted= False

    def __enter__(self):
        ie= isEncrypted(self.file)
        if not allow_nullop and not ie:
            raise Exception("File is not encrypted")
        if ie:
            self.decrypted_file= open_encrypted_disk( self.file )
            self.decrypted=True
        else:
            self.decrypted_file= self.file
        return self.decrypted_file     
            
    def __exit__( self, e_type, e_value, e_trc ):
        if self.decrypted:
            close_encrypted_disk( self.decrypted_file )
            self.decrypted= False

        
class MountPool(object):
    '''A Pool of mountpoints'''
    def __init__(self, mountpoints):
        self.free_mountpoints= mountpoints[:]
        self.used_mountpoints= []

    def _return_to_pool(self, mounted_file):
        m= mounted_file.mountpoint
        self.used_mountpoints.remove(m)
        self.free_mountpoints.append(m)

    def mount( self, file, options=""):
        '''returns a MountedFile, to be used in a "with" statement'''
        try:
            m= MountedFile( file, self.free_mountpoints.pop(), options )
            self.used_mountpoints.append(m)
            m.exit_callback= self._return_to_pool
        except IndexError:
            raise Exception("No free mountpoints in pool")

def isEncrypted(x):
    out= subprocess.check_output( "file --special --dereference "+x, shell=True)
    return "LUKS" in out

def isOpened(x):
    return os.path.exists( unencrypted_path(x) )

def mount(device, mountpoint, options=""):
    options= "-o "+options if options else ""
    command='mount {0} {1} {2}'.format(options, device,mountpoint)
    p=subprocess.check_call(command, shell=True)

def unmount(device):
    command='umount {0}'.format(device)
    p=subprocess.check_call(command, shell=True)

def open_encrypted_disk( path ):
    '''unencrypt if needed. return path to unencrypted disk device'''
    u_path= unencrypted_path( path )
    u_name= os.path.basename(u_path)
    if not os.path.exists(u_path): #already opened
        command='/sbin/cryptsetup luksOpen {0} {1}'.format(path, u_name)
        p=subprocess.Popen(command, shell=True)
        p.wait()
        if p.returncode!=0:
            raise Exception("error decrypting "+path)
    return u_path

def close_encrypted_disk( path ):
    command= '/sbin/cryptsetup luksClose {0}'.format( path )
    subprocess.check_call( command )

def createEncrypted( device_path ):
    assert os.path.exists(device_path) 
    command= "cryptsetup luksFormat "+device_path
    subprocess.check_call( command, shell=True )

def unencrypted_path( encrypted_disk_path ):
    unencrypted_name= os.path.basename(encrypted_disk_path ) 
    return "/dev/mapper/"+unencrypted_name
    
def get_opened_disks( disk_paths ):
    return [open_encrypted_disk(x) if isEncrypted(x) else x for x in disk_paths]

def is_mountpoint( path ):
    assert os.path.isdir(path)
    return os.path.ismount(path)

def create_filesystem(path, fs="btrfs", options=[]):
    if fs=="btrfs":
        options.append("-f")
    options= " ".join(options) 
    command="/sbin/mkfs.{fs} {options} {path}".format(**locals())
    subprocess.check_call(command, shell=True)

if __name__=="__main__":
    python_cli(globals().values())
