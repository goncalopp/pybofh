#!/usr/bin/python
import os,subprocess
from cli import python_cli

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
