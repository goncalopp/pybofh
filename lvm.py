import os
import subprocess

def getLVs(vg):
    dir="/dev/"+vg
    disks= os.listdir(dir)
    return [os.path.join(dir, x) for x in disks]

def createLV(vg, name, size="1GB"):
    command="/sbin/lvcreate {vg} --name {name} --size {size}".format(**locals())
    subprocess.check_call(command, shell=True)

