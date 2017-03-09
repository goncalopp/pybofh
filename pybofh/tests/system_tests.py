import os
import os.path
import unittest
import pybofh
from pybofh import lvm, encryption, blockdevice, filesystem, mount

if not __name__=="__main__":
    #these tests should not be run automatically
    unittest = lambda : None
    unittest.TestCase = object

TEST_BLOCKDEVICE= '/dev/vglocal/test_lv'
TEST_MOUNTPOINT= '/media/tmp'
TEST_VG= 'test_vg_pybofh'
TEST_LV= 'test_lv_pybofh'
TEST_LV_SIZE= 500*1024*1024 #500MiB
LUKS_KEY= '3r9b4g3v9no3'
LUKS_KEYFILE= 'luks_test_keyfile'
FILESYSTEM_FILL_RATE=0.8 #how much to fill up a filesystem of data for integrity tests

def hash_file(file_path, hash_cls=None):
    if hash_cls is None:
        hash_cls= hashlib.sha1
    h= hash_cls()
    f= open(file_path)
    blocksize=4*1024*1024 #4MB
    while True:
        data= f.read(blocksize)
        if data=="":
            break
        h.update(data)
    return h.hexdigest()

def hash_dir(dir_path, base_path=None, flat=True):
    from collections import OrderedDict
    import os
    import os.path
    import json
    import hashlib
    def recurse(subdir_path):
        return hash_dir(subdir_path, base_path, flat=False)
    def rel(path):
        return os.path.relpath(path, base_path)
    if base_path is None:
        base_path= dir_path
    contents= [os.path.join(dir_path, x) for x in os.listdir(dir_path)]
    dirs= sorted(filter(os.path.isdir, contents))
    files= sorted(filter(os.path.isfile, contents))
    hash_dict= OrderedDict()
    hash_dict.update({rel(f): hash_file(f, hashlib.sha1) for f in files})
    hash_dict.update({rel(f): recurse(f) for f in dirs}) #makes function recursive
    if flat:
        serialized= json.dumps(hash_dict)
        h= hashlib.sha1()
        h.update(serialized)
        return h.hexdigest()
    else:
        return hash_dict

class FilesystemState(object):
    def __init__(self, blockdevice_path, flat_hash=False):
        self.bd_path= blockdevice_path
        self.flat_hash= flat_hash

    def get_hash(self):
        with mount.Mounted(self.bd_path, TEST_MOUNTPOINT) as mnt:
            h= hash_dir(mnt, flat=self.flat_hash)
        return h

    def set_state(self, state=None):
        state= state or self.get_hash()
        self.last_hash= state


    def check_unmodified(self):
        h= self.get_hash()
        equal= (self.last_hash == h)
        if not equal:
            e= Exception("Filesystem was modified")
            e.last_hash= self.last_hash
            e.currrent_hash= h
            raise e
     
    @staticmethod
    def _create_file_with_garbage(filename, size):
        with open(filename, 'w') as f:
            block_size= 4*1024*1024 #4MB
            garbage= os.urandom(block_size)
            remaining= size
            while remaining:
                write_size= min(remaining, block_size)
                f.write(garbage[:write_size])
                remaining-= write_size


    def fill_with_garbage(self, total_size=None, min_file_size=4*1024**2, max_file_size=200*1024**2):
        '''fills the filesystem with random garbage'''
        import random
        import string
        total_count_size= 0
        with mount.Mounted(self.bd_path, TEST_MOUNTPOINT) as mnt:
            while total_count_size is None or total_count_size<total_size:
                file_size= random.randint(min_file_size, max_file_size)
                if total_size is not None:
                    file_size= min(file_size, total_size - total_count_size)
                filename= "".join(random.choice(string.ascii_lowercase) for x in range(8))
                try:
                    self._create_file_with_garbage(os.path.join(mnt,filename), file_size)
                    total_count_size+= file_size
                except IOError as ex:
                    #assume this is out-of-space.
                    if ex.errno==28 and max_file_size is None:
                        #out of filesystem space, success!
                        return
                    raise #Uh-oh, we cannot write for some reason other than out-of-space


