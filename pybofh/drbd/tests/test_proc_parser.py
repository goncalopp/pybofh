import unittest
from StringIO import StringIO

from pybofh.drbd import proc_parser

PROC_83= '''version: 8.3.0 (api:88/proto:86-89)
GIT-hash: 9ba8b93e24d842f0dd3fb1f9b90e8348ddb95829 build by buildsystem@linbit, 2008-12-18 16:02:26
 0: cs:Connected ro:Primary/Secondary ds:UpToDate/UpToDate A r---
    ns:4716 nr:0 dw:164979224 dr:9365172 al:120 bm:23436 lo:5 pe:7 ua:11 ap:13 ep:19 wo:f oos:21
 1: cs:Connected ro:Secondary/Secondary ds:UpToDate/UpToDate C r---
    ns:0 nr:12 dw:12 dr:0 al:0 bm:1 lo:0 pe:0 ua:0 ap:0 ep:1 wo:b oos:0
 2: cs:Connected ro:Secondary/Secondary ds:UpToDate/UpToDate C r---
    ns:0 nr:0 dw:0 dr:0 al:0 bm:0 lo:0 pe:0 ua:0 ap:0 ep:1 wo:b oos:0
'''

PROC_84= '''version: 8.4.3 (api:1/proto:86-101)
srcversion: 1A9F77B1CA5FF92235C2213 
 0: cs:Connected ro:Primary/Secondary ds:UpToDate/UpToDate A r-----
    ns:4716 nr:0 dw:164979224 dr:9365172 al:120 bm:23436 lo:5 pe:7 ua:11 ap:13 ep:19 wo:f oos:21
 1: cs:Connected ro:Primary/Secondary ds:UpToDate/UpToDate A r-----
    ns:592 nr:0 dw:4741300 dr:3358549 al:101 bm:350 lo:0 pe:0 ua:0 ap:0 ep:1 wo:f oos:0
 2: cs:Connected ro:Primary/Secondary ds:UpToDate/UpToDate A r-----
    ns:7752 nr:0 dw:8046176 dr:10296191 al:490 bm:1174 lo:0 pe:0 ua:0 ap:0 ep:1 wo:f oos:0
 3: cs:Connected ro:Primary/Secondary ds:UpToDate/UpToDate A r-----
    ns:804 nr:0 dw:17367120 dr:6853072 al:366 bm:847 lo:0 pe:0 ua:0 ap:0 ep:1 wo:f oos:0
'''


class ProcParserTest(unittest.TestCase):
    def test_83(self):
        data= PROC_83
        version, resources= proc_parser.parse_proc_drbd(StringIO(data))
        self.assertEqual(version, "8.3.0")
        self.assertEqual(len(resources), 3)
        self.assertEqual(resources[0][1], []) # parser assigns rp and iof to tuples
        d = resources[0][0]
        self.assertEqual(d['cs'], 'Connected')
        self.assertEqual(d['ro'], 'Primary/Secondary')
        self.assertEqual(d['ds'], 'UpToDate/UpToDate')
        self.assertEqual(d['rp'], 'A')
        self.assertEqual(d['iof'], 'r---')
        self.assertEqual(d['ns'], 4716)
        self.assertEqual(d['nr'], 0)
        self.assertEqual(d['dw'], 164979224)
        self.assertEqual(d['dr'], 9365172)
        self.assertEqual(d['al'], 120)
        self.assertEqual(d['bm'], 23436)
        self.assertEqual(d['lo'], 5)
        self.assertEqual(d['pe'], 7)
        self.assertEqual(d['ua'], 11)
        self.assertEqual(d['ap'], 13)
        self.assertEqual(d['ep'], 19)
        self.assertEqual(d['wo'], 'f')
        self.assertEqual(d['oos'], 21)

    def test_84(self):
        data= PROC_84
        version, resources= proc_parser.parse_proc_drbd(StringIO(data))
        self.assertEqual(version, "8.4.3")
        self.assertEqual(len(resources), 4)
        self.assertEqual(resources[0][1], []) # parser assigns rp and iof to tuples
        d = resources[0][0]
        self.assertEqual(d['cs'], 'Connected')
        self.assertEqual(d['ro'], 'Primary/Secondary')
        self.assertEqual(d['ds'], 'UpToDate/UpToDate')
        self.assertEqual(d['rp'], 'A')
        self.assertEqual(d['iof'], 'r-----')
        self.assertEqual(d['ns'], 4716)
        self.assertEqual(d['nr'], 0)
        self.assertEqual(d['dw'], 164979224)
        self.assertEqual(d['dr'], 9365172)
        self.assertEqual(d['al'], 120)
        self.assertEqual(d['bm'], 23436)
        self.assertEqual(d['lo'], 5)
        self.assertEqual(d['pe'], 7)
        self.assertEqual(d['ua'], 11)
        self.assertEqual(d['ap'], 13)
        self.assertEqual(d['ep'], 19)
        self.assertEqual(d['wo'], 'f')
        self.assertEqual(d['oos'], 21)


if __name__ == '__main__':
    unittest.main()
