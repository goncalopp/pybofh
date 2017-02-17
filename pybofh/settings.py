'''Implements global settings'''
DEFAULT_SETTINGS = {}

#A module level variable. This is not thread-safe at the moment
_settings = {}
_settings.update(DEFAULT_SETTINGS)

def get_settings():
    return dict(_settings) # prevent modification

def _set_settings(updated_settings, update=False):
    '''Changes the settings.
    If update == True, this extends the current settings;
    otherwise it replaces them.
    The settings dict should be treated as immutable'''
    global _settings #pylint: disable=global-statement
    new_settings = {}
    if update:
        new_settings.update(_settings)
    new_settings.update(updated_settings)
    _settings = new_settings #atomic update

class settings(object): #pylint: disable=invalid-name
    '''Context Manager for changing settings'''
    def __init__(self, **kwargs):
        self.updates = kwargs
        self.old_settings = None

    def __enter__(self):
        self.old_settings = _settings
        _set_settings(self.updates, update=True)
        return self

    def __exit__(self, exc_type, exc_value, tb):
        _set_settings(self.old_settings)