class LVMTest(unittest.TestCase):
    @staticmethod
    def _create_stack(testcase, size=TEST_LV_SIZE):
        pv= lvm.PV(TEST_BLOCKDEVICE)
        pv.create()
        pv= blockdevice.BlockDevice(TEST_BLOCKDEVICE).data
        testcase.assertIsInstance(pv, lvm.PV)
        vg= pv.create_vg(TEST_VG)
        lv1= vg.create_lv(TEST_LV, size) 
        return pv, vg, lv1

    @staticmethod
    def _delete_stack(testcase, pv, vg, lv):
        lv.remove()
        vg.remove()
        pv.remove()

    def test_lvm_creation_and_deletion(self):
        pv, vg, lv= self._create_stack(self)
        self._delete_stack(self, pv, vg, lv)
    
    def test_lvm_resize(self):
        pv, vg, lv= self._create_stack(self)
        old_size= lv.size
        new_size= (old_size / 2)
        gr= lv.resize_granularity
        lv.resize(new_size, no_data=True, interactive=False)
        self.assertLess(lv.size, new_size+gr)
        self.assertGreater(lv.size, new_size-gr)
        lv.resize(old_size, no_data=True, interactive=False)
        self.assertEqual(lv.size, old_size)
        self._delete_stack(self, pv, vg, lv)

    def test_lvm_rename(self):
        pv, vg, lv= self._create_stack(self)
        old_name = lv.name
        new_name = "renamed"
        vg.lv(old_name)
        self.assertRaises(Exception, lambda : vg.lv(new_name))
        lv.rename(new_name)
        self.assertRaises(Exception, lambda : vg.lv(old_name))
        vg.lv(new_name)
        self._delete_stack(self, pv, vg, lv)



class LUKSTest(unittest.TestCase):
    @staticmethod
    def _create_on_bd(testcase, bd, format=True):
        if format:
            encryption.create_encrypted(bd.path, key_file=LUKS_KEYFILE, interactive=False)
        encrypted= bd.data
        decrypted= encrypted.inner
        decrypted.set_params(key_file=LUKS_KEYFILE)
        return encrypted, decrypted

    def _create(testcase, format=True):
        bd= blockdevice.BlockDevice(TEST_BLOCKDEVICE)
        encrypted, decrypted= LUKSTest._create_on_bd(testcase, bd, format)
        return bd, encrypted, decrypted

    def _check_accessable(testcase, decrypted):
        testcase.assertTrue(decrypted.is_open)
        size= decrypted.size
        data= decrypted.data

    def _check_not_accessable(testcase, decrypted):
        testcase.assertTrue(not decrypted.is_open)
        with testcase.assertRaises(Exception):
            inner_size= inner.size

    def test_luks(self):
        bd, encrypted, decrypted= self._create()
        self._check_not_accessable(decrypted)
        with decrypted as decrypted:
            self._check_accessable(decrypted)

    def test_independent_doubleopen(self):
        bd, encrypted, decrypted= self._create()
        bd2, encrypted2, decrypted2= self._create(format=False)
        self._check_not_accessable(decrypted)
        self._check_not_accessable(decrypted2)
        self.assertFalse(decrypted2.is_externally_open)
        with decrypted as decrypted:
            self._check_accessable(decrypted)
            self._check_not_accessable(decrypted2)
            self.assertTrue(decrypted2.is_externally_open)
            with decrypted2 as decrypted2:
                self._check_accessable(decrypted)
                self._check_accessable(decrypted2)
                self.assertEqual(decrypted.path, decrypted2.path)
                self.assertTrue(decrypted2.is_externally_open)
            self._check_accessable(decrypted)
            self._check_not_accessable(decrypted2)
        self._check_not_accessable(decrypted)
        self._check_not_accessable(decrypted2)
        self.assertFalse(decrypted2.is_externally_open)


class FilesystemTest(unittest.TestCase):
    def test_filesystem(self):
        new_size= 500*1024*1024 #500 MB
        strange_size= 525336587 #~=501 MB, prime
        bd= blockdevice.BlockDevice(TEST_BLOCKDEVICE)
        fs_cls= filesystem.Ext3

        #create filesystem
        fs_cls.create(bd.path)
        #check it's on the block device as expected
        fs= bd.data
        self.assertIsInstance(fs, fs_cls)
        self.assertGreater(fs.size, new_size) #we will reduce it
        self.assertLess(fs.size, 1*1024*1024*1024*1024) #1TB
        #fill fs with random data
        debug=False
        fs_state= FilesystemState(bd.path, flat_hash=not debug)
        fs_state.fill_with_garbage(int(new_size*FILESYSTEM_FILL_RATE))
        fs_state.set_state()

        #resize it normally
        fs.resize(new_size)
        self.assertEquals(fs.size, new_size) 
        fs_state.check_unmodified()

        #resize it to a strange size
        fs.resize(strange_size)
        self.assertAlmostEqual(fs.size, strange_size, delta=fs.resize_granularity)
        self.assertGreaterEqual(fs.size, strange_size) 
        fs_state.check_unmodified()

        #resize it to a strange size, rounding down
        fs.resize(strange_size, round_up=False)
        self.assertAlmostEqual(fs.size, strange_size, delta=fs.resize_granularity)
        self.assertLessEqual(fs.size, strange_size) 
        fs_state.check_unmodified()

        #try to resize exactly to a incompatible size
        with self.assertRaises(blockdevice.Resizeable.WrongSize):
            fs.resize(strange_size, approximate=False)
        fs_state.check_unmodified()

