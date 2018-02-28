# -*- coding: utf-8 -*-
"""Tests for blockdevice.py"""
# pylint: disable=no-member
# pylint: disable=no-self-use
# pylint: disable=protected-access
# pylint: disable=pointless-statement
# pylint: disable=too-many-public-methods

import unittest
import mock
from pybofh import blockdevice
from pybofh.tests import common
from pybofh.tests.common import FakeDevice

LSBLK_DATA = """NAME                                MAJ:MIN RM  SIZE RO TYPE  MOUNTPOINT
sda                                   8:0    0  2.7T  0 disk  
├─sda1                                8:1    0  1.8T  0 part  
│ └─md0                               9:0    0  1.8T  0 raid1 
│   ├─md0p1                         259:0    0   32G  0 md    
│   │ ├─vg01-something00            254:14   0    8G  0 lvm   
│   │ ├─vg01-something01            254:16   0    2G  0 lvm   
│   │ │ └─something001              254:26   0    2G  0 crypt 
│   │ └─vg01-something02            254:17   0    1G  0 lvm   
│   └─md0p2                         259:1    0  1.5T  0 md    
│     ├─vg02-something03            254:1    0    5G  0 lvm   
└─sda2                                8:2    0    8G  0 part  
sdb                                   8:32   1  7.5G  0 disk  
├─sdb1                                8:33   1  121M  0 part  /home
└─sdb5                                8:37   1  2.8G  0 part  
  └─vg03-something04                254:0    0  2.8G  0 lvm   /media/something4
"""

DMSETUP_INFO_DATA = """Name:              vg01-lv01
State:             ACTIVE
Read Ahead:        256
Tables present:    LIVE
Open count:        1
Event number:      0
Major, minor:      253, 3
Number of targets: 3
UUID: LVM-0bIWK7rs4OtKBT3YAk9qJpnSa19Yj4pbAR5j79MUV5HFIst4JF0McYNuq9avYXBC

"""
# Aux classes for testing -------------------------------------------

class SimpleResizeable(blockdevice.Resizeable):
    GRANULARITY = 29
    MINIMUM = 0
    MAXIMUM = GRANULARITY * 1000
    def __init__(self, size=290):
        blockdevice.Resizeable.__init__(self)
        self._simple_size = size
        assert self._simple_size % self.GRANULARITY == 0

    @property
    def resize_granularity(self):
        return self.GRANULARITY

    def _size(self):
        assert self._simple_size % self.GRANULARITY == 0
        return self._simple_size

    def _resize(self, byte_size, minimum, maximum, interactive, **kwargs):
        if minimum:
            self._simple_size = self.MINIMUM
        elif maximum:
            self._simple_size = self.MAXIMUM
        else:
            self._simple_size = byte_size
            assert self._simple_size % self.GRANULARITY == 0

class SimpleOpenable(blockdevice.Openable):
    def __init__(self, open_data='data', externally_open_data=None):
        blockdevice.Openable.__init__(self)
        self._simple_open_data = open_data
        self._simple_externally_open_data = externally_open_data

    def _open(self):
        return self._simple_open_data

    def _close(self):
        pass

    def _externally_open_data(self):
        return self._simple_externally_open_data

class SimpleParametrizable(blockdevice.Parametrizable):
    @property
    def accepted_params(self):
        return ('a', 'b', 'c')

class SimpleBlockDevice(blockdevice.BlockDevice):
    @property
    def fakedevice(self):
        return common.get_fake_environment().get_device(self.path)

    @property
    def resize_granularity(self):
        if self.fakedevice:
            return self.fakedevice.granularity
        else:
            return blockdevice.BlockDevice.resize_granularity(self)

    def _resize(self, byte_size, minimum, maximum, _, **kwargs):
        if self.fakedevice:
            if minimum or maximum:
                raise NotImplementedError
            self.fakedevice.size = byte_size
        else:
            raise Exception("Not a fake device")

