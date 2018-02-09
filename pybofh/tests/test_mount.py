'''Tests for mount.py'''

import unittest
import mock
from pybofh.mount import Mounted, NestedMounted, MountPool, mount, unmount

from pybofh.shell import FakeShell

DEVS = ('/dev/in1', '/dev/in2', '/dev/in3', '/dev/in4')
MTS = ('/mnt/in1', '/mnt/in2', '/mnt/in3')

def generic_setup(test_instance):
    shell = FakeShell()
    shell.add_fake(lambda command: True, None)
    test_instance.shell = shell
    mocklist = [
        {'target': 'os.path.isdir'},
        {'target': 'pybofh.shell.get', 'side_effect': lambda: shell}
        ]
    patches = [mock.patch(autospec=True, **a) for a in mocklist]
    for patch in patches:
        patch.start()

class MountedTest(unittest.TestCase):
    def setUp(self):
        generic_setup(self)

    def tearDown(self):
        mock.patch.stopall()

    def test_create(self):
        m = Mounted(DEVS[0], MTS[0])
        self.assertIsInstance(m, Mounted)

    def test_mount(self):
        m = Mounted(DEVS[0], MTS[0])
        with m:
            self.assertIn(('/bin/mount', DEVS[0], MTS[0]), self.shell.run_commands)
        self.assertIn(('/bin/umount', MTS[0]), self.shell.run_commands)
        self.assertEqual(len(self.shell.run_commands), 2)

class NestedMountedTest(unittest.TestCase):
    def setUp(self):
        generic_setup(self)

    def tearDown(self):
        mock.patch.stopall()

    def test_create(self):
        m = NestedMounted([(DEVS[0], '/mnt/inexistent'), (DEVS[1], '/mnt/inexistent/boot')])
        self.assertIsInstance(m, NestedMounted)

    def test_mount(self):
        calls = self.shell.run_commands
        m = NestedMounted([(DEVS[0], '/mnt/inexistent'), (DEVS[1], '/mnt/inexistent/boot')])
        with m:
            self.assertEqual(calls[0], ('/bin/mount', DEVS[0], '/mnt/inexistent'))
            self.assertEqual(calls[1], ('/bin/mount', DEVS[1], '/mnt/inexistent/boot'))
        self.assertEqual(calls[2], ('/bin/umount', '/mnt/inexistent/boot'))
        self.assertEqual(calls[3], ('/bin/umount', '/mnt/inexistent'))
        self.assertEqual(len(calls), 4)

class MountPoolTest(unittest.TestCase):
    def setUp(self):
        generic_setup(self)

    def tearDown(self):
        mock.patch.stopall()
 
    def test_mount(self):
        calls = self.shell.run_commands
        m = MountPool(MTS[:3])
        with m.mount(DEVS[0]):
            self.assertEqual(calls[-1], ('/bin/mount', DEVS[0], MTS[0]))
            with m.mount(DEVS[1]):
                self.assertEqual(calls[-1], ('/bin/mount', DEVS[1], MTS[1]))
                with m.mount(DEVS[2]):
                    self.assertEqual(calls[-1], ('/bin/mount', DEVS[2], MTS[2]))
                self.assertEqual(calls[-1], ('/bin/umount', MTS[2]))
            self.assertEqual(calls[-1], ('/bin/umount', MTS[1]))
        self.assertEqual(calls[-1], ('/bin/umount', MTS[0]))

    def test_mount_overflow(self):
        calls = self.shell.run_commands
        m = MountPool(MTS[:1])
        with m.mount(DEVS[0]):
            self.assertEqual(calls[-1], ('/bin/mount', DEVS[0], MTS[0]))
            with self.assertRaises(Exception):
                with m.mount(DEVS[1]):
                    pass
        self.assertEqual(calls[-1], ('/bin/umount', MTS[0]))

class ModuleFunctionsTest(unittest.TestCase):
    def setUp(self):
        generic_setup(self)

    def tearDown(self):
        mock.patch.stopall()

    def test_mount(self):
        mount(DEVS[0], MTS[0])
        self.assertEqual([('/bin/mount', DEVS[0], MTS[0])], self.shell.run_commands)
 
    def test_umount(self):
        unmount(MTS[0])
        self.assertEqual(self.shell.run_commands, [('/bin/umount', MTS[0])])

    def test_is_mountpoint(self):
        pass # TODO
 
if __name__=="__main__":
    unittest.main()
