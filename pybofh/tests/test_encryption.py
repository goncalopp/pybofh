"""Tests for encryption.py"""
# pylint: disable=no-member
# pylint: disable=maybe-no-member
# pylint: disable=too-many-public-methods
import unittest
import mock
from pybofh.tests import common
from pybofh.tests.common import FakeDevice
from pybofh import encryption
from pybofh import blockdevice

LUKS_HEADER = """LUKS\xba\xbe\x00\x01aes\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00xts-plain64\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00sha1\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00 WX\xa6\xda\xe5\xf1G\xc4\xe2/%\x9c\\\xd3y\xcf/\xd9\xac\xb5P\xee\x0bH$nT\x9b\x97\xb9\xb5a\xe8\x1c\xbf\x0fU%o\xca\xc9\xbe}{H\xe0\x91\xe8\x17\x94z\xea\x00\x02\xb2n52bdc10e-de99-44dc-95af-05068338a84b\x00\x00\x00\x00\x00\xacq\xf3\x00\n\xcamc\x8b\x97\x04jb\x98\x1c\xa1-x\xee`\x8a\xcaZ\x0c\xf1\x19\xb2|!8^\xa5$\xde\xd7\x03\xc4z\x91\x00\x00\x00\x08\x00\x00\x0f\xa0\x00\x00\xde\xad"""

class FakeEnvironment(common.FakeEnvironment):
    """FakeEnvironment"""
    def __init__(self):
        common.FakeEnvironment.__init__(self)
        self.shell.add_fake_binary("/sbin/cryptsetup", self.cryptsetup)
        self.shell.add_fake_binary("/sbin/blockdev", self.blockdev)

    def cryptsetup(self, command):
        """Implements a fake cryptsetup command"""
        open_commands = ("luksOpen", "open")
        close_commands = ("luksClose", "close")
        assert command[0].endswith("cryptsetup")
        if command[1] in open_commands + close_commands:
            is_open = command[1] in open_commands
            if is_open:
                name = command[3]
            else:
                name = command[2]
                if "/" in name:
                    # user specified the encrypted path, not the name
                    name = encryption.luks_name(name)
            decrypted_path = encryption.luks_path(name)
            fakedevice = self.get_device(decrypted_path, active=not is_open, enforce=True)
            if is_open:
                self.activate_device(fakedevice)
            else:
                self.deactivate_device(fakedevice)
        elif command[1] == "resize":
            assert len(command) == 5
            assert command[2] == "--size"
            decrypted_path = command[4]
            fakedevice = self.get_device(decrypted_path, enforce=True)
            fakedevice.size = encryption.LUKS_SECTOR_SIZE * int(command[3])
        elif command[1] == "luksFormat":
            fakedevice = self.get_device(command[-1], enforce=True)
            # noop
        else:
            raise Exception("Unimplemented cryptsetup fake command: {}".format(command))

    def blockdev(self, command):
        """Implements the blockdev fake command"""
        assert command[0].endswith("blockdev")
        if command[1] != "--getsize64" or len(command) != 3:
            raise NotImplementedError
        device = self.get_device(command[2])
        if not device:
            raise Exception("FakeDevice not found for path: {}".format(command[2]))
        return device.size

def generic_setup(test_instance):
    """Setups mocks"""
    # pylint: disable=unnecessary-lambda, star-args
    env = FakeEnvironment()
    test_instance.env = env

    mocklist = [
        {"target": "pybofh.shell.get", "side_effect": lambda: env.shell},
        ]
    patches = [mock.patch(autospec=True, **a) for a in mocklist] + [
        mock.patch("pybofh.tests.common.get_fake_environment", new=env),
        mock.patch("pybofh.misc.read_file", new=env.read_file),
        mock.patch("os.path.exists", new=env.path_exists),
        ]
    for patch in patches:
        patch.start()

