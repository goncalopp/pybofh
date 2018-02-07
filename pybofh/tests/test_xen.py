# -*- coding: utf-8 -*-
"""Tests for xen.py"""

import unittest
import mock
import functools
from pkg_resources import resource_stream
from pybofh.shell import MockShell
from pybofh import xen

XL_LIST_DATA = """Name                                        ID   Mem VCPUs    State   Time(s)
Domain-0                                     0  5301     2     r-----   72726.8
domu1                                        1   256     1     -b----  106502.6
domu2                                        2   256     1     -b----   12900.8
domu3                                        3   128     1     -b----    6917.9
"""

class Environment(object):
    def xl(self, command):
        assert command[0] == xen.XL
        if command[1] == 'list':
            return XL_LIST_DATA
        else:
            raise NotImplementedError(str(command))

def create_mock_shell(env):
    shell = MockShell()
    shell.add_mock_binary(xen.XL, env.xl)
    return shell

class DomuConfigTest(unittest.TestCase):
    def setUp(self):
        self.f = resource_stream('pybofh.tests', 'domu1.cfg')

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
        self.assertEqual(c.memory, 1024)

    def test_name(self):
        c = xen.DomuConfig(self.f)
        self.assertEqual(c.name, 'domu1')

class ModuleTest(unittest.TestCase):
    def setUp(self):
        self.env = Environment()
        self.shell = create_mock_shell(self.env)
        mocklist = [
        {"target": "pybofh.shell.get", "side_effect": lambda: self.shell},
        ]
        patches = [mock.patch(autospec=True, **a) for a in mocklist]
        for patch in patches:
            patch.start()

    def tearDown(self):
        mock.patch.stopall()

    def test_running_domus(self):
        l = xen.running_domus()
        self.assertEqual(len(l), 3)
        self.assertEqual([d.name for d in l], ['domu1', 'domu2', 'domu3'])

    def test_running_domus_names(self):
        l = xen.running_domus_names()
        self.assertEqual(l, ['domu1', 'domu2', 'domu3'])


if __name__ == "__main__":
    unittest.main()
