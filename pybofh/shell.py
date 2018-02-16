from abc import ABCMeta, abstractmethod
import functools
import logging
import os.path
import subprocess

log = logging.getLogger(__name__)

class Shell(object):
    """Shell executes processes on a system. It has a interface similar to subprocess."""
    __metaclass__ = ABCMeta
    def check_call(self, command):
        """Executes the command, and ensures it doesn't return a error. Doesn't return the output"""
        self.run_process(command)

    def check_output(self, command):
        """Executes the command, and ensures it doesn't return a error. Returns the output"""
        return self.run_process(command)

    def run_process(self, command):
        """Executes the command, and ensures it doesn't return a error. Returns the output"""
        if isinstance(command, (str, unicode)):
            command = (command,)
        else:
            command = tuple(command)
        logging.debug("Running command: %s" % " ".join(command))
        try:
            response = self._run_process(command)
        except Exception as e:
            logging.debug("Failed: %s" % e)
            raise
        logging.debug("Result: %s" % response)
        return response

    def _run_process(self, command):
        raise NotImplementedError

class SystemShell(Shell):
    def _run_process(self, command):
        result = subprocess.check_output(command)
        return result

class FakeShell(Shell):
    class NoFakeForCommand(Exception):
        def __init__(self, command):
            Exception.__init__(self, "No fake exists for command: {}".format(command))

    def __init__(self):
        self._fakes = []
        self.run_commands = []

    def add_fake(self, command, response):
        """Adds a fake command to the FakeShell.

        Command can either be a tuple, or a callable.
        If it's a tuple, it represents the literal command that this fake should respond to.
        Example: ("ls", "thisdirectory")
        If command is a callable, it should take a single argument (the command) and return True iff the response should be used.

        Response can be either a string or a callable.
        If it's a string, it's interpreted as the literal command response.
        If it's a callable, it should take a single argument (the command) and return the response (string).
        """
        if isinstance(command, str):
            command = (command,)
        elif callable(command):
            pass
        else:
            command = tuple(command)
        self._fakes.append((command, response))

    def remove_fake(self, command):
        """Removes a fake command from the FakeShell.
        The command argument must be the same object as passed to add_fake.
        """
        removed_fakes = [fake for fake in self._fakes if fake[0] == command]
        if not removed_fakes:
            raise KeyError("Fake not found: {}".format(command))
        for fake in removed_fakes:
            self._fakes.remove(fake)

    def add_fake_binary(self, binary_path, response):
        """Adds a fake "binary" to the FakeShell.

        This is a helper function on top of add_fake(), that helps creating the command function,
        such that all commands that start with the given binary name are matched. This also simulates shell path, so that add_fake_binary('/bin/ls', ...) will match command ('ls', ...).
        binary_path can be an absolute or relative path.
        The response argument is passed unmodified to add_fake() (see documentation there).
        """
        f = functools.partial(_command_matches_binary, binary_path)
        self.add_fake(f, response)

    def _get_fake_response(self, command):
        for fake_command, fake_response in self._fakes:
            if (callable(fake_command) and fake_command(command)) or command == fake_command:
                self.run_commands.append(command)
                return fake_response(command) if callable(fake_response) else fake_response
        raise FakeShell.NoFakeForCommand(command)

    def _run_process(self, command):
        assert not isinstance(command, str)
        return self._get_fake_response(command)

def _command_matches_binary(binary, command):
    """Evaluates whether a given command matches a given binary.
    Example: _command_matches_binary('/bin/ls', ('ls', 'mydir')) == True
    """
    assert isinstance(binary, str)
    absolute_binary = binary.startswith('/')
    absolute_command = command[0].startswith('/')
    if absolute_binary:
        if absolute_command:
            return binary == command[0]
        else: # absolute_binary, not absolute_command
            path = ('/bin', '/sbin', '/usr/bin', '/usr/sbin', '/usr/local/bin', '/usr/local/sbin')
            dirname, binname = os.path.split(binary)
            return dirname in path and command[0] == binname
    else: # not absolute_binary
        if absolute_command:
            return False # local binaries are not added to any directory (i.e.: no simulated cwd)
        else: #not absolute_binary, not absolute_command
            return binary == command[0]
    assert False # should not be reached




    raise NotImplementedError

shell = SystemShell() # singleton

def get():
    return shell

