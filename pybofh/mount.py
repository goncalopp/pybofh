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
        
    def _mount(self):
        if is_mountpoint(self.mountpoint):
            raise Exception("Mountpoint already mounted: "+self.mountpoint)
        mount(self.file, self.mountpoint, self.options)
    def _unmount(self):
        unmount( self.mountpoint )
    
    def __enter__(self):
        self._mount()
        self.mounted= True
        return self.mountpoint

    def __exit__( self, e_type, e_value, e_trc ):
        if self.mounted:
            self._unmount()
            self.mounted=False
            try:
                self.exit_callback(self)
            except AttributeError:
                pass #not set

class NestedMounted(Mounted):
    '''A mounted mountpoint with other mountpoints inside. 
    Useful for mounting root filesystems with separate partitions for /boot, etc'''
    def __init__(self, mounts, mountpoint):
        '''Example: NestedMounted( [('/dev/sdb2','/'),('/dev/sdb1', '/boot')], '/media/mount')
        will mount /dev/sdb2 in /media/mount and then /dev/sdb1 in /media/mount/boot'''
        mounts.sort( key= lambda m: len(m[1])) #make sure we mount directories before subdirectories
        self.mounts= [Mounted(*t) for t in mounts]

    def _mount(self):
        mounted=[]
        try:
            for m in self.mounts:
                sub.__enter__()
                mounted.append(m)
        finally:
            for m in mounted:
                m.__exit__()

    def _unmount(self):
        for m in reversed(self.submounts):
            m.__exit__()

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
        '''returns a Mounted, to be used in a "with" statement.
        if file is a Mounted, fill its mountpoint and return it'''
        try:
            mountpoint= self.free_mountpoints.pop()
        except IndexError:
            raise Exception("No free mountpoints in pool")
        m= file if isinstance(file, Mounted) else Mounted( file, mountpoint, options )
        self.used_mountpoints.append(m.mountpoint)
        assert not hasattr(m, 'exit_callback')
        m.exit_callback= self._return_to_pool
        return m

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
