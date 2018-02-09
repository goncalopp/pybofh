from pybofh.shell import FakeShell

class FakeEnvironment(object):
    def __init__(self):
        self.shell = FakeShell()
        self.devices = []

    def add_device(self, fakedevice):
        if self.get_device(fakedevice.path):
            raise Exception("FakeEnvironment: a device already exists with path {}".format(fakedevice.path))
        self.devices.append(fakedevice)
        self.shell.add_fake(fakedevice.fake_shell_match, fakedevice.fake_shell_execute)

    def get_device(self, path):
        for d in self.devices:
            if d.path == path:
                return d
        # returns None if there's no match


class FakeDevice(object):
    def __init__(self, path, content, parent=None, size=10*2**20, granularity=1):
        self.path = path
        self.content = content
        self.size = size
        self.granularity = granularity
        self.child = None
        self.parent = parent
        if parent:
            parent.child = self

    def fake_shell_match(self, command):
        """Whether this FakeDevice should execute the faked command - used in FakeShell"""
        return self.path in command

    def fake_shell_execute(self, command):
        """Implementation of command execution for FakeShell"""
        if command == ('/sbin/blockdev', '--getsize64', self.path):
            return str(self.size)
        if command == ('file', '--special', '--dereference', self.path):
            name = self.content.__name__ if callable(self.content) else self.content.__class__.__name__
            return "{}: some data: {}".format(self.path, name)
        raise Exception("Unhandled fake command: " + command)

