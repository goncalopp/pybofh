#!/usr/bin/python

XL='/usr/sbin/xl'

import os,subprocess
from functools import partial
import logging
import re
import shlex

import pybofh
from pybofh.mount import mount, unmount
from pybofh import shell
from site_specific import getDomuConfigFile, getDomuDiskMountpoint, getAllDomuNames

log = logging.getLogger(__name__)

settings = pybofh.settings.for_("xen")
settings.define("domu_config_dirs", ["/etc/xen/"])

class DomuDisk(object):
    def __init__(self, protocol, device, domu_device, access):
        self.protocol = protocol
        self.device = device
        self.domu_device = domu_device
        self.access = access

    def __repr__(self):
        return "Domu Disk<{}:{},{},{}>".format(self.protocol, self.device, self.domu_device, self.access)

class DomuConfig(object):
    def __init__(self, path_or_file):
        if isinstance (path_or_file, (str, unicode)):
            path_or_file = open(path_or_file)
        self._f = path_or_file

    @property
    def text(self):
        self._f.seek(0)
        text = self._f.read()
        # remove comments
        lines = text.splitlines()
        lines = [l for l in lines if l.strip() and l.strip()[0] != "#"]
        text = "\n".join(lines)
        return text


    def _get_key(self, k):
        """Given a DomU config file variable, returns its value"""
        s = shlex.split( self.text )
        i = s.index(k)
        assert s[i+1] == "="
        i += 2
        if s[i] == "[":
            i2 = s.index("]", i)
            return list(s[i+1:i2])
        else:
            return s[i]

    @property
    def kernel(self):
        return self._get_key("kernel")

    @property
    def ramdisk(self):
        return self._get_key("ramdisk")

    @property
    def vcpus(self):
        return int(self._get_key("vcpus"))

    @property
    def memory(self):
        return int(self._get_key("memory"))

    @property
    def name(self):
        return self._get_key("name")

    def __repr__(self):
        return "DomuConfig<{}>".format(self.filename)
 
    @property
    def disks(self):
        def disk_string_to_disk(s):
            proto_device, domu_device, access= s.split(",")[:3]
            proto, device= proto_device.split(":")
            return DomuDisk( proto, device, domu_device, access ) 
        disks_strings= self._get_key("disk")
        disks= map( disk_string_to_disk, disks_strings )
        return disks

class Domu(object):
    class NoDomuConfig(Exception):
        pass
    
    def __init__(self, name, configfile_path_override=None):
        self.name=name
        self.configfile= configfile_path_override or getDomuConfigFile(name)
        if self.configfile:
            try:
                self._config = DomuConfig(self.configfile)
            except Exception as e:
                log.info("Failed to get DomuConfig for {}: {}".format(name, e))
                self._config= None
        self.sanity_check()
    
    @property
    def config(self):
        if not self._config:
            raise Domu.NoDomuConfig(self.name)
        return self._config
    
    def sanity_check(self):
        try:
            n1, n2= self.name, self.config.getName()
            if n1 != n2:
                raise Exception("Domu configured name mismatch: {},{}".format(n1, n2))
        except Domu.NoDomuConfig:
            pass

    def start(self):
        log.info("Starting domu {domu}".format(domu=self))
        cf= self.config.filename
        command= (XL, "create", cf)
        subprocess.check_call(command)

    @property
    def isRunning(self):
        return self.name in running_domus_names()

    def __repr__(self):
        return "Domu<{}>".format(self.name)

def allDomus():
    return map(Domu, getAllDomuNames())

def running_domus_names():
    command = (XL, "list")
    out= shell.get().check_output(command)
    running = [line.split()[0] for line in out.split('\n')[1:-1]]
    running.remove('Domain-0') #Domain-0 is not a DomU!
    return running

def running_domus(return_objects=True):
    return map(Domu, running_domus_names())
