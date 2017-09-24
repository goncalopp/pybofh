from abc import ABCMeta, abstractmethod
import logging
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

    @abstractmethod
    def run_process(self, command):
        """Executes the command, and ensures it doesn't return a error. Returns the output"""
        raise NotImplementedError

class SystemShell(Shell):
    def run_process(self, command):
        logging.debug("Running command: %s", lambda: "".join(command))
        result = subprocess.check_output(command)
        return result

class MockShell(Shell):
    def __init__(self):
        self._mocks = []
        self.run_commands = []

    def add_mock(self, command, response):
        """Command can either be a tuple, or a callable.
        If it's a tuple, it represents the literal command that this mock should respond to.
        Example: ("ls", "thisdirectory")
        If command is a callable, it should take a single argument (the command) and return True iff the response should be used.

        Response can be either a string or a callable.
        If it's a string, it's interpreted as the literal command response.
        If it's a callable, it should take a single argument (the command) and return the response (string).
        """
        self._mocks.append((command, response))

    def _get_mock_response(self, command):
        for mock_command, mock_response in self._mocks:
            if (callable(mock_command) and mock_command(command)) or command == mock_command:
                self.run_commands.append(command)
                return mock_response(command) if callable(mock_response) else mock_response
        raise Exception("No mock response found for {}".format(command))

    def run_process(self, command):
        return self._get_mock_response(command)

shell = SystemShell() # singleton

def get():
    return shell

