import unittest
import mock
import pybofh
from pybofh.drbd import misc

SLASH_DEV_CONTENTS = [
 'dm-19',
 'drbd0',
 'drbd1',
 'drbd2',
 'drbd_somename',
 'drbd_othername123',
 'drbd',
 'log',
 'sda'
]

RESOURCE_CONFIG_FILE_CONTENTS1 = """resource myresource1 {
  device    /dev/drbd_res1 minor 13;
  meta-disk internal;
  on host1 {
    address   127.0.0.1:1234;
    disk      /dev/sda;
  }
  on host2 {
    address   192.168.1.1:1234;
    disk      /dev/sdb;
  }
}
"""

RESOURCE_CONFIG_FILE_CONTENTS2 = """resource myresource2 {
  device    /dev/drbd_res2 minor 14;
  meta-disk internal;
  on host1 {
    address   127.0.0.1:1235;
    disk      /dev/sdc;
  }
  on host2 {
    address   192.168.1.1:1235;
    disk      /dev/sdd;
  }
}
"""
 
class ModuleTest(unittest.TestCase):
    def setUp(self):
        def mock_listdir(path):
            if path == "/etc/drbd.d": # default config dir
                return ["a", "a.res", "b.res", "c.cfg", "d.txt"]
            raise NotImplementedError("mock_listdir for path {}".format(path))
        def mock_read_file(path):
            return {
                "/etc/drbd.d/a.res": RESOURCE_CONFIG_FILE_CONTENTS1,
                "/etc/drbd.d/b.res": RESOURCE_CONFIG_FILE_CONTENTS2,
            }[path]
        mock.patch("pybofh.misc.list_dir", new=mock_listdir).start()
        mock.patch("pybofh.misc.read_file", new=mock_read_file).start()

    def tearDown(self):
        mock.patch.stopall()

    def test_devices_list(self):
        with mock.patch("pybofh.misc.list_dir", new=lambda path: SLASH_DEV_CONTENTS):
            l = misc.devices_list()
            self.assertEqual(l, ["/dev/drbd_somename", "/dev/drbd_othername123"])
            l = misc.devices_list(named=False)
            self.assertEqual(l, ["/dev/drbd0", "/dev/drbd1", "/dev/drbd2"])
            l = misc.devices_list(absolute_paths=False)
            self.assertEqual(l, ["drbd_somename", "drbd_othername123"])
            l = misc.devices_list(named=False, absolute_paths=False)
            self.assertEqual(l, ["drbd0", "drbd1", "drbd2"])
            l = misc.devices_list(absolute_paths=False, include_prefix=False)
            self.assertEqual(l, ["somename", "othername123"])
            l = misc.devices_list(named=False, absolute_paths=False, include_prefix=False)
            self.assertEqual(l, ["0", "1", "2"])

    def test_config_files(self):
        self.assertEqual(misc.config_files(), ["/etc/drbd.d/a.res", "/etc/drbd.d/b.res"])

    def test_config_addresses(self):
        addrs = misc.config_addresses("/etc/drbd.d/a.res")
        self.assertEqual(addrs, ['127.0.0.1:1234', '192.168.1.1:1234'])

    def test_config_minor(self):
        minor = misc.config_minor("/etc/drbd.d/a.res")
        self.assertEqual(minor, 13)

    def test_highest_port(self):
        self.assertEqual(misc.highest_port(), 1235)

    def test_highest_minor(self):
        self.assertEqual(misc.highest_minor(), 14)

    def test_resources_list(self):
        self.assertEqual(misc.resources_list(), ["myresource1", "myresource2"])

    def test_metadata_size(self):
        self.assertEqual(misc.metadata_size(0), 2**20)
        self.assertEqual(misc.metadata_size(10), 2**20)
        self.assertEqual(misc.metadata_size(5 * 2**30), 2**20)
        self.assertEqual(misc.metadata_size(33 * 2**30), 2 * 2**20)
        # TODO: verify this






if __name__ == "__main__":
    unittest.main()