class SimpleData(blockdevice.Data):
    def __init__(self, bd):
        blockdevice.Data.__init__(self, bd)
        self._simple_size = bd.size #starts as the size of the container blockdevice

    def _resize(self, byte_size, minimum, maximum, interactive, **kwargs):
        if minimum or maximum:
            raise NotImplementedError
        self._simple_size = byte_size

    @property
    def resize_granularity(self):
        return 1

    def _size(self):
        return self.device.size if self._simple_size is None else self._simple_size

class SimpleOuterLayer(blockdevice.OuterLayer):
    def __init__(self, bd):
        self._simple_size = bd.size #starts as the size of the container blockdevice
        blockdevice.OuterLayer.__init__(self, bd)
        self.resize_overhead = 'constant'

    @property
    def _inner_layer_class(self):
        return SimpleInnerLayer

    def _resize(self, byte_size, minimum, maximum, interactive, **kwargs):
        #resizes the innerlayer as well
        if minimum or maximum:
            raise NotImplementedError
        old_size = self._simple_size
        new_size = byte_size
        self._simple_size = new_size
        if self.resize_overhead == 'zero':
            self.inner.fakedevice.size = new_size
        elif self.resize_overhead == 'constant':
            overhead = old_size - self.inner.fakedevice.size
            self.inner.fakedevice.size = new_size - overhead
        else:
            raise Exception("SimpleOuterLayer has invalid resize_overhead: " + self.resize_overhead)


    @property
    def resize_granularity(self):
        return 1

    def _size(self):
        return self._simple_size

class SimpleInnerLayer(blockdevice.InnerLayer):
    def __init__(self, outer_layer, **kwargs):
        blockdevice.InnerLayer.__init__(self, outer_layer, **kwargs)
        self._simple_size = outer_layer.size
        self.outer_layer = outer_layer

    @property
    def fakedevice(self):
        return self.outer_layer.device.fakedevice.child

    def _close(self):
        pass

    def _open(self, **_):
        return self.fakedevice.path

    def _resize(self, byte_size, minimum, maximum, interactive, **kwargs):
        byte_size = byte_size + (self.outer_layer.size - self.size) if byte_size is not None else None
        self.outer_layer._resize(byte_size, minimum, maximum, interactive)

    @property
    def resize_granularity(self):
        return self.fakedevice.granularity

    def _size(self):
        return self.fakedevice.size

class FakeEnvironment(common.FakeEnvironment):
    def __init__(self):
        common.FakeEnvironment.__init__(self)
        self.shell.add_fake('/bin/lsblk', LSBLK_DATA)
        self.shell.add_fake(('/sbin/dmsetup', 'info', '/dev/mapper/vg01-lv01'), DMSETUP_INFO_DATA)

# Module level constants / vars / code  --------------------------------------

blockdevice.register_data_class('SimpleData', SimpleData)
blockdevice.register_data_class('SimpleOuterLayer', SimpleOuterLayer)

def generic_setup(test_instance):
    '''Setups mocks'''
    env = FakeEnvironment()
    test_instance.env = env

    mocklist = [
        {"target": "pybofh.shell.get", "side_effect": lambda: env.shell},
        ]
    patches = [mock.patch(autospec=True, **a) for a in mocklist] + [
        mock.patch('pybofh.blockdevice.blockdevice_from_path', new=SimpleBlockDevice),
        mock.patch('pybofh.tests.common.get_fake_environment', new=lambda: env),
        mock.patch('os.path.exists', new=env.path_exists),
        ]
    for patch in patches:
        patch.start()

# Tests ----------------------------------------------------------


