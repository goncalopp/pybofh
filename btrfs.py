import subprocess
import os

def snapshot(fro, to):
    command= "/sbin/btrfs sub snap {0} {1}".format(fro, to)
    subprocess.check_call(command, shell=True)

def create_subvolume(path):
    command= "/sbin/btrfs sub create {0}".format(path)
    subprocess.check_call(command, shell=True)

def get_subvolumes(path):
    command= "/sbin/btrfs sub list {0}".format(path)
    out= subprocess.check_output(command, shell=True)
    def line_to_subvol(line):
        splitted= line.split()
        assert splitted[0]=="ID"
        assert len(splitted)==9
        id= int(splitted[1])
        path= splitted[-1]
        return {"id":id, "path":path}
    return map( line_to_subvol, out.splitlines() ) 

def get_subvolume_id( fs_path, subvol_path ):
    subs= btrfs_get_subvolumes( fs_path )
    subs= filter( lambda sub: subvol_path in sub['path'], subs )
    assert len(subs)==1
    return subs[0]["id"]

def set_default_subvol( fs_path, subvol_id ):
    command= "/sbin/btrfs sub set {subvol_id} {fs_path}".format(**locals())
    subprocess.check_call(command, shell=True)    

def create_base_structure(rootsubvol_mountpoint, subvolumes=[""], set_default_subvol=True):
    '''Creates default subvolumes, and snapshots directory structure, migrating any existing data'''
    subvol_path= {"":"root", "home":"home"} #path of a subvolume inside the root subvolume
    SNAPSHOT_PATH= "snapshots"			#snapshot directory, inside the root subvolume    
    TMP_SUBVOL_PREFIX="-subvol"
    def snapshot_path( subvolume ):
        return j(SNAPSHOT_PATH, subvol_path[subvolume])
    j= os.path.join
    mountpoint= rootsubvol_mountpoint
    oldlisting= os.listdir(mountpoint)
    
    assert is_mountpoint(mountpoint)
    assert len(subvolumes) and set( subvolumes )<set(subvol_path.keys())

    snapshot(mountpoint, j(mountpoint, subvol_path[""]))
    print "creating snapshots dirs"
    os.mkdir( j(mountpoint, SNAPSHOT_PATH))
    for subvol in subvolumes:
        os.mkdir( j(mountpoint, snapshot_path(subvol) )) 

    if ("" in subvolumes) and set_default_subvol:
        print "setting default subvolume"
        set_default_subvol( mountpoint, get_subvolume_id( mountpoint, subvol_path[""] ) )

#--------------- This section pertains to the btrfs-snapshot script-------------------------------

def get_btrfs_snapshot_path():
    '''gets the path to the btrfs-snapshot script'''
    module_path= os.path.dirname(os.path.abspath(__file__)) #path to this module
    p= os.join( module_path, "btrfs-snapshot")
    assert os.path.exists(p)
    return p 
    

def install_btrfs_snapshot_rotation(mountpoint="/", fs_path="/", snap_path="/media/btrfs/root/snapshots/root", daily=7*3, weekly=4*3, monthly=12*3, yearly=10):
    '''installs btrfs-snapshot-rotation script
        mountpoint: where we have the root filesystem (we want to install on)
        fs_path: path we want to make snapshots of, relative to mountpoint
        snap_path: path we want snapshots stored on, relative to mountpoint
        '''
    SCRIPT_PATH="{mountpoint}/usr/local/bin".format(**locals())
    source_script_path= get_btrfs_snapshot_path()
    assert any(map(os.path.exists, ("/sbin/anacron", "/usr/sbin/anacron"))) #check anacron is installed
    assert not os.path.exists(SCRIPT_PATH)	#check btrfs-snapshot not installed
    assert os.path.isdir( snap_path )
    def check_not_installed(s):
        s= "cat {0} | grep btrfs-snapshot | cat -".format(s)
        if subprocess.check_output( s, shell=True)!="":
            raise Exception("btrfs-snapshot already installed on "+s)
    check_not_installed("/etc/anacrontab")
    map( check_not_installed, ("/etc/anacrontab", "/etc/cron.daily/*", "/etc/cron.weekly/*", "/etc/cron.monthly/*"))
    anacron_string= (
	'''1		12	daily_snap	{SCRIPT_PATH}/btrfs-snapshot {fs_path} {snap_path} daily   {daily}   \n'''
        '''7		16	weekly_snap	{SCRIPT_PATH}/btrfs-snapshot {fs_path} {snap_path} weekly  {weekly}  \n'''
        '''@monthly	21	monthly_snap	{SCRIPT_PATH}/btrfs-snapshot {fs_path} {snap_path} monthly {monthly} \n'''
        '''365		26	yearly_snap	{SCRIPT_PATH}/btrfs-snapshot {fs_path} {snap_path} yearly  {yearly}  \n'''
        ).format(**locals())
    subprocess.check_call("cp btrfs-snapshot "+SCRIPT_PATH, shell=True)
    open(os.path.join(mountpoint, "etc","anacrontab"), "a").write( anacron_string )

#------------------------------------------------------------------------------------------------

if __name__=="__main__":
    python_cli(globals().values())
