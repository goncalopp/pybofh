import unittest
import pybofh
from pybofh import lvm, encryption, blockdevice, filesystem

TEST_BLOCKDEVICE= '/dev/vgpersonal/lv_as_pv'
TEST_VG= 'test_lv_pybofh'
LUKS_KEY= '3r9b4g3v9no3'
LUKS_KEYFILE= 'luks_test_keyfile'

class LVMTest(unittest.TestCase):
    def test_lvm(self):
        pv= lvm.PV(TEST_BLOCKDEVICE)
        pv.create()
        pv= blockdevice.BlockDevice(TEST_BLOCKDEVICE).data
        self.assertIsInstance(pv, lvm.PV)
        vg= pv.createVG(TEST_VG)
        lv1= vg.createLV('one')
        lv1.remove()
        vg.remove()
        pv.remove()

class LUKSTest(unittest.TestCase):
    def test_luks(self):
        encryption.create_encrypted(TEST_BLOCKDEVICE, key_file=LUKS_KEYFILE, interactive=False)
        bd= blockdevice.BlockDevice(TEST_BLOCKDEVICE)
        encrypted= bd.data
        decrypted= encrypted.get_inner(key_file=LUKS_KEYFILE)
        with self.assertRaises(Exception):
            inner_size= inner.size
        with decrypted as decrypted:
            size= decrypted.size
            data= decrypted.data

class FilesystemTest(unittest.TestCase):
    def test_filesystem(self):
        bd= blockdevice.BlockDevice(TEST_BLOCKDEVICE)
        filesystem.Ext3.create(TEST_BLOCKDEVICE)
        fs= bd.data
        self.assertIsInstance(fs, filesystem.Ext3)
        size= fs.size
        self.assertGreater(size, 0)
        self.assertLess(size, 1*1024*1024*1024*1024) #1TB


if __name__ == '__main__':
    with open(LUKS_KEYFILE, 'w') as f:
        f.write(LUKS_KEY)
    unittest.main()