class ResizeableTest(unittest.TestCase):
    def test_init(self):
        r = SimpleResizeable()
        self.assertIsInstance(r, blockdevice.Resizeable)

    def test_size(self):
        gr = SimpleResizeable.GRANULARITY
        r = SimpleResizeable(gr * 3)
        self.assertEqual(r.size, gr * 3)

    def test_resize_default(self):
        gr = SimpleResizeable.GRANULARITY
        r = SimpleResizeable(gr * 3)
        r.resize(gr * 3 + 1)
        self.assertEqual(r.size, gr * 4) # rounds up by default

    def test_resize_minimum(self):
        gr = SimpleResizeable.GRANULARITY
        r = SimpleResizeable(gr * 3)
        r.resize(minimum=True)
        self.assertEqual(r.size, r.MINIMUM)

    def test_resize_maximum(self):
        gr = SimpleResizeable.GRANULARITY
        r = SimpleResizeable(gr * 3)
        r.resize(maximum=True)
        self.assertEqual(r.size, r.MAXIMUM)

    def test_resize_round_up(self):
        gr = SimpleResizeable.GRANULARITY
        r = SimpleResizeable(gr * 3)
        r.resize(gr * 3 + 1, round_up=True)
        self.assertEqual(r.size, gr * 4)

    def test_resize_round_down(self):
        gr = SimpleResizeable.GRANULARITY
        r = SimpleResizeable(gr * 3)
        r.resize(gr * 3 + 1, round_up=False)
        self.assertEqual(r.size, gr * 3)

    def test_resize_exact(self):
        gr = SimpleResizeable.GRANULARITY
        r = SimpleResizeable(gr * 3)
        with self.assertRaises(blockdevice.Resizeable.ResizeError):
            r.resize(gr * 3 + 1, approximate=False)
        self.assertEqual(r.size, gr * 3)
        r.resize(gr * 4, approximate=False)
        self.assertEqual(r.size, gr * 4)

class OpenableTest(unittest.TestCase):
    def test_init(self):
        r = SimpleOpenable()
        self.assertIsInstance(r, blockdevice.Openable)

    def test_open_function(self):
        r = SimpleOpenable()
        self.assertEqual(r.is_open, False)
        r.open()
        self.assertEqual(r.is_open, True)
        r.close()
        self.assertEqual(r.is_open, False)

    def test_open_contextmanager(self):
        r = SimpleOpenable()
        self.assertEqual(r.is_open, False)
        with r:
            self.assertEqual(r.is_open, True)
        self.assertEqual(r.is_open, False)

    def test_open_double_function(self):
        r = SimpleOpenable()
        r.open()
        with self.assertRaises(blockdevice.Openable.AlreadyOpen):
            r.open()

    def test_open_double_contextmanager(self):
        r = SimpleOpenable()
        with r:
            with self.assertRaises(blockdevice.Openable.AlreadyOpen):
                with r:
                    pass

    def test_close_unopened(self):
        r = SimpleOpenable()
        with self.assertRaises(blockdevice.Openable.AlreadyOpen):
            r.close()

    def test_close_double(self):
        r = SimpleOpenable()
        r.open()
        r.close()
        with self.assertRaises(blockdevice.Openable.AlreadyOpen):
            r.close()

    def test_open_externally_open(self):
        # open() when not externally open
        r = SimpleOpenable(open_data='xyz')
        r._on_open = mock.Mock(r._on_open)
        self.assertFalse(r.is_externally_open)
        r.open()
        r._on_open.assert_called_with('xyz', True) # a true open
        # open when externally open
        r = SimpleOpenable(externally_open_data='xyz')
        r._on_open = mock.Mock(r._on_open)
        self.assertTrue(r.is_externally_open)
        self.assertFalse(r.is_open) # Externally open doesn't count as open
        r.open()
        r._on_open.assert_called_with('xyz', False) # a fake open
        self.assertTrue(r.is_open) # Externally open doesn't count as open

class ParametrizableTest(unittest.TestCase):
    def test_init(self):
        r = SimpleParametrizable()
        self.assertIsInstance(r, blockdevice.Parametrizable)

    def test_init_params(self):
        r = SimpleParametrizable(a=1)
        self.assertIsInstance(r, blockdevice.Parametrizable)
        self.assertEqual(r._params, {'a': 1})

    def test_init_multi_params(self):
        r = SimpleParametrizable(a=1, b='', c=None)
        self.assertIsInstance(r, blockdevice.Parametrizable)
        self.assertEqual(r._params, {'a': 1, 'b': '', 'c': None})

    def test_init_unrecognized_params(self):
        r = SimpleParametrizable(a=1, z=2)
        self.assertEqual(r._params, {'a': 1})

