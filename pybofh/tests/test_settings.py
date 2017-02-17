'''Tests for settings.py'''

import unittest
from pybofh.settings import DEFAULT_SETTINGS, settings, get_settings

class SettingsTest(unittest.TestCase):
    # pylint: disable=invalid-name
    def test_settings_defaults(self):
        s = get_settings()
        self.assertEquals(s, DEFAULT_SETTINGS)

    def test_settings_immutable(self):
        mutate_settings = get_settings()
        #Check we can't change the settings by mutating return object
        mutate_settings['a'] = 1
        test_settings = get_settings()
        self.assertEquals(test_settings.get('a'), None)
        # Check we can't change settings by setting them,
        # they should be immutable after calling get_settings()
        with settings(a=1):
            self.assertEquals(test_settings.get('a'), None)

    def test_settings_set(self):
        with settings(a=1, b="1", c=None):
            s = get_settings()
            self.assertEquals(s.get('a'), 1)
            self.assertEquals(s.get('b'), "1")
            self.assertEquals(s.get('c', 1), None)

    def test_settings_unset(self):
        with settings(a=1, b="1", c=None):
            get_settings()
        s = get_settings()
        self.assertEquals(s.get('a'), None)
        self.assertEquals(s.get('b'), None)
        self.assertEquals(s.get('c', 1), 1)

    def test_settings_double_set(self):
        with settings(a=1):
            with settings(a=2):
                s = get_settings()
                self.assertEquals(s.get('a'), 2)

if __name__ == '__main__':
    unittest.main()
