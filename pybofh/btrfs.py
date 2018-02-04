from pybofh import shell
import os

def snapshot(fro, to):
    #command already prints #print "Creating snapshot of {fro} in {to}".format(**locals())
    assert not os.path.exists(to)
    command= ("/sbin/btrfs", "sub", "snap", fro, to)
    shell.get().check_call(command)

def create_subvolume(path):
    print "Creating subvolume: {path}".format(**locals())
    command= ("/sbin/btrfs", "sub", "create", path)
    shell.get().check_call(command)

def get_subvolumes(path):
    command= ("/sbin/btrfs", "sub", "list", path)
    out= shell.get().check_output(command)
    def line_to_subvol(line):
        splitted= line.split()
        assert splitted[0]=="ID"
        assert len(splitted)==9
        id= int(splitted[1])
        path= splitted[-1]
        return {"id":id, "path":path}
    return map( line_to_subvol, out.splitlines() ) 

def get_subvolume_id( fs_path, subvol_path ):
    subs= get_subvolumes( fs_path )
    subs= filter( lambda sub: subvol_path in sub['path'], subs )
    assert len(subs)==1
    return subs[0]["id"]

def set_default_subvol( fs_path, subvol_id ):
    print "Setting default subvolume of {fs_path} to {subvol_id}".format(**locals())
    command= ("/sbin/btrfs", "sub", "set", subvol_id, fs_path)
    shell.get().check_call(command)

def create_base_structure(rootsubvol_mountpoint, subvolumes=[""], set_default_subv=True):
    '''Creates default subvolumes, and snapshots directory structure, migrating any existing data'''
    SUBVOL_NAME= {"":"root", "home":"home"} #path of a subvolume inside the root subvolume
    SNAPSHOT_PATH= "snapshots"			#snapshot directory, inside the root subvolume    
    SUBVOLUME_PATH="subvolumes"
    
    #aliases, imports 
    j= os.path.join
    mountpoint= rootsubvol_mountpoint
    from pybofh.mount import is_mountpoint
    
    def snapshot_path( subvolume ):
        return j(mountpoint, SNAPSHOT_PATH, SUBVOL_NAME[subvolume])
    def subvol_path( subvolume ):
        return j(mountpoint, SUBVOLUME_PATH, SUBVOL_NAME[subvolume]) 
    
    print "creating btrfs base structure on {rootsubvol_mountpoint}".format(**locals())
    oldlisting= os.listdir(mountpoint)
    
    assert is_mountpoint(mountpoint)
    assert len(subvolumes) and set( subvolumes )<set(SUBVOL_NAME.keys())
    
    print "creating dirs"
    if not os.path.isdir(j(mountpoint, SNAPSHOT_PATH)):
        os.mkdir(j(mountpoint, SNAPSHOT_PATH))
    if not os.path.isdir(j(mountpoint, SUBVOLUME_PATH)):
        os.mkdir(j(mountpoint, SUBVOLUME_PATH))

    for subvol in subvolumes:
        snapshot( j(mountpoint, subvol), subvol_path(subvol) )
        os.mkdir( snapshot_path(subvol) ) 

    if ("" in subvolumes) and set_default_subv:
        set_default_subvol( mountpoint, get_subvolume_id( mountpoint, SUBVOL_NAME[""] ) )

#--------------- This section pertains to the btrfs-snapshot script-------------------------------

def get_btrfs_snapshot_path():
    '''gets the path to the btrfs-snapshot script'''
    module_path= os.path.dirname(os.path.abspath(__file__)) #path to this module
    p= os.path.join( module_path, "btrfs-snapshot")
    assert os.path.exists(p)
    return p 
    

def install_btrfs_snapshot_rotation(mountpoint="/", fs_path="/", snap_path="/media/btrfs/root/snapshots/root", daily=7*3, weekly=4*3, monthly=12*3, yearly=10):
    '''installs btrfs-snapshot-rotation script
        mountpoint: where we have the root filesystem (we want to install on)
        fs_path: path we want to make snapshots of, relative to mountpoint
        snap_path: path we want snapshots stored on, relative to mountpoint
        '''
    SCRIPT_PATH="{mountpoint}/usr/local/bin".format(**locals())
    print "installing btrfs-snapshot on {mountpoint}".format(**locals())
    source_script_path= get_btrfs_snapshot_path()
    assert any(map(os.path.exists, ("/sbin/anacron", "/usr/sbin/anacron"))) #check anacron is installed
    assert not os.path.exists(SCRIPT_PATH+"/btrfs-snapshot")	#check btrfs-snapshot not installed
    assert os.path.isdir( snap_path )
    def check_not_installed(s):
        if "btrfs-snapshot" in open(s).read():
            raise Exception("btrfs-snapshot already installed on "+s)
    check_not_installed("/etc/anacrontab")
    map( check_not_installed, ("/etc/anacrontab", "/etc/cron.daily/*", "/etc/cron.weekly/*", "/etc/cron.monthly/*"))
    anacron_string= (
	'''1		12	daily_snap	{SCRIPT_PATH}/btrfs-snapshot {fs_path} {snap_path} daily   {daily}   \n'''
        '''7		16	weekly_snap	{SCRIPT_PATH}/btrfs-snapshot {fs_path} {snap_path} weekly  {weekly}  \n'''
        '''@monthly	21	monthly_snap	{SCRIPT_PATH}/btrfs-snapshot {fs_path} {snap_path} monthly {monthly} \n'''
        '''365		26	yearly_snap	{SCRIPT_PATH}/btrfs-snapshot {fs_path} {snap_path} yearly  {yearly}  \n'''
        ).format(**locals())
    #copy script
    shell.get().check_call(("cp", "btrfs-snapshot", SCRIPT_PATH))
    #append anacrontab lines
    open(os.path.join(mountpoint, "etc","anacrontab"), "a").write( anacron_string )

#------------------------------------------------------------------------------------------------