class BlockDeviceTest(unittest.TestCase):
    def test_blockdevice_resize(self):
        bd= blockdevice.BlockDevice( TEST_BLOCKDEVICE ) 
        old_size= bd.size
        new_size= bd.size/2
        with self.assertRaises(blockdevice.Resizeable.ResizeError):
            #should fail without the no_data argument
            bd.resize( old_size/2 )
        with self.assertRaises(NotImplementedError):
            #should not be implemented for the non-specific blockdevice
            bd.resize( old_size/2, no_data=True )


class BlockDeviceStackTest(unittest.TestCase):
    DEFAULT_FILESYSTEM= filesystem.Ext3
    @staticmethod
    def _create_stack(testcase, size=TEST_LV_SIZE):
        fs_cls= BlockDeviceStackTest.DEFAULT_FILESYSTEM
        pv, vg, lv= LVMTest._create_stack(testcase, size=size)
        encrypted, decrypted= LUKSTest._create_on_bd(testcase, lv)
        with decrypted:
            fs_cls.create(decrypted.path)
        stack= blockdevice.BlockDeviceStack(lv, key_file=LUKS_KEYFILE)
        return stack, pv, vg, lv, decrypted

    @staticmethod
    def _delete_stack(testcase, stack, pv, vg, lv, decrypted):
        LVMTest._delete_stack(testcase, pv, vg, lv)
 
    def test_stack_basics(self):
        stack, pv, vg, lv, decrypted= BlockDeviceStackTest._create_stack(self)
        old_size= lv.size
        new_size= old_size / 2
        with stack as stack:
            self.assertIsInstance(stack.innermost.data, BlockDeviceStackTest.DEFAULT_FILESYSTEM)
            self.assertEquals(stack.outermost, lv)
            self.assertEquals(list(stack.layers), [lv,decrypted])
        BlockDeviceStackTest._delete_stack(self, stack, pv, vg, lv, decrypted)

    @staticmethod
    def _test_stack_resize(testcase, old_size, new_size, pre_sizes, post_sizes):
        stack, pv, vg, lv, decrypted= BlockDeviceStackTest._create_stack(testcase, size=old_size)
        with stack as stack:
            testcase.assertEquals(stack.layer_and_data_sizes(), pre_sizes)
            fs_state= FilesystemState(stack.innermost.path)
            fs_state.fill_with_garbage(int(min(new_size,old_size)*FILESYSTEM_FILL_RATE))
            fs_state.set_state()

            stack.resize(new_size)

            testcase.assertAlmostEquals(stack.size, new_size, delta=stack.resize_granularity) 
            last_layer_size=float('inf')
            for layer in stack.layers:
                testcase.assertAlmostEquals(layer.size, new_size, delta=stack.total_overhead) 
                testcase.assertAlmostEquals(layer.data.size, new_size, delta=stack.total_overhead) 
                testcase.assertLessEqual(layer.size, last_layer_size)
                testcase.assertLessEqual(layer.data.size, layer.size)
                last_layer_size= layer.data.size
            fs_state.check_unmodified()
            testcase.assertEquals(stack.layer_and_data_sizes(), post_sizes)
        BlockDeviceStackTest._delete_stack(testcase, stack, pv, vg, lv, decrypted)

    def test_stack_resize_down(self):
        pre_sizes= [524288000, 524288000, 522190848, 522190848]
        post_sizes= [264241152, 264241152, 262144000, 262144000]
        BlockDeviceStackTest._test_stack_resize(self, TEST_LV_SIZE, TEST_LV_SIZE/2, pre_sizes, post_sizes)

    def test_stack_resize_up(self):
        pre_sizes= [264241152, 264241152, 262144000, 262144000]
        post_sizes= [524288000, 524288000, 522190848, 522190848]
        BlockDeviceStackTest._test_stack_resize(self, TEST_LV_SIZE/2, TEST_LV_SIZE, pre_sizes, post_sizes)


if __name__ == '__main__':
    assert os.path.exists(TEST_BLOCKDEVICE)
    assert os.path.exists(TEST_MOUNTPOINT)
    with open(LUKS_KEYFILE, 'w') as f:
        f.write(LUKS_KEY)
    unittest.main()
