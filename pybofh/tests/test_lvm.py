'''Tests for mount.py'''
# pylint: disable=no-member
# pylint: disable=no-self-use

import unittest
import mock
from pybofh import lvm
from pybofh import shell

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

def generic_setup():
    '''Setups mocks'''
    mocklist = [
        {"target": "os.path.isdir"},
        {"target": "os.path.exists"},
        {"target": "pybofh.shell.run_process", "side_effect": command_side_effect},
        {"target": "pybofh.blockdevice.BlockDevice"},
        {"target": "pybofh.blockdevice.Data"},
        ]
    patches = [mock.patch(autospec=True, **a) for a in mocklist]
    for patch in patches:
        patch.start()

class PVTest(unittest.TestCase):
    def setUp(self):
        generic_setup()

    def tearDown(self):
        mock.patch.stopall()

    def test_init(self):
        pv = lvm.PV(PV)
        self.assertIsInstance(pv, lvm.PV)

    def test_create(self):
        pv = lvm.PV(PV)
        pv.device.path = PV # manual mock
        pv.create()
        shell.run_process.assert_has_calls([mock.call(('/sbin/pvcreate', "-f", PV))])

    def test_create_vg(self):
        pv = lvm.PV(PV)
        pv.device.path = PV # manual mock
        vg = pv.create_vg(VG)
        shell.run_process.assert_has_calls([mock.call(('/sbin/vgcreate', VG, PV))])
        self.assertIsInstance(vg, lvm.VG)
        self.assertEqual(vg.name, VG)

    def test_remove(self):
        pv = lvm.PV(PV)
        pv.device.path = PV # manual mock
        pv.remove()
        shell.run_process.assert_has_calls([mock.call(('/sbin/pvremove', PV))])

class VGTest(unittest.TestCase):
    def setUp(self):
        generic_setup()

    def tearDown(self):
        mock.patch.stopall()

    def test_get_lvs(self):
        vg = lvm.VG(VG)
        lvs = vg.get_lvs()
        shell.run_process.assert_called_with('/sbin/lvdisplay')
        self.assertEqual(len(lvs), 1)
        self.assertIsInstance(lvs[0], lvm.LV)
        self.assertEqual(lvs[0].name, LV)

    def test_create_lv(self):
        vg = lvm.VG(VG)
        lv = vg.create_lv(LV, size="1G")
        shell.run_process.assert_has_calls([mock.call(('/sbin/lvcreate', VG, '--name', LV, '--size', '1G'))])
        self.assertIsInstance(lv, lvm.LV)
        self.assertEqual(lv.name, LV)

    def test_lv(self):
        vg = lvm.VG(VG)
        lv = vg.lv(LV)
        shell.run_process.assert_has_calls([mock.call('/sbin/lvdisplay')])
        self.assertIsInstance(lv, lvm.LV)
        self.assertEqual(lv.name, LV)

    def test_remove(self):
        vg = lvm.VG(VG)
        vg.remove()
        shell.run_process.assert_has_calls([mock.call(('/sbin/vgremove', VG))])

class LVTest(unittest.TestCase):
    def setUp(self):
        generic_setup()

    def tearDown(self):
        mock.patch.stopall()

    def test_init(self):
        lv = lvm.LV(VG, LV)
        shell.run_process.assert_has_calls([mock.call('/sbin/lvdisplay')])
        self.assertIsInstance(lv, lvm.LV)
        self.assertEqual(lv.name, LV)

    def test_remove(self):
        lv = lvm.LV(VG, LV)
        lv.remove()
        shell.run_process.assert_has_calls([mock.call(('/sbin/lvremove', '-f', VG + '/' + LV))])

    def test_resize(self):
        pass # TODO
        #lv = lvm.LV(VG, LV)
        #lv.resize(100 * 2**20, no_data=True)
        #shell.run_process.assert_has_calls([mock.call(('/sbin/lvresize', '-f', VG + '/' + LV))])

    def test_rename(self):
        lv = lvm.LV(VG, LV)
        lv.rename('newname')
        shell.run_process.assert_has_calls([mock.call(('/sbin/lvrename', VG, LV, 'newname'))])

class ModuleFunctionsTest(unittest.TestCase):
    def setUp(self):
        generic_setup()

    def tearDown(self):
        mock.patch.stopall()

    def test_get_vgs(self):
        vgs = lvm.get_vgs()
        shell.run_process.assert_called_once_with('/sbin/vgdisplay')
        self.assertEqual(len(vgs), 1)
        self.assertItemsEqual(vgs, [VG])

    def test_get_lvs(self):
        lvs = lvm.get_lvs(VG)
        shell.run_process.assert_called_once_with('/sbin/lvdisplay')
        self.assertEqual(len(lvs), 1)
        self.assertItemsEqual(lvs, [LV])

    def test_create_lv(self):
        lvm.create_lv(VG, LV, '1G')
        shell.run_process.assert_called_once_with(('/sbin/lvcreate', VG, '--name', LV, '--size', '1G'))

    def test_remove_lv(self):
        lvm.remove_lv(VG, LV)
        shell.run_process.assert_called_once_with(('/sbin/lvremove', "-f", VG + "/" + LV))

    def test_rename_lv(self):
        lvm.rename_lv(VG, LV, "lvnewname")
        shell.run_process.assert_called_once_with(('/sbin/lvrename', VG, LV, "lvnewname"))

    def test_create_pv(self):
        lvm.create_pv(PV)
        shell.run_process.assert_called_once_with(('/sbin/pvcreate', "-f", PV))

    def test_create_vg(self):
        lvm.create_vg(VG, PV)
        shell.run_process.assert_called_once_with(('/sbin/vgcreate', VG, PV))

    def test_remove_vg(self):
        lvm.remove_vg(VG)
        shell.run_process.assert_called_once_with(('/sbin/vgremove', VG))

    def test_remove_pv(self):
        lvm.remove_pv(PV)
        shell.run_process.assert_called_once_with(('/sbin/pvremove', PV))

if __name__ == "__main__":
    unittest.main()