class BlockdeviceTest(unittest.TestCase):
    def setUp(self):
        generic_setup(self)
        self.bd = FakeDevice('/dev/inexistent', SimpleData)
        self.env.add_device(self.bd)

    def tearDown(self):
        mock.patch.stopall()

    def test_init(self):
        b = blockdevice.BlockDevice(self.bd.path)
        self.assertIsInstance(b, blockdevice.BlockDevice)

    def test_size(self):
        b = blockdevice.BlockDevice(self.bd.path)
        self.assertEquals(b.size, self.bd.size)
        self.assertEquals(self.env.shell.run_commands[-1], ('/sbin/blockdev', '--getsize64', self.bd.path))

    def test_size_badgranularity(self):
        self.bd.granularity = 10
        #
        # good size
        self.bd.size = 20
        # We need to use SimpleBlockDevice instead of BlockDevice for the granularity implementation
        b = blockdevice.blockdevice(self.bd.path)
        b.size
        #
        #bad size
        self.bd.size = 11
        b = blockdevice.blockdevice(self.bd.path)
        with self.assertRaises(blockdevice.Resizeable.WrongSize):
            b.size

    def test_data(self):
        b = blockdevice.BlockDevice(self.bd.path)
        data = b.data
        # getting the data uses file to check the format of content in the blockdevice
        self.assertIn(('file', '--special', '--dereference', self.bd.path), self.env.shell.run_commands)
        self.assertIsInstance(data, SimpleData) # SimpleData is registered in this test file

    def test_data_identity(self):
        # getting .data twice should return the same object
        b = blockdevice.BlockDevice(self.bd.path)
        data = b.data
        self.assertTrue(b.data is data)
        self.assertTrue(b.data is data) # even when called thrice
        # except if the data type changes
        mock.patch('pybofh.blockdevice.get_data_class_for', return_value=lambda bd: object).start()
        self.assertFalse(b.data is data)

    def test_path(self):
        b = blockdevice.BlockDevice(self.bd.path)
        self.assertEqual(b.path, self.bd.path)

    def test_resize(self):
        b = blockdevice.BlockDevice(self.bd.path)
        with self.assertRaises(blockdevice.Resizeable.ResizeError):
            # Should refuse to resize unless no_data arg is provided
            b.resize(-100, relative=True)
        self.assertEqual(len(self.env.shell.run_commands), 0)
        with self.assertRaises(NotImplementedError):
            # resize is not implemented for base BlockDevice
            b.resize(-100, relative=True, no_data=True)

class OuterLayerTest(unittest.TestCase):
    def setUp(self):
        self.l0 = FakeDevice('/dev/inexistent_l0', SimpleOuterLayer)
        self.l1 = FakeDevice('/dev/inexistent_l1', SimpleData, parent=self.l0)
        generic_setup(self)
        self.env.add_device(self.l0)
        self.env.add_device(self.l1)

    def tearDown(self):
        mock.patch.stopall()

    def test_init(self):
        ol = blockdevice.blockdevice(self.l0.path)
        self.assertIsInstance(ol.data, blockdevice.OuterLayer)

    def test_inner(self):
        ol = blockdevice.blockdevice(self.l0.path)
        inner = ol.data.inner
        self.assertIsInstance(inner, SimpleInnerLayer)

    def test_overhead(self):
        ol = blockdevice.blockdevice(self.l0.path)
        mock.patch('pybofh.blockdevice.InnerLayer._externally_open_data', return_value=None).start()
        with ol.data.inner:
            self.assertEqual(ol.data.overhead, 0)
        self.l1.size -= 100
        self.assertEqual(ol.data.overhead, 100)

class InnerLayerTest(unittest.TestCase):
    def setUp(self):
        self.l0 = FakeDevice('/dev/inexistent_l0', SimpleOuterLayer)
        self.l1 = FakeDevice('/dev/inexistent_l1', SimpleData, parent=self.l0)
        generic_setup(self)
        self.env.add_device(self.l0)

    def tearDown(self):
        mock.patch.stopall()

    def test_init(self):
        ol = blockdevice.blockdevice(self.l0.path)
        self.assertIsInstance(ol.data.inner, blockdevice.InnerLayer)

    def test_outer(self):
        ol = blockdevice.blockdevice(self.l0.path)
        inner = ol.data.inner
        self.assertTrue(inner.outer is ol.data)

    def test_is_externally_open(self):
        # pylint: disable=maybe-no-member
        ol = blockdevice.blockdevice(self.l0.path)
        inner = ol.data.inner
        patch = mock.patch('pybofh.blockdevice.InnerLayer._externally_open_data', return_value=None).start()
        self.assertFalse(inner.is_externally_open)
        patch.stop()
        patch = mock.patch('pybofh.blockdevice.InnerLayer._externally_open_data', return_value="something").start()
        self.assertTrue(inner.is_externally_open)

