'''Tests for settings.py'''

# pylint: disable=pointless-statement, protected-access

import unittest
from pybofh.settingsmodule import Settings, SettingsMutation, DuplicateError, UndefinedError, Resolver, Definitions

class ResolverTest(unittest.TestCase):
    def test_name_to_key(self):
        r = Resolver(prefix="something")
        self.assertEqual(r.name_to_key("a"), "something.a")
        self.assertEqual(r.name_to_key("a"), "something.a")
        # list
        self.assertEqual(
            r.name_to_key(["a", "something.a"]),
            ["something.a", "something.something.a"])
        # dict
        self.assertEqual(
            r.name_to_key({"a": 1, "something.a": 2}),
            {"something.a": 1, "something.something.a": 2})

    def test_key_to_name(self):
        r = Resolver(prefix="something")
        self.assertEqual(r.key_to_name("something.a"), "a")
        with self.assertRaises(ValueError):
            # wrong prefix
            r.key_to_name("somethingelse.a")
        # list
        self.assertEqual(
            r.name_to_key(["a", "something.a"]),
            ["something.a", "something.something.a"])
        # dict
        self.assertEqual(
            r.key_to_name({"something.a": 1, "something.something.a": 2}),
            {"a": 1, "something.a": 2})
        with self.assertRaises(ValueError):
            # wrong prefix
            r.key_to_name({"something.a": 1, "omething.a": 2})

    def test_for(self):
        r = Resolver()
        self.assertEqual(r.name_to_key("a"), "a")
        self.assertEqual(r.key_to_name("a"), "a")
        r2 = r.for_("r2")
        self.assertEqual(r2.name_to_key("a"), "r2.a")
        self.assertEqual(r2.key_to_name("r2.a"), "a")
        r3 = r2.for_("r3")
        self.assertEqual(r3.name_to_key("a"), "r2.r3.a")
        self.assertEqual(r3.key_to_name("r2.r3.a"), "a")

class DefinitionsTest(unittest.TestCase):
    def test_add(self):
        defs = Definitions()
        self.assertEqual(list(defs), [])
        defs.add("a")
        self.assertEqual(list(defs), ["a"])
        defs.add('b', 'desc')
        self.assertEqual(list(defs), ["a", "b"])
        with self.assertRaises(DuplicateError):
            defs.add("b")

    def test_get_description(self):
        defs = Definitions()
        defs.add("a", "desc")
        defs.add("b")
        self.assertEqual(defs.get_description('a'), 'desc')
        self.assertEqual(defs.get_description('b'), '')
        with self.assertRaises(UndefinedError):
            defs.get_description('d')

    def test_enforce_defined(self):
        defs = Definitions()
        defs.add("a")
        defs.add("b")
        with self.assertRaises(UndefinedError):
            defs.enforce_defined(["e"])
        with self.assertRaises(UndefinedError):
            defs.enforce_defined(["a", "b", "c"])
        defs.enforce_defined(set(["a", "b"]))

    def test_iter(self):
        defs = Definitions()
        defs.add("b", "somedesc")
        defs.add("a")
        defs.add("c")
        self.assertEqual(list(defs), ['a', 'b', 'c']) # sorted


