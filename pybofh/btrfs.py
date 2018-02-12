"""Btrfs filesystem utilities"""

from pybofh import shell
import logging
import os

log = logging.getLogger(__name__)
BTRFS_BIN = '/sbin/btrfs'

def snapshot(fro, to):
    """Create a new btrfs snapshot from the given subvolume into the given path"""
    logging.info("Creating snapshot of {} in {}".format(fro, to))
    command = (BTRFS_BIN, "sub", "snap", fro, to)
    shell.get().check_call(command)

def create_subvolume(path):
    """Create a new btrfs subvolume in the given path"""
    logging.info("Creating subvolume: {}".format(path))
    command = (BTRFS_BIN, "sub", "create", path)
    shell.get().check_call(command)

def get_subvolumes(path):
    """Returns a list of dicts representing subvolumes.
    Dict keys: id, path.
    """
    command = (BTRFS_BIN, "sub", "list", path)
    out = shell.get().check_output(command)
    def line_to_subvol(line):
        """Converts a single line of "btrfs sub list" into a dict"""
        splitted = line.split()
        assert splitted[0] == "ID"
        assert len(splitted) == 9
        id_ = int(splitted[1])
        path = splitted[-1]
        return {"id":id_, "path":path}
    return map(line_to_subvol, out.splitlines())

def get_subvolume_id(fs_path, subvol_path):
    """Given a mounted btrfs filesystem and a subvolume path, returns the subvolume id"""
    subs = get_subvolumes(fs_path)
    subs = [s for s in subs if s["path"] == subvol_path]
    if len(subs) > 1:
        raise Exception("Found more than one subvolume for path: {}".format(subvol_path))
    if len(subs) == 0:
        raise KeyError("Subvolume not found: {}".format(subvol_path))
    return subs[0]["id"]

def set_default_subvolume(fs_path, subvol_id):
    """Sets the default subvolume of the btrfs filesystem fs_path to subvol_id"""
    logging.info("Setting default subvolume of {} to {}".format(fs_path, subvol_id))
    command = (BTRFS_BIN, "sub", "set", str(subvol_id), fs_path)
    shell.get().check_call(command)

def create_base_structure(rootsubvol_mountpoint, subvolumes=("",), set_default_subvol=True):
    """Creates default subvolumes, and snapshots directory structure, migrating any existing data"""
    SUBVOL_NAME = {"":"rootfs", "home":"home"} #path of a subvolume inside the root subvolume
    SNAPSHOT_PATH = "snapshots"			#snapshot directory, inside the root subvolume
    SUBVOLUME_PATH = "subvolumes"

    #aliases, imports
    j = os.path.join
    mountpoint = rootsubvol_mountpoint
    from pybofh.mount import is_mountpoint

    def snapshot_path(subvolume):
        return j(mountpoint, SNAPSHOT_PATH, SUBVOL_NAME[subvolume])
    def subvol_path(subvolume):
        return j(mountpoint, SUBVOLUME_PATH, SUBVOL_NAME[subvolume])

    logging.info("creating btrfs base structure on {}".format(rootsubvol_mountpoint))

    assert is_mountpoint(mountpoint)
    assert len(subvolumes) and set(subvolumes) < set(SUBVOL_NAME.keys())

    if not os.path.isdir(j(mountpoint, SNAPSHOT_PATH)):
        os.mkdir(j(mountpoint, SNAPSHOT_PATH))
    if not os.path.isdir(j(mountpoint, SUBVOLUME_PATH)):
        os.mkdir(j(mountpoint, SUBVOLUME_PATH))

    for subvol in subvolumes:
        snapshot(j(mountpoint, subvol), subvol_path(subvol))
        os.mkdir(snapshot_path(subvol))

    if ("" in subvolumes) and set_default_subvol:
        set_default_subvol(mountpoint, get_subvolume_id(mountpoint, SUBVOL_NAME[""]))

#--------------- This section pertains to the btrfs-snapshot script-------------------------------

def get_btrfs_snapshot_path():
    """gets the path to the btrfs-snapshot script"""
    module_path = os.path.dirname(os.path.abspath(__file__)) #path to this module
    p = os.path.join(module_path, "btrfs-snapshot")
    assert os.path.exists(p)
    return p

def install_btrfs_snapshot_rotation(mountpoint="/", fs_path="/", snap_path="/media/btrfs/root/snapshots/root", daily=7*3, weekly=4*3, monthly=12*3, yearly=10):
    '''installs btrfs-snapshot-rotation script
        mountpoint: where we have the root filesystem (we want to install on)
        fs_path: path we want to make snapshots of, relative to mountpoint
        snap_path: path we want snapshots stored on, relative to mountpoint
        '''
    raise NotImplementError("This code needs to be reviewed before usage")
    SCRIPT_PATH = "{mountpoint}/usr/local/bin".format(**locals())
    logging.info("installing btrfs-snapshot on {}".format(mountpoint))
    source_script_path = get_btrfs_snapshot_path()
    assert any(map(os.path.exists, ("/sbin/anacron", "/usr/sbin/anacron"))) #check anacron is installed
    assert not os.path.exists(SCRIPT_PATH+"/btrfs-snapshot")	#check btrfs-snapshot not installed
    assert os.path.isdir(snap_path)
    def check_not_installed(s):
        if "btrfs-snapshot" in open(s).read():
            raise Exception("btrfs-snapshot already installed on "+s)
    check_not_installed("/etc/anacrontab")
    map(check_not_installed, ("/etc/anacrontab", "/etc/cron.daily/*", "/etc/cron.weekly/*", "/etc/cron.monthly/*"))
    anacron_string = (
        '''1		12	daily_snap	{SCRIPT_PATH}/btrfs-snapshot {fs_path} {snap_path} daily   {daily}   \n'''
        '''7		16	weekly_snap	{SCRIPT_PATH}/btrfs-snapshot {fs_path} {snap_path} weekly  {weekly}  \n'''
        '''@monthly	21	monthly_snap	{SCRIPT_PATH}/btrfs-snapshot {fs_path} {snap_path} monthly {monthly} \n'''
        '''365		26	yearly_snap	{SCRIPT_PATH}/btrfs-snapshot {fs_path} {snap_path} yearly  {yearly}  \n'''
        ).format(**locals())
    #copy script
    shell.get().check_call(("cp", "btrfs-snapshot", SCRIPT_PATH))
    #append anacrontab lines
    open(os.path.join(mountpoint, "etc", "anacrontab"), "a").write(anacron_string)

#------------------------------------------------------------------------------------------------
