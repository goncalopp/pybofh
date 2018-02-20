# -*- coding: utf-8 -*-
"""Tests for xen.py"""

import unittest
import mock
from pkg_resources import resource_stream
from pybofh.tests import common
from pybofh import xen
from pybofh import settings

DOMUS_CFGS = ["domu1.cfg"]
XL_LIST_DATA = """Name                                        ID   Mem VCPUs    State   Time(s)
Domain-0                                     0  5301     2     r-----   72726.8
domu1                                        1   256     1     -b----  106502.6
domu2                                        2   256     1     -b----   12900.8
domu3                                        3   128     1     -b----    6917.9
"""

class FakeEnvironment(common.FakeEnvironment):
    """Shell environment - keeps state for side effects from commands"""
    def xl(self, command):
        assert command[0] == xen.XL
        c1 = command[1]
        if c1 == 'list':
            return XL_LIST_DATA
        elif c1 == 'create':
            return ''
        else:
            raise NotImplementedError(str(command))

def generic_setup(testcase):
    env = FakeEnvironment()
    testcase.env = env
    env.shell.add_fake_binary(xen.XL, env.xl)
    mocklist = [
        {"target": "pybofh.shell.get", "side_effect": lambda: env.shell},
    ]
    mock.patch("pybofh.xen.all_domus_configs_files", new=lambda: [resource_stream('pybofh.tests', cfg) for cfg in DOMUS_CFGS]).start()
    patches = [mock.patch(autospec=True, **a) for a in mocklist]
    for patch in patches:
        patch.start()

class DomuConfigTest(unittest.TestCase):
    def setUp(self):
        self.f = resource_stream('pybofh.tests', DOMUS_CFGS[0])

    def tearDown(self):
        mock.patch.stopall()

    def test_init(self):
        c = xen.DomuConfig(self.f)
        self.assertIsInstance(c, xen.DomuConfig)

    def test_disks(self):
        c = xen.DomuConfig(self.f)
        disks = c.disks
        self.assertEqual(len(disks), 2)
        self.assertIsInstance(disks[0], xen.DomuDisk)
        self.assertIsInstance(disks[1], xen.DomuDisk)
        self.assertEqual(disks[1].protocol, 'phy')
        self.assertEqual(disks[1].device, '/dev/mapper/domu1_home')
        self.assertEqual(disks[1].domu_device, 'xvda3')
        self.assertEqual(disks[1].access, 'w')

    def test_kernel(self):
        c = xen.DomuConfig(self.f)
        self.assertEqual(c.kernel, '/boot/vmlinuz-9.11-3-amd64')

    def test_ramdisk(self):
        c = xen.DomuConfig(self.f)
        self.assertEqual(c.ramdisk, '/boot/initrd.img-9.11-3-amd64')

    def test_vcpus(self):
        c = xen.DomuConfig(self.f)
        self.assertEqual(c.vcpus, 1)

    def test_memory(self):
        c = xen.DomuConfig(self.f)
        self.assertEqual(c.memory, 256)

    def test_name(self):
        c = xen.DomuConfig(self.f)
        self.assertEqual(c.name, 'domu1')

class DomuTest(unittest.TestCase):
    def setUp(self):
        generic_setup(self)

    def tearDown(self):
        mock.patch.stopall()

    def test_init(self):
        domu = xen.Domu("random_name")
        self.assertIsInstance(domu, xen.Domu)

    def test_config(self):
        domu = xen.Domu("random_name")
        with self.assertRaises(xen.NoDomuConfig):
            _ = domu.config
        domu = xen.Domu("domu1")
        self.assertIsInstance(domu.config, xen.DomuConfig)

    def test_start(self):
        domu = xen.Domu("domu1")
        domu.start()
        self.assertEqual(self.env.shell.run_commands[-1], (xen.XL, 'create', "domu1"))

class ModuleTest(unittest.TestCase):
    def setUp(self):
        generic_setup(self)

    def tearDown(self):
        mock.patch.stopall()

    def test_running_domus(self):
        l = xen.running_domus()
        self.assertEqual(len(l), 3)
        self.assertEqual([d.name for d in l], ['domu1', 'domu2', 'domu3'])

    def test_running_domus_names(self):
        l = xen.running_domus_names()
        self.assertEqual(l, ['domu1', 'domu2', 'domu3'])

    def test_all_domus_configs_filepaths(self):
        with mock.patch('os.listdir', return_value=['domu.cfg', 'unrelated.txt']):
            with settings.for_('xen').change(domu_config_dirs=[]):
                l = xen._all_domus_configs_filepaths()
                self.assertEqual(l, [])
            with settings.for_('xen').change(domu_config_dirs=['/a', '/b']):
                l = xen._all_domus_configs_filepaths()
                self.assertEqual(l, ['/a/domu.cfg', '/b/domu.cfg'])



if __name__ == "__main__":
    unittest.main()
