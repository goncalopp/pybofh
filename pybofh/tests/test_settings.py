'''Tests for settings.py'''

import unittest
from pybofh.settings import Settings, GlobalSettings, GlobalSettingsMutation, PrefixedSettings, DuplicateError

class SettingsTest(unittest.TestCase):
    def test_update_values(self):
        all_keys = ['a', 'b', 'c', 'd']
        s = Settings({'a': None, 'b': 1, 'c': None, 'd': 2})
        # Invalid keys
        with self.assertRaises(KeyError):
            Settings.update_values(s, {'e':None})
        with self.assertRaises(KeyError):
            Settings.update_values(s, {'a':None, 'e':None})
        # Update
        s2 = Settings.update_values(s, {'c': 9, 'd': 8})
        self.assertEqual([s2.get(k) for k in all_keys], [None, 1, 9, 8])
        self.assertEqual([s.get(k) for k in all_keys], [None, 1, None, 2])

    def test_get(self):
        s = Settings({'a': 1})
        self.assertEqual(s.get('a'), 1)
        self.assertEqual(s['a'], 1)
        with self.assertRaises(KeyError):
            s.get('b')
        with self.assertRaises(KeyError):
            _ = s['b']

    def test_get_description(self):
        s = Settings({'a': 1, 'b':2, 'c':3}, descs={'a': 'desc', 'b':None})
        self.assertEqual(s.get_description('a'), 'desc')
        self.assertEqual(s.get_description('b'), None)
        self.assertEqual(s.get_description('c'), '')
        with self.assertRaises(KeyError):
            s.get_description('d')

    def test_enforce_defined(self):
        s = Settings({'a': None, 'b': 1, 'c': None, 'd': 2})
        with self.assertRaises(KeyError):
            s.enforce_defined(['e'])
        with self.assertRaises(KeyError):
            s.enforce_defined(['a', 'b', 'c', 'e', 'd'])
        s.enforce_defined(set(['a', 'b', 'c', 'd']))
        s.enforce_defined({'a': None, 'b': None, 'c': None, 'd': None})

    def test_for(self):
        self.assertIsInstance(Settings().for_('prefix'), PrefixedSettings)

    def test_define(self):
        s = Settings({'a': 1, 'b':2}, descs={'a': 'desc'})
        with self.assertRaises(DuplicateError):
            s.define('a')
        with self.assertRaises(DuplicateError):
            s.define('b')
        with self.assertRaises(KeyError):
            s.get('c')
        # No description, no default
        s.define('c')
        self.assertEqual(s.get('c'), None)
        self.assertEqual(s.get_description('c'), '')
        with self.assertRaises(DuplicateError):
            s.define('c')
        # Description, no default
        s.define('d', 'desc')
        self.assertEqual(s.get('d'), None)
        self.assertEqual(s.get_description('d'), 'desc')
        with self.assertRaises(DuplicateError):
            s.define('d')
        # Description, default
        s.define('e', 'desc', 1)
        self.assertEqual(s.get('e'), 1)
        self.assertEqual(s.get_description('e'), 'desc')
        with self.assertRaises(DuplicateError):
            s.define('e')

    def test_iter(self):
        s = Settings({'b': None, 'a': 1, 'c': None, 'd': 2})
        self.assertEqual(list(s), ['a', 'b', 'c', 'd']) # sorted

    def test_immutable(self):
        s = Settings({'a': None})
        with self.assertRaises(TypeError):
            s['a'] = 1

if __name__ == '__main__':
    unittest.main()

class PrefixedSettingsTest(unittest.TestCase):
    def test_init(self):
        s = Settings()
        p = PrefixedSettings(s, 'prefix')
        self.assertIsInstance(p, PrefixedSettings)

    def test_define(self):
        s = Settings()
        p = PrefixedSettings(s, 'prefix')
        with self.assertRaises(KeyError):
            s.get('prefix.a')
        p.define('a')
        self.assertEquals(s.get('prefix.a'), None)

class GlobalSettingsTest(unittest.TestCase):
    def test_init(self):
        g = GlobalSettings()
        self.assertIsInstance(g, GlobalSettings)

    def test_get(self):
        g = GlobalSettings()
        s = g.get()
        self.assertIsInstance(s, Settings)

class GlobalSettingsMutationTest(unittest.TestCase):
    def test_enter(self):
        gs = GlobalSettings()
        m1 = GlobalSettingsMutation(gs, a=1)
        m2 = GlobalSettingsMutation(gs, a=2)
        gs.get().define("a", default=0)
        self.assertEqual(gs.get().get("a"), 0)
        with m1:
            self.assertEqual(gs.get().get("a"), 1)
            with m2:
                self.assertEqual(gs.get().get("a"), 2)
            self.assertEqual(gs.get().get("a"), 1)
        self.assertEqual(gs.get().get("a"), 0)

    def test_enter_undefined(self):
        gs = GlobalSettings()
        m1 = GlobalSettingsMutation(gs, a=1)
        with self.assertRaises(KeyError):
            with m1:
                pass