class EncryptedTest(unittest.TestCase):
    def setUp(self):
        generic_setup(self)
        self.bd = FakeDevice("/dev/bd1", content=LUKS_HEADER)
        self.env.add_device(self.bd)

    def tearDown(self):
        mock.patch.stopall()

    def test_init(self):
        e = encryption.Encrypted(self.bd.path)
        self.assertIsInstance(e, encryption.Encrypted)

    def test_size(self):
        e = encryption.Encrypted(self.bd.path)
        self.assertEquals(e.size, self.bd.size)

    def test_resize_granularity(self):
        e = encryption.Encrypted(self.bd.path)
        self.assertEquals(e.resize_granularity, 512)

    def test_inner(self):
        e = encryption.Encrypted(self.bd.path)
        self.assertIsInstance(e.inner, encryption.Decrypted)

    def test_resize(self):
        e = encryption.Encrypted(self.bd.path)
        with self.assertRaises(blockdevice.NotReady):
            e.resize(2**20) # 1MB

class DecryptedTest(unittest.TestCase):
    def setUp(self):
        generic_setup(self)
        self.outer = FakeDevice("/dev/something", content=LUKS_HEADER)
        self.env.add_device(self.outer)
        self.inner = FakeDevice(encryption.luks_path("something"), size=self.outer.size - encryption.luks_data_offset(self.outer.path))
        self.env.add_device(self.inner, active=False)

    def tearDown(self):
        mock.patch.stopall()

    def test_init(self):
        e = encryption.Encrypted(self.outer.path)
        d = e.inner
        self.assertIsInstance(d, encryption.Decrypted)

    def test_open(self):
        e = encryption.Encrypted(self.outer.path)
        with mock.patch("pybofh.blockdevice.get_blockdevice_child", new=lambda path: None):
            with e.inner:
                self.assertIn(("/sbin/cryptsetup", "luksOpen", "/dev/something", "something"), self.env.shell.run_commands)
            self.assertIn(("/sbin/cryptsetup", "luksClose", "/dev/mapper/something"), self.env.shell.run_commands)

    def test_open_alreadyopen(self):
        e = encryption.Encrypted(self.outer.path)
        self.env.activate_device(self.inner)
        with mock.patch("pybofh.blockdevice.get_blockdevice_child", new=lambda path: self.inner.path):
            with e.inner:
                pass
            self.assertNotIn(("/sbin/cryptsetup", "luksOpen", "/dev/something", "something"), self.env.shell.run_commands)
            self.assertNotIn(("/sbin/cryptsetup", "luksClose", "/dev/mapper/something"), self.env.shell.run_commands)

    def test_resize_granularity(self):
        e = encryption.Encrypted(self.outer.path)
        self.assertEqual(e.inner.resize_granularity, 512)

    def test_resize(self):
        original_encrypted_size = self.outer.size
        original_decrypted_size = self.inner.size
        e = encryption.Encrypted(self.outer.path)
        with mock.patch("pybofh.blockdevice.get_blockdevice_child", new=lambda path: None):
            with self.assertRaises(blockdevice.NotReady):
                e.inner.resize(2**20, no_data=True) # 1MB
            self.assertEqual(e.size, original_encrypted_size)
            with e.inner:
                self.assertEqual(e.inner.size, original_decrypted_size)
                e.inner.resize(2**20, no_data=True) # 1MB
                self.assertIn(("/sbin/cryptsetup", "resize", "--size", "2048", "/dev/mapper/something"), self.env.shell.run_commands)
                self.assertEqual(e.inner.size, 2**20)
                # while open, we can see the true size of the data
                self.assertEqual(e.size, 2**20 + encryption.luks_data_offset(self.outer.path))
            # after being closed, the data size is opaque
            self.assertEqual(e.size, original_encrypted_size)

class ModuleTest(unittest.TestCase):
    def setUp(self):
        generic_setup(self)
        self.bd = FakeDevice("/dev/something")
        self.env.add_device(self.bd)

    def tearDown(self):
        mock.patch.stopall()

    def test_create_encrypted(self):
        encryption.create_encrypted(self.bd.path)
        self.assertEqual(self.env.shell.run_commands[-1], ("/sbin/cryptsetup", "luksFormat", "/dev/something"))


