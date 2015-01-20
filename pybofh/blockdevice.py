#!/usr/bin/python
import os,subprocess
from cli import python_cli

class Mounted(object):
    '''A class that represents a mounted file.
    Use as a context manager: 
        with Mounted(filepath, mountpoint) as mountpoint:'''
    
    def __init__(self, file, mountpoint, options=""):
        self.file, self.mountpoint, self.options= file, mountpoint, options
        self.mounted= False
        
    def __enter__(self):
        if is_mountpoint(self.mountpoint):
            raise Exception("Mountpoint already mounted: "+self.mountpoint)
        mount(self.file, self.mountpoint, self.options)
        self.mounted= True
        return self.mountpoint

    def __exit__( self, e_type, e_value, e_trc ):
        if self.mounted:
            unmount( self.mountpoint )
            self.mounted=False
            try:
                self.exit_callback(self)
            except AttributeError:
                pass #not set


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
        '''returns a Mounted, to be used in a "with" statement'''
        try:
            m= Mounted( file, self.free_mountpoints.pop(), options )
            self.used_mountpoints.append(m.mountpoint)
            m.exit_callback= self._return_to_pool
            return m
        except IndexError:
            raise Exception("No free mountpoints in pool")

def isOpened(x):
    return os.path.exists( unencrypted_path(x) )

def mount(device, mountpoint, options=""):
    print "mounting {device} on {mountpoint}".format(**locals())
    options= "-o "+options if options else ""
    command='mount {0} {1} {2}'.format(options, device,mountpoint)
    p=subprocess.check_call(command, shell=True)

def unmount(device):
    print "unmounting {device}".format(**locals())
    command='umount {0}'.format(device)
    p=subprocess.check_call(command, shell=True)

def is_mountpoint( path ):
    assert os.path.isdir(path)
    return os.path.ismount(path)

def create_filesystem(path, fs="btrfs", options=[]):
    print "creating {fs} filesystem on {path}".format(**locals())
    if fs=="btrfs":
        options.append("-f")
    options= " ".join(options) 
    command="/sbin/mkfs.{fs} {options} {path}".format(**locals())
    subprocess.check_call(command, shell=True)

if __name__=="__main__":
    python_cli(globals().values())
