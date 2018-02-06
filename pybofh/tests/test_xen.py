# -*- coding: utf-8 -*-

'''Tests for xen.py'''

import unittest
import mock
import functools
from pkg_resources import resource_stream
from pybofh.shell import MockShell
from pybofh import xen


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
    pass


if __name__ == "__main__":
    unittest.main()
