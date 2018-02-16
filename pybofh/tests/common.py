from pybofh.shell import FakeShell

class FakeEnvironment(object):
    def __init__(self):
        self.shell = FakeShell()
        self.devices = []
        self.inactive_devices = []

    def add_device(self, fakedevice, active=True):
        self.inactive_devices.append(fakedevice)
        if active:
            self.activate_device(fakedevice)

    def activate_device(self, fakedevice):
        if self.get_device(fakedevice.path):
            raise Exception("FakeEnvironment: a device already exists with path {}".format(fakedevice.path))
        self.inactive_devices.remove(fakedevice)
        self.devices.append(fakedevice)
        self.shell.add_fake(fakedevice.fake_shell_match, fakedevice.fake_shell_execute)

    def deactivate_device(self, fakedevice):
        self.devices.remove(fakedevice)
        self.inactive_devices.append(fakedevice)
        self.shell.remove_fake(fakedevice.fake_shell_match)

    def get_device(self, path, active=True, enforce=False):
        l = self.devices if active else self.inactive_devices
        for d in l:
            if d.path == path:
                return d
        if enforce:
            raise Exception("Can't find FakeDevice for path: {}".format(path))
        # returns None if there's no match and enforce == False

    def path_exists(self, path):
        """Emulates os.path.exists"""
        return self.get_device(path) is not None

    def read_file(self, path, size=None):
        """Emulates pybofh.misc.read_file"""
        dev = self.get_device(path)
        if dev is None:
            raise Exception("Can't find device for path: {}".format(path))
        if dev.content is None:
            raise Exception("FakeDevice has no content: {}".format(path))
        return dev.content[:size]



class FakeDevice(object):
    def __init__(self, path, data=None, content=None, parent=None, size=10*2**20, granularity=1):
        self.path = path
        self.data = data # a pybofh.blockdevice.Data subclass or instance
        self.content = content # a string, representing device content raw data
        self.size = size # in bytes
        self.granularity = granularity
        self.child = None
        self.parent = parent
        if parent:
            parent.child = self

    @property
    def file_type(self):
        """The file type, in the syle returned by "file" UNIX command"""
        if self.data is None:
            content_type = "data"
        else:
            name = self.data.__name__
            content_type = "some data, {}".format(name)
        return "{}: {}".format(self.path, content_type)

    def fake_shell_match(self, command):
        """Whether this FakeDevice should execute the faked command - used in FakeShell"""
        return self.path in command

    def fake_shell_execute(self, command):
        """Implementation of command execution for FakeShell"""
        if command == ('/sbin/blockdev', '--getsize64', self.path):
            return str(self.size)
        if command == ('file', '--special', '--dereference', self.path):
            return self.file_type
        raise Exception("Unhandled fake command: {}".format(command))

    def __repr__(self):
        return "FakeDevice<{}>".format(self.path)

def get_fake_environment():
    """Returns the current test's FakeEnvironment instance.
    This function is meant to be overriden using mock.patch.
    """
    raise Exception("get_fake_environment is meant to be overriden by a mock.patch")

