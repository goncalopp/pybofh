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


class Values(object):
    """A Values instance holds concrete values for settings.
    Values are immutable. They cannot be modified after the creation of the Values instance.
    If existing is specified, a copy of a existing Settings instance is returned.
    updated_values is a optional {key: value} that contains values to be change from existing.
    """
    def __init__(self, defs, values=None):
        assert isinstance(defs, Definitions)
        self.defs = defs
        self._values = {}
        if values:
            self.defs.enforce_defined(values)
            self._values.update(values)

    def update(self, updated_values, defs=None):
        """Constructor for a new Settings() based on existing_settings but with
        updated values
        """
        assert isinstance(updated_values, dict)
        defs = defs or self.defs
        values = {}
        values.update(self._values)
        values.update(updated_values)
        return Values(defs, values)

    def get(self, key, default=None):
        self.defs.enforce_defined(key)
        return self._values.get(key, default)

    def __getitem__(self, key):
        self.defs.enforce_defined(key)
        return self._values[key]


class Settings(object):
    """A container for settings definitions and values.

    The values instance is immutable, and the reference to it can be modified exclusively through a context manager.
    """
    def __init__(self, defs=None, values=None, resolver=None):
        self._defs = defs or Definitions()
        self._values = values or Values(self._defs)
        self.resolver = resolver or Resolver()
        assert self._values.defs is self._defs

    def get(self, name, default=None):
        """Gets the value of a setting.
        If the setting is not defined, raises UndefinedError.
        If the setting has no value, the default is returned.
        To get without a default, use __getitem__.
        """
        key = self.resolver.name_to_key(name)
        return self._values.get(key, default)

    def __getitem__(self, name):
        """Gets the value of a setting.
        If the setting is not defined, raises UndefinedError.
        If the setting has no value, raises KeyError.
        """
        key = self.resolver.name_to_key(name)
        return self._values[key]

    def __iter__(self):
        l = self.resolver.key_to_name(list(self._defs), ignore_mismatches=True)
        return iter(l)

    def define(self, name, description=None):
        """Defines a new setting"""
        key = self.resolver.name_to_key(name)
        self._defs.add(key, description)

    def _set_values(self, values):
        """Used exclusively by SettingsMutation"""
        self._values = values

    def for_(self, prefix):
        """Returns a new Settings object that represents a view over these settings,
        with all setting names starting with a prefix.
        Example: settings.for_("prefix").get("a") is equivalent to settings.get("prefix.a").
        """
        resolver = self.resolver.for_(prefix)
        return Settings(defs=self._defs, values=self._values, resolver=resolver)

    def values(self, **kwargs):
        """Returns a context manager that mutates the given values.
        The values are changed only while the context manager is opened.
        """
        return SettingsMutation(self, kwargs)


class SettingsMutation(object):
    """Context Manager for changing settings"""
    def __init__(self, settings, updates):
        self.settings = settings
        self.updates = updates
        self.old_values = None

    def __enter__(self):
        self.old_values = self.settings._values # pylint: disable=protected-access
        updates = self.settings.resolver.name_to_key(self.updates)
        new_values = self.old_values.update(updates)
        self.settings._set_values(new_values) # pylint: disable=protected-access
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.settings._set_values(self.old_values) # pylint: disable=protected-access
