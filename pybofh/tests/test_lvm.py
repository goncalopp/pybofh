'''Tests for mount.py'''
# pylint: disable=no-member
# pylint: disable=no-self-use

import unittest
import mock
from pybofh import lvm
from pybofh.shell import FakeShell

PV = '/dev/in1'
VG = 'in_vg'
LV = 'in_lv'

PVDISPLAY_DATA = '''  --- Physical volume ---
  PV Name               /dev/in1
  VG Name               in_vg
  PV Size               2.79 GiB / not usable 4.00 MiB
  Allocatable           yes (but full)
  PE Size               4.00 MiB
  Total PE              714
  Free PE               0
  Allocated PE          714
  PV UUID               EvbqlT-AUsZ-MfKi-ZSOz-Lh6L-Y3xC-KiLcYx
   
'''

VGDISPLAY_DATA = '''  --- Volume group ---
  VG Name               in_vg
  System ID             
  Format                lvm2
  Metadata Areas        2
  Metadata Sequence No  13
  VG Access             read/write
  VG Status             resizable
  MAX LV                0
  Cur LV                1
  Open LV               0
  Max PV                0
  Cur PV                1
  Act PV                1
  VG Size               107.88 GiB
  PE Size               4.00 MiB
  Total PE              27616
  Alloc PE / Size       25318 / 98.90 GiB
  Free  PE / Size       2298 / 8.98 GiB
  VG UUID               jWIQCX-uxUT-aG1x-1tpc-1Ixk-pxw2-gL6mlJ

'''

LVDISPLAY_DATA = '''  --- Logical volume ---
  LV Path                /dev/in_vg/in_lv
  LV Name                in_lv
  VG Name                in_vg
  LV UUID                wgA7Jd-cve5-eK2K-OcUk-yZ43-vvbw-diT892
  LV Write Access        read/write
  LV Creation host, time hostname, 2011-11-19 11:28:13 +0000
  LV Status              available
  # open                 1
  LV Size                14.90 GiB
  Current LE             3814
  Segments               1
  Allocation             inherit
  Read ahead sectors     auto
  - currently set to     256
  Block device           253:1
   
'''

def command_side_effect(command):
    if command == '/sbin/vgdisplay':
        return VGDISPLAY_DATA
    if command == '/sbin/lvdisplay':
        return LVDISPLAY_DATA
    return mock.DEFAULT

def generic_setup(test_instance):
    '''Setups mocks'''
    test_instance.shell = shell = FakeShell()
    shell.add_fake('/sbin/vgdisplay', VGDISPLAY_DATA)
    shell.add_fake('/sbin/lvdisplay', LVDISPLAY_DATA)
    shell.add_fake(lambda _: True, mock.DEFAULT) # catch-all
    mocklist = [
        {"target": "os.path.isdir"},
        {"target": "os.path.exists"},
        {"target": "pybofh.shell.get", "side_effect": lambda: shell},
        {"target": "pybofh.blockdevice.BlockDevice"},
        {"target": "pybofh.blockdevice.Data"},
        ]
    patches = [mock.patch(autospec=True, **a) for a in mocklist]
    for patch in patches:
        patch.start()

class PVTest(unittest.TestCase):
    def setUp(self):
        generic_setup(self)

    def tearDown(self):
        mock.patch.stopall()

    def test_init(self):
        pv = lvm.PV(PV)
        self.assertIsInstance(pv, lvm.PV)

    def test_create(self):
        pv = lvm.PV(PV)
        pv.device.path = PV # manual mock
        pv.create()
        self.assertIn(('/sbin/pvcreate', "-f", PV), self.shell.run_commands)

    def test_create_vg(self):
        pv = lvm.PV(PV)
        pv.device.path = PV # manual mock
        vg = pv.create_vg(VG)
        self.assertIn(('/sbin/vgcreate', VG, PV), self.shell.run_commands)
        self.assertIsInstance(vg, lvm.VG)
        self.assertEqual(vg.name, VG)

    def test_remove(self):
        pv = lvm.PV(PV)
        pv.device.path = PV # manual mock
        pv.remove()
        self.assertIn(('/sbin/pvremove', PV), self.shell.run_commands)

