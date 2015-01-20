import subprocess
from cli import python_cli
from site_specific import unencrypted_path

class Unencrypted(object):
    '''A class that represents a unencrypted block device.
    Use as a context manager'''
    
    def __init__(self, device, allow_noop=True):
        '''if allow_noop is True, don't error out if the device is not encrypted, 
        and return the device itself on entering the context manager'''
        self.device= device
        self.allow_noop= allow_noop
        self.decrypted= False

    def __enter__(self):
        self.decrypted_device= open_encrypted( self.device, allow_noop=self.allow_noop )
        return self.decrypted_device
    
    def __exit__( self, e_type, e_value, e_trc ):
        decrypted= self.decrypted_device != self.device
        if decrypted:
            close_encrypted( self.decrypted_device )

def create_encrypted( device ):
    print "formatting new encrypted disk on {device}".format(**locals())
    assert os.path.exists(device) 
    command= "cryptsetup luksFormat "+device
    subprocess.check_call( command, shell=True )

def is_encrypted( device ):
    out= subprocess.check_output( "file --special --dereference "+device, shell=True)
    return "LUKS" in out

def open_encrypted( device, allow_noop=False ):
    '''unencrypt if needed. return path to unencrypted disk device'''
    if not is_encrypted(device):
        if allow_noop:
            return device
        else:
            raise Exception("device is not encrypted: {}".format(device))
    print "opening encrypted disk {device}".format(**locals())
    u_path= unencrypted_path( device )
    assert u_path != device #otherwise we can't tell nullop from op
    u_name= os.path.basename(u_path)
    if not os.path.exists(u_path): #already opened
        command='/sbin/cryptsetup luksOpen {0} {1}'.format(device, u_name)
        p=subprocess.Popen(command, shell=True)
        p.wait()
        if p.returncode!=0:
            raise Exception("error decrypting "+device)
    return u_path

def close_encrypted( path ):
    print "closing encrypted disk {path}".format(**locals())
    command= '/sbin/cryptsetup luksClose {0}'.format( path )
    subprocess.check_call( command )

if __name__=="__main__":
    python_cli([create_encrypted, is_encrypted, open_encrypted, close_encrypted])
