"""Tests for xen.py"""

import unittest
import mock
from pybofh.tests import common
from pybofh import btrfs

class FakeEnvironment(common.FakeEnvironment):
    def __init__(self):
        common.FakeEnvironment.__init__(self)
        self.shell.add_fake_binary("/sbin/btrfs", self.btrfs_command)

    def btrfs_command(self, command):
        assert command[0] == "/sbin/btrfs"
        if command[1] in ("sub", "subvolume"):
            if command[2] == "list":
                return self.btrfs_subvolume_list(command[3])
        return ""

    def btrfs_subvolume_list(self, path):
        return """ID 270 gen 165066 top level 5 path a_subvolume
        ID 271 gen 163299 top level 5 path a_snapshot"""


def generic_setup(testcase):
    env = FakeEnvironment()
    testcase.env = env
    mocklist = [
        {"target": "pybofh.shell.get", "side_effect": lambda: env.shell},
    ]
    patches = [mock.patch(autospec=True, **a) for a in mocklist]
    for patch in patches:
        patch.start()   

class ModuleTest(unittest.TestCase):
    def setUp(self):
        generic_setup(self)

    def tearDown(self):
        mock.patch.stopall()

    def test_snapshot(self):
        btrfs.snapshot('/1', '/2')
        self.assertEqual(self.env.shell.run_commands[-1], ("/sbin/btrfs", "sub", "snap", "/1", "/2"))

    def test_create_subvolume(self):
        btrfs.create_subvolume('/1')
        self.assertEqual(self.env.shell.run_commands[-1], ("/sbin/btrfs", "sub", "create", "/1"))

    def test_get_subvolumes(self):
        subs = btrfs.get_subvolumes("/1")
        self.assertEqual(self.env.shell.run_commands[-1], ("/sbin/btrfs", "sub", "list", "/1"))
        self.assertEqual(len(subs), 2)
        self.assertEqual(subs[0]["path"], "a_subvolume")
        self.assertEqual(subs[0]["id"], 270)
        self.assertEqual(subs[1]["path"], "a_snapshot")
        self.assertEqual(subs[1]["id"], 271)

    def test_get_subvolume_id(self):
        with self.assertRaises(Exception):
            btrfs.get_subvolume_id("/1", "inexistent_subvol")
        sub = btrfs.get_subvolume_id("/1", "a_subvolume")
        self.assertEqual(sub, 270)

    def test_set_default_subvolume(self):
        btrfs.set_default_subvolume("/1", 270)
        self.assertEqual(self.env.shell.run_commands[-1], ("/sbin/btrfs", "sub", "set", "270", "/1"))





