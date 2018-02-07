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
        shell.add_mock('pwd', 'response')
        response = shell.check_call(('pwd',))
        self.assertEqual(response, None)

    def test_check_output(self):
        shell = MockShell()
        shell.add_mock('pwd', 'response')
        response = shell.check_output(('pwd',))
        self.assertEqual(response, 'response')

    def test_add_mock(self):
        shell = MockShell()
        # literal command, literal response
        shell.add_mock(('pwd'), 'response')
        self.assertEqual(shell.run_process('pwd',), 'response')
        # command function, literal response
        shell.add_mock(lambda command: command[0] == 'cat', 'content')
        self.assertEqual(shell.run_process(('cat', 'myfile')), 'content')
        # command function, response function
        shell.add_mock(
                lambda command: command[0] == ('ls'), 
                lambda command: 'dir ' + command[1])
        self.assertEqual(shell.run_process(('ls', '.')), 'dir .')
        # no mock command match
        with self.assertRaises(MockShell.NoMockForCommand):
            shell.run_process(('ps', '.'))

    def test_add_mock_binary(self):
        shell = MockShell()
        # literal response, relative path binary
        shell.add_mock_binary('bla', 'abc')
        self.assertEqual(shell.check_output(('bla', 'a')), 'abc')
        self.assertEqual(shell.check_output(('bla', 'a', 'b')), 'abc')
        with self.assertRaises(MockShell.NoMockForCommand):
            shell.check_output(('/bin/bla','a'))
        # literal response, absolute path binary
        shell.add_mock_binary('/bin/cat', 'content')
        self.assertEqual(shell.check_output(('/bin/cat','a')), 'content')
        self.assertEqual(shell.check_output(('cat','a')), 'content')
        with self.assertRaises(MockShell.NoMockForCommand):
            shell.check_output(('/sbin/cat','a'))
        # response function
        shell.add_mock_binary(
            '/bin/ls', 
            lambda command: "called {}: {}".format(command[0], command[1]))
        self.assertEqual(shell.check_output(('/bin/ls','a')), 'called /bin/ls: a')
        self.assertEqual(shell.check_output(('ls','a')), 'called ls: a')




if __name__ == "__main__":
    unittest.main()