class BlockDeviceStackTest(unittest.TestCase):
    def setUp(self):
        self.l0 = FakeDevice('/dev/inexistent_l0', SimpleOuterLayer)
        self.l1 = FakeDevice('/dev/inexistent_l1', SimpleOuterLayer, parent=self.l0)
        self.l2 = FakeDevice('/dev/inexistent_l2', SimpleData, parent=self.l1)
        generic_setup(self)
        self.env.add_device(self.l0)
        self.env.add_device(self.l1)
        self.env.add_device(self.l2)
        mock.patch('pybofh.blockdevice.InnerLayer._externally_open_data', return_value=None).start()

    def tearDown(self):
        mock.patch.stopall()

    def test_init(self):
        st = blockdevice.BlockDeviceStack(self.l0.path)
        self.assertIsInstance(st, blockdevice.BlockDeviceStack)

    def test_open(self):
        st = blockdevice.BlockDeviceStack(self.l0.path)
        with st:
            self.assertEqual(st.is_open, True)
        self.assertEqual(st.is_open, False)

    def test_layers(self):
        st = blockdevice.BlockDeviceStack(self.l0.path)
        with self.assertRaises(blockdevice.NotReady):
            st.layers
        with st:
            self.assertEqual([l.path for l in st.layers], [self.l0.path, self.l1.path, self.l2.path])
            for l in st.layers:
                self.assertEqual(st.is_open, True)

    def test_innermost_and_outermost(self):
        st = blockdevice.BlockDeviceStack(self.l0.path)
        self.assertEquals(st.outermost.path, self.l0.path)
        with self.assertRaises(blockdevice.NotReady):
            st.innermost
        with st:
            self.assertEquals(st.outermost.path, self.l0.path)
            self.assertEquals(st.innermost.path, self.l2.path)

    def test_size(self):
        st = blockdevice.BlockDeviceStack(self.l0.path)
        self.assertEquals(st.size, self.l0.size)
        self.assertEquals(st.size, st.outermost.size)

    def test_total_overhead(self):
        self.l0.size = 50
        self.l1.size = 50
        self.l2.size = 50
        st = blockdevice.BlockDeviceStack(self.l0.path)
        with st:
            self.assertEquals(st.total_overhead, 0 + 0)
        self.l0.size = 50
        self.l1.size = 50
        self.l2.size = 30
        st = blockdevice.BlockDeviceStack(self.l0.path)
        with st:
            self.assertEquals(st.total_overhead, 0 + 20)
        self.l0.size = 50
        self.l1.size = 30
        self.l2.size = 30
        st = blockdevice.BlockDeviceStack(self.l0.path)
        with st:
            self.assertEquals(st.total_overhead, 20 + 0)
        self.l0.size = 50
        self.l1.size = 30
        self.l2.size = 20
        st = blockdevice.BlockDeviceStack(self.l0.path)
        with st:
            self.assertEquals(st.total_overhead, 20 + 10)

    def test_resize_up_granularity1_overhead0(self):
        self.l0.size = 100
        self.l1.size = 100
        self.l2.size = 100
        self.l0.granularity = 1
        self.l1.granularity = 1
        self.l2.granularity = 1
        st = blockdevice.BlockDeviceStack(self.l0.path)
        with st:
            self.assertItemsEqual(st.layer_and_data_sizes(), [100]*6)
            st.resize(200)
            self.assertItemsEqual(st.layer_and_data_sizes(), [200]*6)

    def test_resize_up_granularity5_overhead0(self):
        self.l0.size = 100
        self.l1.size = 100
        self.l2.size = 100
        self.l0.granularity = 5
        self.l1.granularity = 5
        self.l2.granularity = 5
        st = blockdevice.BlockDeviceStack(self.l0.path)
        with st:
            self.assertItemsEqual(st.layer_and_data_sizes(), [100]*6)
            st.resize(200)
            self.assertItemsEqual(st.layer_and_data_sizes(), [200]*6)

    def test_resize_up_granularitymix_overhead0(self):
        self.l0.size = 385
        self.l1.size = 385
        self.l2.size = 385
        self.l0.granularity = 5
        self.l1.granularity = 7
        self.l2.granularity = 11
        st = blockdevice.BlockDeviceStack(self.l0.path)
        with st:
            self.assertItemsEqual(st.layer_and_data_sizes(), [385]*6)
            st.resize(1000)
            self.assertItemsEqual(st.layer_and_data_sizes(), [1155]*6)

    def test_resize_up_granularity1_overhead1(self):
        self.l0.size = 100
        self.l1.size = 99
        self.l2.size = 98
        self.l0.granularity = 1
        self.l1.granularity = 1
        self.l2.granularity = 1
        st = blockdevice.BlockDeviceStack(self.l0.path)
        with st:
            self.assertEqual(list(st.layer_and_data_sizes()), [100, 100, 99, 99, 98, 98])
            st.resize(200)
            self.assertEqual(list(st.layer_and_data_sizes()), [200, 200, 199, 199, 198, 198])

    def test_resize_up_granularity1_overhead5(self):
        self.l0.size = 100
        self.l1.size = 95
        self.l2.size = 90
        self.l0.granularity = 1
        self.l1.granularity = 1
        self.l2.granularity = 1
        st = blockdevice.BlockDeviceStack(self.l0.path)
        with st:
            self.assertEqual(list(st.layer_and_data_sizes()), [100, 100, 95, 95, 90, 90])
            st.resize(200)
            self.assertEqual(list(st.layer_and_data_sizes()), [200, 200, 195, 195, 190, 190])

    def test_resize_up_granularitymix_overhead5(self):
        self.l0.size = 400
        self.l1.size = 395
        self.l2.size = 380
        self.l0.granularity = 2
        self.l1.granularity = 5
        self.l2.granularity = 20
        st = blockdevice.BlockDeviceStack(self.l0.path)
        with st:
            self.assertEqual(list(st.layer_and_data_sizes()), [400, 400, 395, 395, 380, 380])
            st.resize(1000)
            self.assertEqual(list(st.layer_and_data_sizes()), [1000, 1000, 995, 995, 980, 980])

    def test_resize_down_granularity1_overhead0(self):
        self.l0.size = 100
        self.l1.size = 100
        self.l2.size = 100
        self.l0.granularity = 1
        self.l1.granularity = 1
        self.l2.granularity = 1
        st = blockdevice.BlockDeviceStack(self.l0.path)
        with st:
            self.assertItemsEqual(st.layer_and_data_sizes(), [100]*6)
            st.resize(50)
            self.assertItemsEqual(st.layer_and_data_sizes(), [50]*6)

    def test_resize_down_granularity5_overhead0(self):
        self.l0.size = 100
        self.l1.size = 100
        self.l2.size = 100
        self.l0.granularity = 5
        self.l1.granularity = 5
        self.l2.granularity = 5
        st = blockdevice.BlockDeviceStack(self.l0.path)
        with st:
            self.assertItemsEqual(st.layer_and_data_sizes(), [100]*6)
            st.resize(50)
            self.assertItemsEqual(st.layer_and_data_sizes(), [50]*6)

    def test_resize_down_granularitymix_overhead0(self):
        self.l0.size = 1155
        self.l1.size = 1155
        self.l2.size = 1155
        self.l0.granularity = 5
        self.l1.granularity = 7
        self.l2.granularity = 11
        st = blockdevice.BlockDeviceStack(self.l0.path)
        with st:
            self.assertItemsEqual(st.layer_and_data_sizes(), [1155]*6)
            st.resize(100)
            self.assertItemsEqual(st.layer_and_data_sizes(), [385]*6)

    def test_resize_down_granularity1_overhead1(self):
        self.l0.size = 100
        self.l1.size = 99
        self.l2.size = 98
        self.l0.granularity = 1
        self.l1.granularity = 1
        self.l2.granularity = 1
        st = blockdevice.BlockDeviceStack(self.l0.path)
        with st:
            self.assertEqual(list(st.layer_and_data_sizes()), [100, 100, 99, 99, 98, 98])
            st.resize(50)
            self.assertEqual(list(st.layer_and_data_sizes()), [50, 50, 49, 49, 48, 48])

    def test_resize_down_granularity1_overhead5(self):
        self.l0.size = 100
        self.l1.size = 95
        self.l2.size = 90
        self.l0.granularity = 1
        self.l1.granularity = 1
        self.l2.granularity = 1
        st = blockdevice.BlockDeviceStack(self.l0.path)
        with st:
            self.assertEqual(list(st.layer_and_data_sizes()), [100, 100, 95, 95, 90, 90])
            st.resize(50)
            self.assertEqual(list(st.layer_and_data_sizes()), [50, 50, 45, 45, 40, 40])

    def test_resize_down_granularitymix_overhead5(self):
        self.l0.size = 400
        self.l1.size = 395
        self.l2.size = 380
        self.l0.granularity = 2
        self.l1.granularity = 5
        self.l2.granularity = 20
        st = blockdevice.BlockDeviceStack(self.l0.path)
        with st:
            self.assertEqual(list(st.layer_and_data_sizes()), [400, 400, 395, 395, 380, 380])
            st.resize(200)
            self.assertEqual(list(st.layer_and_data_sizes()), [200, 200, 195, 195, 180, 180])

    def test_layer_and_data_sizes(self):
        self.l0.size = 3
        self.l1.size = 2
        self.l2.size = 1
        st = blockdevice.BlockDeviceStack(self.l0.path)
        with st:
            sizes = st.layer_and_data_sizes()
            self.assertItemsEqual(sizes, [3, 3, 2, 2, 1, 1])