class VGTest(unittest.TestCase):
    def setUp(self):
        generic_setup(self)

    def tearDown(self):
        mock.patch.stopall()

    def test_get_lvs(self):
        vg = lvm.VG(VG)
        lvs = vg.get_lvs()
        self.assertIn(('/sbin/lvdisplay',), self.shell.run_commands)
        self.assertEqual(len(lvs), 1)
        self.assertIsInstance(lvs[0], lvm.LV)
        self.assertEqual(lvs[0].name, LV)

    def test_create_lv(self):
        vg = lvm.VG(VG)
        lv = vg.create_lv(LV, size="1G")
        self.assertIn(('/sbin/lvcreate', VG, '--name', LV, '--size', '1G'), self.shell.run_commands)
        self.assertIsInstance(lv, lvm.LV)
        self.assertEqual(lv.name, LV)

    def test_lv(self):
        vg = lvm.VG(VG)
        lv = vg.lv(LV)
        self.assertIn(('/sbin/lvdisplay',), self.shell.run_commands)
        self.assertIsInstance(lv, lvm.LV)
        self.assertEqual(lv.name, LV)

    def test_remove(self):
        vg = lvm.VG(VG)
        vg.remove()
        self.assertIn((('/sbin/vgremove', VG)), self.shell.run_commands)

class LVTest(unittest.TestCase):
    def setUp(self):
        generic_setup(self)

    def tearDown(self):
        mock.patch.stopall()

    def test_init(self):
        lv = lvm.LV(VG, LV)
        self.assertIn(('/sbin/lvdisplay',), self.shell.run_commands)
        self.assertIsInstance(lv, lvm.LV)
        self.assertEqual(lv.name, LV)

    def test_remove(self):
        lv = lvm.LV(VG, LV)
        lv.remove()
        self.assertIn((('/sbin/lvremove', '-f', VG + '/' + LV)), self.shell.run_commands)

    def test_resize(self):
        pass # TODO
        #lv = lvm.LV(VG, LV)
        #lv.resize(100 * 2**20, no_data=True)
        #self.assertIn((('/sbin/lvresize', '-f', VG + '/' + LV)), self.shell.run_commands)

    def test_rename(self):
        lv = lvm.LV(VG, LV)
        lv.rename('newname')
        self.assertIn((('/sbin/lvrename', VG, LV, 'newname')), self.shell.run_commands)

class ModuleFunctionsTest(unittest.TestCase):
    def setUp(self):
        generic_setup(self)

    def tearDown(self):
        mock.patch.stopall()

    def test_get_vgs(self):
        vgs = lvm.get_vgs()
        self.assertIn(('/sbin/vgdisplay',), self.shell.run_commands)
        self.assertEqual(len(vgs), 1)
        self.assertItemsEqual(vgs, [VG])

    def test_get_lvs(self):
        lvs = lvm.get_lvs(VG)
        self.assertIn(('/sbin/lvdisplay',), self.shell.run_commands)
        self.assertEqual(len(lvs), 1)
        self.assertItemsEqual(lvs, [LV])

    def test_create_lv(self):
        lvm.create_lv(VG, LV, '1G')
        self.assertIn((('/sbin/lvcreate', VG, '--name', LV, '--size', '1G')), self.shell.run_commands)

    def test_remove_lv(self):
        lvm.remove_lv(VG, LV)
        self.assertIn((('/sbin/lvremove', "-f", VG + "/" + LV)), self.shell.run_commands)

    def test_rename_lv(self):
        lvm.rename_lv(VG, LV, "lvnewname")
        self.assertIn((('/sbin/lvrename', VG, LV, "lvnewname")), self.shell.run_commands)

    def test_create_pv(self):
        lvm.create_pv(PV)
        self.assertIn((('/sbin/pvcreate', "-f", PV)), self.shell.run_commands)

    def test_create_vg(self):
        lvm.create_vg(VG, PV)
        self.assertIn((('/sbin/vgcreate', VG, PV)), self.shell.run_commands)

    def test_remove_vg(self):
        lvm.remove_vg(VG)
        self.assertIn((('/sbin/vgremove', VG)), self.shell.run_commands)

    def test_remove_pv(self):
        lvm.remove_pv(PV)
        self.assertIn((('/sbin/pvremove', PV)), self.shell.run_commands)

if __name__ == "__main__":
    unittest.main()
