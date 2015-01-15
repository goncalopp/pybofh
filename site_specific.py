#his file contains site-specific values or functions with such knowledge

import os

DOMU_LVM_VG="g3"


#------DISKS-------------------------------------------------------------

def unencrypted_path( encrypted_disk_path ):
    unencrypted_name= os.path.basename(encrypted_disk_path )
    return "/dev/mapper/"+unencrypted_name

#-------XEN-----------------------------------------------------------------

def getDomuDisks(domu):
    '''returns the absolute paths to devices (disks) belonging to a DomU'''
    import lvm
    possible_disks= lvm.getLVs( DOMU_LVM_VG ) + getDrbdDevices()
    def is_domu_disk(path, domu_name):
        name= os.path.basename(path)
        lvm_match= name.startswith( domu_name+"_" )
        drbd_match= name.startswith( "drbd_"+domu_name+"_" )
        match= lvm_match or drbd_match
        if match:
            try:
                getDomuDiskMountpoint(domu_disk)
            except:
                print "path {} matched DomU {}, but getMountpoint failed. Ignoring it.".format(path, domu_name)
                return False
        return match
    f= partial(is_domu_disk, domu_name=domu) 
    return list(filter(f, possible_disks))

def getDomuDiskMountpoint(domu_disk):
    '''Given a absolute path to a device (disk) belonging to a DomU,
    returns its mountpoint in the DomU root filestem (/home, /var, ...)'''
    MOUNTPOINT_MAP={"root":"/","home":"/home","swap":""}
    d=os.path.basename(domu_disk)
    suffix= d[d.index("_")+1:]
    return MOUNTPOINT_MAP[suffix]

def getConfigurationFile(domu):
    '''Given the DomU name, returns its configuration file'''
    BASEPATH= "/etc/xen/"
    p= BASEPATH + domu + ".cfg"
    return p