class ModuleTest(unittest.TestCase):
    def setUp(self):
        generic_setup(self)

    def tearDown(self):
        mock.patch.stopall()

    def test_lsblk(self):
        node = blockdevice.lsblk()
        self.assertEqual(len(node.children), 2)
        self.assertEqual(node.parent, None)
        self.assertEqual(node.children[0].parent, node)
        nodes = list(node.iterate())
        self.assertEqual(len(nodes), 15 + 1)

        node1 = node.find_node('vg01-something01')
        self.assertEqual(node1.name, 'vg01-something01')
        self.assertEqual(node1.major, 254)
        self.assertEqual(node1.minor, 16)
        self.assertEqual(node1.size, '2G')
        self.assertEqual(node1.type, 'lvm')
        self.assertEqual(node1.mountpoint, None)
        self.assertEqual(node1.ro, False)

        node2 = node.find_node('sdb1')
        self.assertEqual(node2.mountpoint, '/home')

    def test_devicemapper_info(self):
        with mock.patch('os.path.exists', new=lambda path: True):
            info = blockdevice.devicemapper_info('/dev/mapper/vg01-lv01')
            self.assertEqual(info['Major, minor'], '253, 3')
            self.assertEqual(info['Name'], 'vg01-lv01')
            self.assertEqual(info['UUID'], 'LVM-0bIWK7rs4OtKBT3YAk9qJpnSa19Yj4pbAR5j79MUV5HFIst4JF0McYNuq9avYXBC')
            self.assertEqual(info['Open count'], 1)

    def test_get_blockdevice_child(self):
        # uses LSBLK_DATA
        with mock.patch('os.path.exists', new=lambda path: True):
            child = blockdevice.get_blockdevice_child('dev/sda1')
            self.assertEqual(child, '/dev/mapper/md0')
            child = blockdevice.get_blockdevice_child('sda1')
            self.assertEqual(child, '/dev/mapper/md0')
            with self.assertRaises(Exception):
                blockdevice.get_blockdevice_child('xxxsda1')
            child = blockdevice.get_blockdevice_child('md0p2')
            self.assertEqual(child, '/dev/mapper/vg02-something03')

if __name__ == '__main__':
    unittest.main()
