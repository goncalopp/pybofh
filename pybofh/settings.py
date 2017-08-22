'''Implements package / module settings'''

class DuplicateError(Exception):
    "Raised when a setting is defined twiced"

class Settings(object):
    """
    A Settings instance holds settings definitions and values.
    New settings definitions can be added, but not overriden.
    Values are immutable. They cannot be modified without returning a new Settings instance
    If existing is specified, a copy of a existing Settings instance is returned.
    updated_values is a optional {name: value} that contains values to be change from existing.
    """
    def __init__(self, values=None, descs=None):
        self._values = {}
        self._descs = {}
        if values:
            self._values.update(values)
        if descs:
            self.enforce_defined(descs)
            self._descs.update(descs)

    @classmethod
    def update_values(cls, existing_settings, updated_values):
        """Constructor for a new Settings() based on existing_settings but with
        updated values
        """
        assert isinstance(existing_settings, Settings)
        assert isinstance(updated_values, dict)
        existing_settings.enforce_defined(updated_values)
        values = {}
        values.update(existing_settings._values) # pylint: disable=protected-access
        values.update(updated_values)
        return Settings(values, existing_settings._descs) # pylint: disable=protected-access

    def get(self, name):
        return self._values[name]

    def get_description(self, name):
        if not name in self._values:
            raise KeyError(name)
        return self._descs.get(name, '')

    def enforce_defined(self, names):
        inexistent_k = set(names) - set(self._values.keys())
        if inexistent_k:
            raise KeyError(list(inexistent_k))

    def for_(self, prefix):
        return PrefixedSettings(self, prefix)

    def define(self, name, desc=None, default=None):
        """Defines a new setting.

        name is the name of the setting.
        desc is a human-readable description of the setting.
        default is the default value of the setting
        """
        if name in self._values:
            raise DuplicateError(name)
        self._values[name] = default
        if desc is not None:
            self._descs[name] = desc


    def __getitem__(self, name):
        return self.get(name)

    def __iter__(self):
        return iter(sorted(self._values.keys()))

class PrefixedSettings(object):
    """A view over Settings with a given prefix.
    Example: PrefixedSettings(_, "a").define("b") defines a.b
    """
    def __init__(self, settings, prefix):
        assert isinstance(settings, Settings)
        assert isinstance(prefix, basestring)
        self.settings = settings
        self.prefix = prefix

    def define(self, name, *args, **kwargs):
        self.settings.define(self.prefixed_name(name), *args, **kwargs)

    def prefixed_name(self, name):
        return self.prefix + '.' + name

class GlobalSettings(object):
    """A container for settings, mutatable exclusively through a context manager"""
    def __init__(self):
        self._settings = Settings()

    def get(self):
        return self._settings

    def _set(self, settings):
        """This is used exclusively by GlobalSettingsMutation"""
        self._settings = settings

class GlobalSettingsMutation(object):
    '''Context Manager for changing settings'''
    def __init__(self, global_settings, **kwargs):
        self.global_settings = global_settings
        self.updates = kwargs
        self.old_settings = None

    def __enter__(self):
        self.old_settings = self.global_settings.get()
        new_settings = Settings.update_values(self.old_settings, self.updates)
        self.global_settings._set(new_settings) # pylint: disable=protected-access
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.global_settings._set(self.old_settings) # pylint: disable=protected-access
