'''Tests for mount.py'''
# pylint: disable=no-member
# pylint: disable=no-self-use

import unittest
import mock
import functools
from pybofh.shell import MockShell
from pybofh import blockdevice

# Aux classes for testing -------------------------------------------

class MockDevice(object):
    def __init__(self, path, content, parent=None, size=10*2**20, granularity=1):
        self.path = path
        self.content = content
        self.size = size
        self.granularity = granularity
        self.child = None
        self.parent = parent
        if parent:
            parent.child = self

    def mock_shell_match(self, command):
        """Whether this MockDevice should execute the mocked command - used in MockShell"""
        return self.path in command

    def mock_shell_execute(self, command):
        """Implementation of command execution for MockShell"""
        if command == ('/sbin/blockdev', '--getsize64', self.path):
            return str(self.size)
        if command == ('file', '--special', '--dereference', self.path):
            name = self.content.__name__ if callable(self.content) else self.content.__class__.__name__
            return "{}: some data: {}".format(self.path, name)
        raise Exception("Unhandled mock command: " + command)

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
    def __init__(self, path_or_mock_device):
        self.mockdevice = path_or_mock_device if isinstance(path_or_mock_device, MockDevice) else None
        path = self.mockdevice.path if self.mockdevice else path_or_mock_device
        blockdevice.BlockDevice.__init__(self, path)

    @property
    def resize_granularity(self):
        if self.mockdevice:
            return self.mockdevice.granularity
        else:
            return blockdevice.BlockDevice.resize_granularity(self)

    def _resize(self, byte_size, minimum, maximum, interactive, **kwargs):
        if self.mockdevice:
            if minimum or maximum:
                raise NotImplementedError
            self.mockdevice.size = byte_size
        else:
            return blockdevice.BlockDevice._resize(self)

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

    def _resize(self, byte_size, minimum, maximum, interactive, **kwargs):
        self._simple_size = byte_size

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
            self.inner.mockdevice.size = new_size
        elif self.resize_overhead == 'constant':
            overhead = old_size - self.inner.mockdevice.size
            self.inner.mockdevice.size = new_size - overhead
        else:
            raise Exception("SimpleOuterLayer has invalid resize_overhead: " + seld.resize_overhead)


    @property
    def resize_granularity(self):
        return 1

    def _size(self):
        return self._simple_size


class SimpleInnerLayer(blockdevice.InnerLayer):
    def __init__(self, outer_layer, **kwargs):
        blockdevice.InnerLayer.__init__(self, outer_layer, **kwargs)
        self._simple_size = outer_layer.size
        obd = outer_layer.device
        self.mockdevice = outer_layer.device.mockdevice.child

    def _close(self):
        pass

    def _open(self, **kwargs):
        return self.mockdevice.path

    def _resize(self, byte_size, minimum, maximum, interactive, **kwargs):
        raise NotImplementedError

    @property
    def resize_granularity(self):
        return self.mockdevice.granularity

    def _size(self):
        return self.mockdevice.size
    
# Module level constants / vars / code  --------------------------------------
 
blockdevice.register_data_class('SimpleData', SimpleData)
blockdevice.register_data_class('SimpleOuterLayer', SimpleOuterLayer)

def create_mock_shell(mock_devices):
    shell = MockShell()
    for md in mock_devices:
        shell.add_mock(md.mock_shell_match, md.mock_shell_execute)
    return shell

def get_dev_from_path(path, mock_devices):
    for md in mock_devices:
        if md.path == path:
            return SimpleBlockDevice(md)
    return SimpleBlockDevice(path)

def generic_setup(test_instance, mock_devices=()):
    '''Setups mocks'''
    shell = create_mock_shell(mock_devices)
    test_instance.shell = shell
    mocklist = [
        {"target": "os.path.isdir"},
        {"target": "os.path.exists"},
        {"target": "pybofh.blockdevice.blockdevice_from_path", "side_effect": lambda path: SimpleBlockDevice(path)},
        {"target": "pybofh.shell.get", "side_effect": lambda: shell},
        ]
    patches = [mock.patch(autospec=True, **a) for a in mocklist] + \
        [mock.patch('pybofh.blockdevice.blockdevice_from_path', new_callable=lambda : functools.partial(get_dev_from_path, mock_devices=mock_devices))]
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
        r._on_open.assert_called_with('xyz',True) # a true open
        # open when externally open
        r = SimpleOpenable(externally_open_data='xyz')
        r._on_open = mock.Mock(r._on_open)
        self.assertTrue(r.is_externally_open)
        self.assertFalse(r.is_open) # Externally open doesn't count as open
        r.open()
        r._on_open.assert_called_with('xyz',False) # a fake open
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
        self.bd = MockDevice('/dev/inexistent', SimpleData)
        generic_setup(self, (self.bd,))

    def tearDown(self):
        mock.patch.stopall()

    def test_init(self):
        b = blockdevice.BlockDevice(self.bd.path)
        self.assertIsInstance(b, blockdevice.BlockDevice)

    def test_size(self):
        b = blockdevice.BlockDevice(self.bd.path)
        self.assertEquals(b.size, self.bd.size)
        self.assertEquals(self.shell.run_commands[-1], ('/sbin/blockdev', '--getsize64', self.bd.path))

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
        self.assertIn(('file', '--special', '--dereference', self.bd.path), self.shell.run_commands)
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
        self.assertEqual(len(self.shell.run_commands), 0)
        with self.assertRaises(NotImplementedError):
            # resize is not implemented for base BlockDevice
            b.resize(-100, relative=True, no_data=True)

class OuterLayerTest(unittest.TestCase):
    def setUp(self):
        self.l0 = MockDevice('/dev/inexistent_l0', SimpleOuterLayer)
        self.l1 = MockDevice('/dev/inexistent_l1', SimpleData, parent=self.l0)
        generic_setup(self, (self.l0,))

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
        self.l0 = MockDevice('/dev/inexistent_l0', SimpleOuterLayer)
        self.l1 = MockDevice('/dev/inexistent_l1', SimpleData, parent=self.l0)
        generic_setup(self, (self.l0,))

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
        ol = blockdevice.blockdevice(self.l0.path)
        inner = ol.data.inner
        patch = mock.patch('pybofh.blockdevice.InnerLayer._externally_open_data', return_value=None).start()
        self.assertFalse(inner.is_externally_open)
        patch.stop()
        patch = mock.patch('pybofh.blockdevice.InnerLayer._externally_open_data', return_value="something").start()
        self.assertTrue(inner.is_externally_open)

class BlockDeviceStackTest(unittest.TestCase):
    def setUp(self):
        self.l0 = MockDevice('/dev/inexistent_l0', SimpleOuterLayer)
        self.l1 = MockDevice('/dev/inexistent_l1', SimpleOuterLayer, parent=self.l0)
        self.l2 = MockDevice('/dev/inexistent_l2', SimpleData, parent=self.l1)
        devices = [self.l2, self.l1, self.l0]
        device_dict = {d.path: d for d in devices}
        generic_setup(self, (self.l0, self.l1, self.l2))
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
        self.l1.granularit = 5
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
        self.l1.granularit = 1
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




    def test_layer_and_data_sizes(self):
        self.l0.size = 3
        self.l1.size = 2
        self.l2.size = 1
        st = blockdevice.BlockDeviceStack(self.l0.path)
        with st:
            sizes = st.layer_and_data_sizes()
            self.assertItemsEqual(sizes, [3,3,2,2,1,1])
        

if __name__ == "__main__":
    unittest.main()