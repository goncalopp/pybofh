'''Tests for mount.py'''

import unittest
import mock
from pybofh.mount import Mounted, NestedMounted, MountPool, mount, unmount
from pybofh import shell

DEVS = ('/dev/in1', '/dev/in2', '/dev/in3', '/dev/in4')
MTS = ('/mnt/in1', '/mnt/in2', '/mnt/in3')

def generic_setup():
    mocklist = [
        'os.path.isdir',
        'pybofh.shell.run_process'
        ]
    patches = [mock.patch(a, autospec=True) for a in mocklist]
    for patch in patches:
        patch.start()

class MountedTest(unittest.TestCase):
    def setUp(self):
        generic_setup()

    def tearDown(self):
        mock.patch.stopall()

    def test_create(self):
        m = Mounted(DEVS[0], MTS[0])
        self.assertIsInstance(m, Mounted)

    def test_mount(self):
        m = Mounted(DEVS[0], MTS[0])
        with m:
            shell.run_process.assert_called_once_with(('/bin/mount', DEVS[0], MTS[0]))
        shell.run_process.assert_called_with(('/bin/umount', MTS[0]))
        self.assertEqual(len(shell.run_process.mock_calls), 2)

class NestedMountedTest(unittest.TestCase):
    def setUp(self):
        generic_setup()

    def tearDown(self):
        mock.patch.stopall()

    def test_create(self):
        m = NestedMounted([(DEVS[0], '/mnt/inexistent'), (DEVS[1], '/mnt/inexistent/boot')])
        self.assertIsInstance(m, NestedMounted)

    def test_mount(self):
        m = NestedMounted([(DEVS[0], '/mnt/inexistent'), (DEVS[1], '/mnt/inexistent/boot')])
        with m:
            shell.run_process.assert_has_calls([
                mock.call(('/bin/mount', DEVS[0], '/mnt/inexistent')),
                mock.call(('/bin/mount', DEVS[1], '/mnt/inexistent/boot'))])
        shell.run_process.assert_has_calls([
            mock.call(('/bin/umount', '/mnt/inexistent/boot')),
            mock.call(('/bin/umount', '/mnt/inexistent'))])
        self.assertEqual(len(shell.run_process.mock_calls), 4)

class MountPoolTest(unittest.TestCase):
    def setUp(self):
        generic_setup()

    def tearDown(self):
        mock.patch.stopall()
 
    def test_mount(self):
        m = MountPool(MTS[:3])
        with m.mount(DEVS[0]):
            shell.run_process.assert_called_with(('/bin/mount', DEVS[0], MTS[0]))
            with m.mount(DEVS[1]):
                shell.run_process.assert_called_with(('/bin/mount', DEVS[1], MTS[1]))
                with m.mount(DEVS[2]):
                    shell.run_process.assert_called_with(('/bin/mount', DEVS[2], MTS[2]))
                shell.run_process.assert_called_with(('/bin/umount', MTS[2]))
            shell.run_process.assert_called_with(('/bin/umount', MTS[1]))
        shell.run_process.assert_called_with(('/bin/umount', MTS[0]))

    def test_mount_overflow(self):
        m = MountPool(MTS[:1])
        with m.mount(DEVS[0]):
            shell.run_process.assert_called_with(('/bin/mount', DEVS[0], MTS[0]))
            try:
                with m.mount(DEVS[1]):
                    self.assertTrue(False)
            except:
                pass
        shell.run_process.assert_called_with(('/bin/umount', MTS[0]))

class ModuleFunctionsTest(unittest.TestCase):
    def setUp(self):
        generic_setup()

    def tearDown(self):
        mock.patch.stopall()

    def test_mount(self):
        mount(DEVS[0], MTS[0])
        shell.run_process.assert_called_once_with(('/bin/mount', DEVS[0], MTS[0]))
 
    def test_umount(self):
        unmount(MTS[0])
        shell.run_process.assert_called_once_with(('/bin/umount', MTS[0]))

    def test_is_mountpoint(self):
        pass # TODO
 
if __name__=="__main__":
    unittest.main()
