import unittest
import mock

from pybofh.shell import SystemShell, MockShell

class SystemShellTest(unittest.TestCase):
    def test_check_call(self):
        shell = SystemShell()
        response = shell.check_call(('pwd',))
        self.assertEqual(response, None)
        response = shell.check_call(('ls', '.'))
        self.assertEqual(response, None)

    def test_check_output(self):
        shell = SystemShell()
        response = shell.check_output(('pwd',))
        self.assertEqual(response[0], '/')
        response = shell.check_output(('ls', '.'))
        self.assertGreater(len(response), 0)

class MockShellTest(unittest.TestCase):
    def test_check_call(self):
        shell = MockShell()
        shell.add_mock(('pwd'), 'response')
        shell.add_mock(lambda command: command[0] == 'who', 'user')
        shell.add_mock(
                lambda command: command[0] == ('ls'), 
                lambda command: 'response ' + command[1])
        response = shell.check_call(('pwd',))
        self.assertEqual(response, None)
        response = shell.check_call(('ls', '.'))
        self.assertEqual(response, None)
        with self.assertRaises(Exception):
            # no mock for this command
            shell.check_call(('ps', '.'))

    def test_check_output(self):
        shell = MockShell()
        shell.add_mock(('pwd'), 'response')
        shell.add_mock(lambda command: command[0] == 'who', 'user')
        shell.add_mock(
                lambda command: command[0] == ('ls'), 
                lambda command: 'response ' + command[1])
        response = shell.check_output(('pwd',))
        self.assertEqual(response, 'response')
        response = shell.check_output(('ls', '.'))
        self.assertEqual(response, 'response .')
        with self.assertRaises(Exception):
            # no mock for this command
            shell.check_output(('ps', '.'))

if __name__ == "__main__":
    unittest.main()
