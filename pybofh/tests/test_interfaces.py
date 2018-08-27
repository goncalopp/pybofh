"""Tests for interfaces.py"""
import unittest
import mock

from pybofh import interfaces
from pybofh.tests import common

IFCONFIG_DATA = """enp0s92a1: flags=4099<UP,BROADCAST,MULTICAST>  mtu 1500
        ether 12:34:56:78:76:54  txqueuelen 1000  (Ethernet)
        RX packets 0123  bytes 0234 (0.0 B)
        RX errors 0345  dropped 0456  overruns 0  frame 0
        TX packets 0567  bytes 0678 (0.0 B)
        TX errors 0789  dropped 0 overruns 0  carrier 0  collisions 0
        device interrupt 16  memory 0xec300000-ec320000  

lo: flags=73<UP,LOOPBACK,RUNNING>  mtu 65536
        inet 127.0.0.1  netmask 255.0.0.0
        inet6 ::1  prefixlen 128  scopeid 0x10<host>
        loop  txqueuelen 1  (Local Loopback)
        RX packets 311412  bytes 5167687959 (4.8 GiB)
        RX errors 0  dropped 0  overruns 0  frame 0
        TX packets 311412  bytes 5167687959 (4.8 GiB)
        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0

wlp1s3: flags=4099<UP,BROADCAST,MULTICAST>  mtu 1500
        ether aa:aa:aa:aa:aa:aa  txqueuelen 1000  (Ethernet)
        RX packets 4513  bytes 1008514 (984.8 KiB)
        RX errors 0  dropped 0  overruns 0  frame 0
        TX packets 6426  bytes 980308 (957.3 KiB)
        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0

"""

class FakeEnvironment(common.FakeEnvironment):
    def __init__(self):
        common.FakeEnvironment.__init__(self)
        self.shell.add_fake(('/sbin/ifconfig', '-a'), IFCONFIG_DATA)

def generic_setup(test_instance):
    """Setups mocks"""
    env = FakeEnvironment()
    test_instance.env = env
    mocklist = [
        {"target": "pybofh.shell.get", "side_effect": lambda: env.shell},
        ]
    patches = [mock.patch(autospec=True, **a) for a in mocklist]
    for patch in patches:
        patch.start()


class ModuleTest(unittest.TestCase):
    def setUp(self):
        generic_setup(self)

    def tearDown(self):
        mock.patch.stopall()

    def test_ifconfig(self):
        itfs = interfaces.ifconfig()
        self.assertEqual(len(itfs), 3)
        # --------
        self.assertIsInstance(itfs[0], interfaces.IfconfigEntry)
        self.assertEqual(itfs[0].name, "enp0s92a1")
        self.assertEqual(itfs[0].mtu, 1500)
        self.assertEqual(itfs[0].rx_packets, 123)
        self.assertEqual(itfs[0].rx_errors, 345)
        self.assertEqual(itfs[0].tx_packets, 567)
        self.assertEqual(itfs[0].tx_errors, 789)
        self.assertEqual(itfs[0].mac, "12:34:56:78:76:54")
        self.assertEqual(itfs[0].ipv4, None)
        self.assertEqual(itfs[0].netmask, None)
        self.assertEqual(itfs[0].ipv6, None)
        # --------
        self.assertIsInstance(itfs[1], interfaces.IfconfigEntry)
        self.assertEqual(itfs[1].name, "lo")
        self.assertEqual(itfs[1].mtu, 65536)
        self.assertEqual(itfs[1].rx_packets, 311412)
        self.assertEqual(itfs[1].rx_errors, 0)
        self.assertEqual(itfs[1].tx_packets, 311412)
        self.assertEqual(itfs[1].tx_errors, 0)
        self.assertEqual(itfs[1].mac, None)
        self.assertEqual(itfs[1].ipv4, "127.0.0.1")
        self.assertEqual(itfs[1].netmask, "255.0.0.0")
        self.assertEqual(itfs[1].ipv6, "::1")
        # --------
        self.assertIsInstance(itfs[2], interfaces.IfconfigEntry)
        self.assertEqual(itfs[2].name, "wlp1s3")
        self.assertEqual(itfs[2].mtu, 1500)
        self.assertEqual(itfs[2].rx_packets, 4513)
        self.assertEqual(itfs[2].rx_errors, 0)
        self.assertEqual(itfs[2].tx_packets, 6426)
        self.assertEqual(itfs[2].tx_errors, 0)
        self.assertEqual(itfs[2].mac, "aa:aa:aa:aa:aa:aa")
        self.assertEqual(itfs[2].ipv4, None)
        self.assertEqual(itfs[2].netmask, None)
        self.assertEqual(itfs[2].ipv6, None)



class InterfaceTest(unittest.TestCase):
    def setUp(self):
        generic_setup(self)

    def tearDown(self):
        mock.patch.stopall()

    def test_init(self):
        itf = interfaces.Interface("lo")
        self.assertIsInstance(itf, interfaces.Interface)

    def test_init_inexistent(self):
        with self.assertRaises(interfaces.InexistentInterfaceError):
            interfaces.Interface("inexistent")

    def test_init_inexistent_nocheck(self):
        itf = interfaces.Interface("inexistent", check_existence=False)
        self.assertIsInstance(itf, interfaces.Interface)

    def test_mac(self):
        itf = interfaces.Interface("enp0s92a1")
        self.assertEqual(itf.data.mac, "12:34:56:78:76:54")
