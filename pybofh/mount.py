#!/usr/bin/python
import os
import pybofh.shell as shell

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
    def __init__(self, mounts):
        '''Example: NestedMounted( [('/dev/sdb2','/'),('/dev/sdb1', '/boot')], '/media/mount')
        will mount /dev/sdb2 in /media/mount and then /dev/sdb1 in /media/mount/boot'''
        mounts = sorted(mounts, key= lambda m: len(m[1])) #make sure we mount directories before subdirectories
        self.mounts= [Mounted(*t) for t in mounts]
        self.mountpoint = self.mounts[0].mountpoint

    def _mount(self):
        mounted=[]
        try:
            for m in self.mounts:
                m.__enter__()
                mounted.append(m)
        except:
            for m in reversed(mounted):
                m.__exit__(None, None, None)


    def _unmount(self):
        for m in reversed(self.mounts):
            m.__exit__(None, None, None)

class MountPool(object):
    '''A Pool of mountpoints'''
    def __init__(self, mountpoints):
        self.free_mountpoints= list(reversed(mountpoints))
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

def mount(device, mountpoint, options=()):
    print "mounting {device} on {mountpoint}".format(**locals())
    options = ("-o",) + options if options else ()
    command= ("/bin/mount",) + options + (device, mountpoint)
    p = shell.get().check_call(command)

def unmount(device):
    print "unmounting {device}".format(**locals())
    command= ('/bin/umount', device)
    p = shell.get().check_call(command)

def is_mountpoint( path ):
    assert os.path.isdir(path)
    return os.path.ismount(path)

def create_filesystem(path, fs="btrfs", options=()):
    print "creating {fs} filesystem on {path}".format(**locals())
    if fs=="btrfs":
        options.append("-f")
    options= " ".join(options) 
    command=("/sbin/mkfs.{}".format(fs)) + options +(path,)
    shell.get().check_call(command)