class SettingsTest(unittest.TestCase):
    def test_init(self):
        s = Settings()
        self.assertIsInstance(s, Settings)

    def test_define(self):
        s = Settings()
        s.define("a")
        s.define("b", "description")
        with self.assertRaises(DuplicateError):
            s.define("b")

    def test_get(self):
        s = Settings()
        s.define("a")
        s.define("b", "description")
        s.define("c")
        s._update_values({"a": 1, "b": 2})
        self.assertEqual(s.get("a"), 1)
        self.assertEqual(s["a"], 1)
        self.assertEqual(s.get("b"), 2)
        self.assertEqual(s.get("b", 9), 2)
        self.assertEqual(s.get("c", 9), 9)
        self.assertEqual(s.get("c"), None)
        with self.assertRaises(KeyError):
            s["c"]
        with self.assertRaises(UndefinedError):
            s.get("d", 1)

    def test_iter(self):
        s = Settings()
        s.define("a")
        s.define("b", "description")
        s.define("c")
        self.assertEqual(list(s), ["a", "b", "c"])
        self.assertEqual(list(s), ["a", "b", "c"])

    def test_for_(self):
        s = Settings()
        s.define("a")
        s.define("b", "desc")
        s.define("prefix.a")
        s.define("prefix.b", "otherdesc")
        s.define("prefix.c")
        s._update_values({"a": 1, "prefix.a": 2, "prefix.b": 3})

        sfi = s.for_("inexistent")
        with self.assertRaises(UndefinedError):
            sfi.get("a")
        with self.assertRaises(UndefinedError):
            sfi.get("c")
        self.assertEqual(list(sfi), [])

        sfp = s.for_("prefix")
        self.assertEquals(sfp.get("a"), 2)
        self.assertEquals(sfp.get("b"), 3)
        self.assertEquals(sfp.get("c", 99), 99)
        with self.assertRaises(KeyError):
            sfi.get("c")
        with self.assertRaises(UndefinedError):
            sfi.get("d")
        self.assertEqual(list(sfp), ["a", "b", "c"])

    def test_changs(self):
        s = Settings()
        with s.change() as mutation:
            self.assertIsInstance(mutation, SettingsMutation)
        # functionality is tested on TestSettingsMutation and IntegrationTest



class SettingsMutationTest(unittest.TestCase):
    def test_enter(self):
        s = Settings()
        m1 = SettingsMutation(s, {"a":1})
        m2 = SettingsMutation(s, {"a":2, "b":3})
        s.define("a")
        s.define("b")
        self.assertEqual(s.get("a"), None)
        with m1:
            self.assertEqual(s.get("a"), 1)
            self.assertEqual(s.get("b"), None)
            with self.assertRaises(UndefinedError):
                s.get("c", 1)
            with m2:
                self.assertEqual(s.get("a"), 2)
                self.assertEqual(s.get("b"), 3)
                with self.assertRaises(UndefinedError):
                    s.get("c", 1)
            self.assertEqual(s.get("a"), 1)
        self.assertEqual(s.get("a"), None)

    def test_enter_different_prefix(self):
        s = Settings()
        s_prefix = s.for_("prefix")
        s.define("a")
        s.define("prefix.a")
        m = SettingsMutation(s, {"a": 1, "prefix.a": 2})
        with m:
            self.assertEqual(s.get("a"), 1)
            self.assertEqual(s.get("prefix.a"), 2)
            self.assertEqual(s_prefix.get("a"), 2)

    def test_enter_undefined(self):
        s = Settings()
        m1 = SettingsMutation(s, {"a":1})
        with self.assertRaises(KeyError):
            with m1:
                pass

class IntegrationTest(unittest.TestCase):
    def test_settings_for_with_mutation(self):
        s = Settings()
        s.define("a")
        s.define("b", "desc")
        s.define("prefix.a")
        s.define("prefix.b", "otherdesc")
        s.define("prefix.c")
        s._update_values({"a": 1, "prefix.a": 2, "prefix.b": 3})

        sfi = s.for_("inexistent")
        # no values can be set in prefix with no settings
        with self.assertRaises(UndefinedError):
            with sfi(a=1):
                pass
        with self.assertRaises(UndefinedError):
            with sfi(b=1):
                pass

        sfp = s.for_("prefix")
        with sfp(a=88, b=77):
            # values in prefix are changed
            self.assertEquals(sfp.get("a"), 88)
            self.assertEquals(sfp.get("b", 99), 77)
            self.assertEquals(sfp.get("c", 99), 99)
            with self.assertRaises(KeyError):
                sfi.get("c")
            with self.assertRaises(UndefinedError):
                sfi.get("d")
            # values outside prefix are not changed
            self.assertEquals(s.get("a", 99), 1)
            self.assertEquals(s.get("b", 99), 99)
            with self.assertRaises(KeyError):
                s["b"]
            with self.assertRaises(UndefinedError):
                s.get("c")


if __name__ == '__main__':
    unittest.main()
