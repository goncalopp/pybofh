"""Xen utilities"""

XL = '/usr/sbin/xl'

import logging
import os
import shlex

import pybofh
from pybofh import shell

log = logging.getLogger(__name__)

DEFAULT_CFG_DIRS = ["/etc/xen/"]
CFG_EXT = ".cfg"

settings = pybofh.settings.for_("xen")
settings.define("domu_config_dirs", "Directories that contain xen DomU configs")

class DomuDisk(object):
    """A disk of a DomU"""
    def __init__(self, protocol, device, domu_device, access):
        self.protocol = protocol
        self.device = device
        self.domu_device = domu_device
        self.access = access

    def __repr__(self):
        return "Domu Disk<{}:{},{},{}>".format(self.protocol, self.device, self.domu_device, self.access)

class DomuConfig(object):
    """A config file of a DomU"""
    def __init__(self, path_or_file):
        if isinstance(path_or_file, (str, unicode)):
            self.filename = path_or_file
            self._f = open(path_or_file)
        else:
            self.filename = None
            self._f = path_or_file

    @property
    def text(self):
        """Returns a string with the contents of the config file"""
        self._f.seek(0)
        text = self._f.read()
        # remove comments
        lines = text.splitlines()
        lines = [l for l in lines if l.strip() and l.strip()[0] != "#"]
        text = "\n".join(lines)
        return text

    def _get_key(self, k):
        """Given a DomU config file variable, returns its value"""
        s = shlex.split(self.text)
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
        """Returns the list of DomuDisk of this DomU"""
        def disk_string_to_disk(s):
            proto_device, domu_device, access = s.split(",")[:3]
            proto, device = proto_device.split(":")
            return DomuDisk(proto, device, domu_device, access)
        disks_strings = self._get_key("disk")
        disks = map(disk_string_to_disk, disks_strings)
        return disks

class NoDomuConfig(Exception):
    """Raised when a Domu config file is not found"""
    def __init__(self, domu_name):
        Exception.__init__(self, "No config found for Domu: {}".format(domu_name))

class Domu(object):
    """A Xen DomU"""
    def __init__(self, name, config=None):
        if config and not isinstance(config, DomuConfig):
            raise ValueError("config must be a DomuConfig instance, not {}".format(config))
        self.name = name
        self._config = config
        self.sanity_check()

    @property
    def config(self):
        if self._config:
            return self._config
        return get_domu_config(self.name)

    def sanity_check(self):
        try:
            n1, n2 = self.name, self.config.name
            if n1 != n2:
                raise Exception("Domu configured name mismatch: {},{}".format(n1, n2))
        except NoDomuConfig:
            pass

    def start(self):
        log.info("Starting domu {domu}".format(domu=self))
        command = (XL, "create", self.config.name)
        shell.get().check_call(command)

    @property
    def is_running(self):
        return self.name in running_domus_names()

    def __repr__(self):
        return "Domu<{}>".format(self.name)

def running_domus_names():
    command = (XL, "list")
    out = shell.get().check_output(command)
    running = [line.split()[0] for line in out.split('\n')[1:-1]]
    running.remove('Domain-0') #Domain-0 is not a DomU!
    return running

def running_domus():
    return map(Domu, running_domus_names())

def _all_domus_configs_filepaths():
    cfg_dirs = settings.get("domu_config_dirs", DEFAULT_CFG_DIRS)
    assert isinstance(cfg_dirs, list)
    all_files = [os.path.join(d, f) for d in cfg_dirs for f in os.listdir(d)]
    cfg_files = [f for f in all_files if f.endswith(CFG_EXT)]
    return cfg_files

def all_domus_configs_files():
    """Returns a list with opened files of all domu configs found in the domu_config_dirs"""
    return [open(f) for f in _all_domus_configs_filepaths()]

def all_domus_configs():
    files = all_domus_configs_files()
    return map(DomuConfig, files)

def get_domu_config(domu_name):
    configs = all_domus_configs()
    # TODO: make this more efficient using heuristics on file.name, if present
    for c in configs:
        if c.name == domu_name:
            return c
    raise NoDomuConfig(domu_name)
