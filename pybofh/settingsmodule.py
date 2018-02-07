'''Implements package / module settings'''

class DuplicateError(Exception):
    """Raised when a setting is defined twiced"""

class UndefinedError(KeyError):
    """Raised when a undefined setting key is used"""

class Resolver(object):
    """A Resolver translates between settings names (user provided) and internal keys to use as storage.
    Keys can, for example, be given a prefix automatically.
    """
    def __init__(self, prefix=None):
        self.separator = '.'
        if prefix is not None:
            prefix = prefix + self.separator
        else:
            prefix = ''
        self.prefix = prefix

    def _name_to_key(self, name):
        return self.prefix + name

    def name_to_key(self, name):
        """Transforms a name into a fully-resolved key"""
        if isinstance(name, basestring):
            return self._name_to_key(name)
        if isinstance(name, dict):
            d = name
            return {self._name_to_key(name): v for name, v in d.items()}
        if isinstance(name, list):
            l = name
            return [self._name_to_key(name) for name in l]
        raise TypeError

    def _key_to_name(self, key):
        if not key.startswith(self.prefix):
            raise ValueError("Failed to convert key to name for {}".format(key))
        n = len(self.prefix)
        return key[n:]

    def _key_to_name_gen(self, key_iter, ignore_mismatches=False):
        for k in key_iter:
            try:
                n = self._key_to_name(k)
                yield n
            except ValueError:
                if not ignore_mismatches:
                    raise

    def key_to_name(self, key, ignore_mismatches=False):
        """Transforms a fully-resolved key into a name"""
        if isinstance(key, basestring):
            return self._key_to_name(key)
        if isinstance(key, dict):
            d = key
            keys = self._key_to_name_gen(d, ignore_mismatches)
            return {n: d[k] for k, n in zip(d, keys)}
        if isinstance(key, list):
            l = key
            return list(self._key_to_name_gen(l, ignore_mismatches))
        raise TypeError


    def for_(self, prefix):
        """Returns a new Resolver, with a extra prefix"""
        return Resolver(prefix=self.prefix + prefix)


class Definitions(object):
    """List of definitions of settings.
    New settings definitions can be added, but not overriden or deleted.
    """
    def __init__(self):
        self._defs = set()
        self._descs = {}
        self._defaults = {}

    def add(self, key, desc=None):
        """Defines a new setting.

        key is the key of the setting.
        desc is a human-readable description of the setting.
        """
        if key in self._defs:
            raise DuplicateError(key)
        self._defs.add(key)
        if desc is not None:
            self._descs[key] = desc

    def get_description(self, key):
        self.enforce_defined(key)
        return self._descs.get(key, '')

    def enforce_defined(self, keys):
        if isinstance(keys, basestring):
            keys = (keys,)
        inexistent_k = set(keys) - self._defs
        if inexistent_k:
            raise UndefinedError(list(inexistent_k))

    def __iter__(self):
        return iter(sorted(self._defs))

class FrozenDict(dict):
    """A immutable dictionary"""
    def __setitem__(self, k, v):
        raise Exception("Can't change values of FrozenDict")

    def pop(self, _):
        raise Exception("Can't change values of FrozenDict")

    def popitem(self, _):
        raise Exception("Can't change values of FrozenDict")

    def update(self, _):
        raise Exception("Can't change values of FrozenDict")

    @classmethod
    def merge(cls, a, b):
        """Merges two FrozeDict. Similar to update(), but returns new instance"""
        x = {}
        x.update(a)
        x.update(b)
        return cls(x)

class Values(FrozenDict):
    pass

class ValuesPointer(object):
    """A ValuesPointer points to a Values instance.

    This indirection is needed so several Settings instances (with potentially
    different resolvers / scopes) share the same ValuesPointer, such that one
    instance's values are updated, all of the other instances share that update.
    """
    def __init__(self):
        self.values = Values()

    def swap(self, new_values):
        assert isinstance(new_values, Values)
        old = self.values
        self.values = new_values
        return old

class Settings(object):
    """A container for settings definitions and values.

    The values instance is immutable, and the reference to it can be modified exclusively through a context manager.
    """
    def __init__(self, defs=None, valuesptr=None, resolver=None):
        self.defs = defs or Definitions()
        self._valuesptr = valuesptr or ValuesPointer()
        self.resolver = resolver or Resolver()
        for v in self._valuesptr.values:
            self.defs.enforce_defined(v)

    def get(self, name, default=None):
        """Gets the value of a setting.
        If the setting is not defined, raises UndefinedError.
        If the setting has no value, the default is returned.
        To get without a default, use __getitem__.
        """
        key = self.resolver.name_to_key(name)
        self.defs.enforce_defined(key)
        return self._valuesptr.values.get(key, default)

    def __getitem__(self, name):
        """Gets the value of a setting.
        If the setting is not defined, raises UndefinedError.
        If the setting has no value, raises KeyError.
        """
        key = self.resolver.name_to_key(name)
        self.defs.enforce_defined(key)
        return self._valuesptr.values[key]

    def __iter__(self):
        l = self.resolver.key_to_name(list(self.defs), ignore_mismatches=True)
        return iter(l)

    def define(self, name, description=None):
        """Defines a new setting"""
        key = self.resolver.name_to_key(name)
        self.defs.add(key, description)

    def _qualify_new_values(self, values):
        if not isinstance(values, Values):
            # scope the dict keys to this resolver
            values = Values(self.resolver.name_to_key(values))
        for v in values:
            self.defs.enforce_defined(v)
        return values

    def _set_values(self, values):
        """Sets the settings values. Returns the old ones"""
        values = self._qualify_new_values(values)
        return self._valuesptr.swap(values)

    def _update_values(self, values):
        """Updates (merges) the settings values. Returns the old ones"""
        values = self._qualify_new_values(values)
        old = self._valuesptr.values
        return self._valuesptr.swap(Values.merge(old, values))

    def for_(self, prefix):
        """Returns a new Settings object that represents a view over these settings,
        with all setting names starting with a prefix.
        Example: settings.for_("prefix").get("a") is equivalent to settings.get("prefix.a").
        """
        resolver = self.resolver.for_(prefix)
        return Settings(defs=self.defs, valuesptr=self._valuesptr, resolver=resolver)

    def __call__(self, **kwargs):
        return self.change(**kwargs)

    def change(self, **kwargs):
        """Returns a context manager that mutates the given values.
        The values are changed only while the context manager is opened.
        Not thread-safe.
        """
        return SettingsMutation(self, kwargs)

class SettingsMutation(object):
    """Context Manager for changing settings. Not thread-safe."""
    def __init__(self, settings, updates):
        self.settings = settings
        self.updates = updates
        self.old_values = None

    def __enter__(self):
        # pylint: disable=protected-access
        self.old_values = self.settings._update_values(self.updates)
        return self

    def __exit__(self, exc_type, exc_value, tb):
        # pylint: disable=protected-access
        self.settings._set_values(self.old_values)
