'''Tests for filesystem.py'''

import unittest
import mock
from pybofh import filesystem
from pybofh.tests import common
from pybofh.tests.common import FakeDevice

def generic_setup(test_instance):
    '''Setups mocks'''
    env = test_instance.env = common.FakeEnvironment()
    env.shell.add_fake(lambda command: "mkfs." in command[0], None)
    env.shell.add_fake(lambda command: "e2fsck" in command[0], None)
    bd = test_instance.bd = FakeDevice('/dev/inexistent')
    env.add_device(bd)
    patches = [
        mock.patch("os.path.exists", env.path_exists),
        mock.patch("pybofh.shell.get", lambda: env.shell),
        ]
    for patch in patches:
        patch.start()

class Ext2Test(unittest.TestCase):
    def setUp(self):
        generic_setup(self)

    def tearDown(self):
        mock.patch.stopall()

    def test_init(self):
        fs = filesystem.Ext2(self.bd.path)
        self.assertIsInstance(fs, filesystem.Ext2)

    def test_create(self):
        fs = filesystem.Ext2.create(self.bd.path)
        self.assertEquals(self.env.shell.run_commands[-1], ("mkfs.ext2", "/dev/inexistent"))
        self.assertIsInstance(fs, filesystem.Ext2)

    def test_fsck(self):
        fs = filesystem.Ext2.create(self.bd.path)
        fs.fsck()
        self.assertEquals(self.env.shell.run_commands[-1], ("e2fsck", "-f", "-p", "/dev/inexistent"))
  
class Ext3Test(unittest.TestCase):
    def setUp(self):
        generic_setup(self)

    def tearDown(self):
        mock.patch.stopall()

    def test_init(self):
        fs = filesystem.Ext3(self.bd.path)
        self.assertIsInstance(fs, filesystem.Ext3)

    def test_create(self):
        fs = filesystem.Ext3.create(self.bd.path)
        self.assertEquals(self.env.shell.run_commands[-1], ("mkfs.ext3", "/dev/inexistent"))
        self.assertIsInstance(fs, filesystem.Ext3)

    def test_fsck(self):
        fs = filesystem.Ext3.create(self.bd.path)
        fs.fsck()
        self.assertEquals(self.env.shell.run_commands[-1], ("e2fsck", "-f", "-p", "/dev/inexistent"))

class Ext4Test(unittest.TestCase):
    def setUp(self):
        generic_setup(self)

    def tearDown(self):
        mock.patch.stopall()

    def test_init(self):
        fs = filesystem.Ext4(self.bd.path)
        self.assertIsInstance(fs, filesystem.Ext4)

    def test_create(self):
        fs = filesystem.Ext4.create(self.bd.path)
        self.assertEquals(self.env.shell.run_commands[-1], ("mkfs.ext4", "/dev/inexistent"))
        self.assertIsInstance(fs, filesystem.Ext4)

    def test_fsck(self):
        fs = filesystem.Ext4.create(self.bd.path)
        fs.fsck()
        self.assertEquals(self.env.shell.run_commands[-1], ("e2fsck", "-f", "-p", "/dev/inexistent"))


class ModuleTest(unittest.TestCase):
    def setUp(self):
        generic_setup(self)

    def tearDown(self):
        mock.patch.stopall()

if __name__ == "__main__":
    unittest.main()
