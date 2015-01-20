import os
import subprocess

def getLVs(vg):
    dir="/dev/"+vg
    disks= os.listdir(dir)
    return [os.path.join(dir, x) for x in disks]

def createLV(vg, name, size="1GB"):
    print "creating LV {name} with size={size}".format(**locals())
    command="/sbin/lvcreate {vg} --name {name} --size {size}".format(**locals())
    subprocess.check_call(command, shell=True)

def removeLV(vg, name, force=True):
    print "deleting LV {name}".format(**locals())
    force_flag= "-f" if force else ""
    command="/sbin/lvremove {force_flag} {vg}/{name}".format(**locals())
    subprocess.check_call(command, shell=True)
