import os
import unittest
import pybofh
from pybofh import lvm, encryption, blockdevice, filesystem, mount

TEST_BLOCKDEVICE= '/dev/vgpersonal/lv_as_pv'
TEST_MOUNTPOINT= '/media/tmp'
TEST_VG= 'test_lv_pybofh'
LUKS_KEY= '3r9b4g3v9no3'
LUKS_KEYFILE= 'luks_test_keyfile'

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
    def __init__(self, blockdevice, flat_hash=False):
        self.bd= blockdevice
        self.flat_hash= flat_hash

    def get_hash(self):
        with mount.Mounted(self.bd.path, TEST_MOUNTPOINT) as mnt:
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
        with mount.Mounted(self.bd.path, TEST_MOUNTPOINT) as mnt:
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
    def _create(testcase):
        encryption.create_encrypted(TEST_BLOCKDEVICE, key_file=LUKS_KEYFILE, interactive=False)
        bd= blockdevice.BlockDevice(TEST_BLOCKDEVICE)
        return bd

    def test_luks(self):
        bd= self._create()
        encrypted= bd.data
        decrypted= encrypted.get_inner(key_file=LUKS_KEYFILE)
        with self.assertRaises(Exception):
            inner_size= inner.size
        with decrypted as decrypted:
            size= decrypted.size
            data= decrypted.data

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
        fs_state= FilesystemState(bd, flat_hash=not debug)
        fs_state.fill_with_garbage(int(new_size*0.8))
        fs_state.set_state()

        #resize it
        fs.resize(new_size)
        self.assertEquals(fs.size, new_size) 
        fs_state.check_unmodified()

        fs.resize(strange_size)
        self.assertAlmostEqual(fs.size, strange_size, delta=fs.resize_granularity)
        self.assertLessEqual(fs.size, strange_size) 
        fs_state.check_unmodified()

        fs.resize(strange_size, round_up=True)
        self.assertAlmostEqual(fs.size, strange_size, delta=fs.resize_granularity)
        self.assertGreaterEqual(fs.size, strange_size) 
        fs_state.check_unmodified()

        with self.assertRaises(blockdevice.Resizeable.WrongSize):
            fs.resize(strange_size, approximate=False)
        fs_state.check_unmodified()


if __name__ == '__main__':
    with open(LUKS_KEYFILE, 'w') as f:
        f.write(LUKS_KEY)
    unittest.main()
