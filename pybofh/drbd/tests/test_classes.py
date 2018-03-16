"""Tests for classes.py"""
# pylint: disable = no-member, too-many-public-methods
import unittest
import mock

from pybofh.drbd import classes
from pybofh.tests import common

class FakeEnvironment(common.FakeEnvironment):
    """Shell environment - keeps state for side effects from commands"""
    @staticmethod
    def drbdadm(command):
        c1 = command[1]
        if c1 in ("attach", "detach", "connect", "disconnect", "up", "down", "primary", "secondary", "invalidate", "invalidate-remote", "create-md", "verify", "pause-sync", "resume-sync"):
            return
        elif c1 == "role":
            return "Primary/Secondary\n"
        elif c1 == "cstate":
            return "Connected\n"
        elif c1 == "dstate":
            return "UpToDate/UpToDate\n"
        else:
            raise NotImplementedError(str(command))

def generic_setup(testcase):
    """Sets up mocks and fakes for a TestCase"""
    env = FakeEnvironment()
    testcase.env = env
    env.shell.add_fake_binary("/sbin/drbdadm", env.drbdadm)
    mocklist = [
        {"target": "pybofh.shell.get", "side_effect": lambda: env.shell},
    ]
    patches = [mock.patch(autospec=True, **a) for a in mocklist]
    for patch in patches:
        patch.start()

class Resource(unittest.TestCase):
    """Tests for Resource"""
    def setUp(self):
        generic_setup(self)

    def tearDown(self):
        mock.patch.stopall()

    def test_init(self):
        r = classes.Resource("some_name", check_existence=False)
        self.assertIsInstance(r, classes.Resource)
        r = classes.Resource("some_name", check_existence=True)
        self.assertIsInstance(r, classes.Resource) # faked in FakeEnvironment

    def test_device(self):
        r = classes.Resource("some_name", check_existence=False)
        self.assertEqual(r.device, "/dev/drbd_some_name")

    def test_attach(self):
        r = classes.Resource("some_name", check_existence=False)
        r.attach()
        self.assertEqual(self.env.shell.run_commands[-1], ('/sbin/drbdadm', 'attach', 'some_name'))

    def test_detach(self):
        r = classes.Resource("some_name", check_existence=False)
        r.detach()
        self.assertEqual(self.env.shell.run_commands[-1], ('/sbin/drbdadm', 'detach', 'some_name'))

    def test_connect(self):
        r = classes.Resource("some_name", check_existence=False)
        r.connect()
        self.assertEqual(self.env.shell.run_commands[-1], ('/sbin/drbdadm', 'connect', 'some_name'))

    def test_disconnect(self):
        r = classes.Resource("some_name", check_existence=False)
        r.disconnect()
        self.assertEqual(self.env.shell.run_commands[-1], ('/sbin/drbdadm', 'disconnect', 'some_name'))

    def test_up(self):
        r = classes.Resource("some_name", check_existence=False)
        r.up()
        self.assertEqual(self.env.shell.run_commands[-1], ('/sbin/drbdadm', 'up', 'some_name'))

    def test_down(self):
        r = classes.Resource("some_name", check_existence=False)
        r.down()
        self.assertEqual(self.env.shell.run_commands[-1], ('/sbin/drbdadm', 'down', 'some_name'))

    def test_primary(self):
        r = classes.Resource("some_name", check_existence=False)
        r.primary()
        self.assertEqual(self.env.shell.run_commands[-1], ('/sbin/drbdadm', 'primary', 'some_name'))

    def test_secondary(self):
        r = classes.Resource("some_name", check_existence=False)
        r.secondary()
        self.assertEqual(self.env.shell.run_commands[-1], ('/sbin/drbdadm', 'secondary', 'some_name'))

    def test_invalidate(self):
        r = classes.Resource("some_name", check_existence=False)
        r.invalidate()
        self.assertEqual(self.env.shell.run_commands[-1], ('/sbin/drbdadm', 'invalidate', 'some_name'))

    def test_invalidate_remote(self):
        r = classes.Resource("some_name", check_existence=False)
        r.invalidate_remote()
        self.assertEqual(self.env.shell.run_commands[-1], ('/sbin/drbdadm', 'invalidate-remote', 'some_name'))

    def test_create_md(self):
        r = classes.Resource("some_name", check_existence=False)
        r.create_md()
        self.assertEqual(self.env.shell.run_commands[-1], ('/sbin/drbdadm', 'create-md', 'some_name'))

    def test_role(self):
        r = classes.Resource("some_name", check_existence=False)
        role = r.role()
        self.assertEqual(self.env.shell.run_commands[-1], ('/sbin/drbdadm', 'role', 'some_name'))
        self.assertEqual(role, ["Primary", "Secondary"])

    def test_cstate(self):
        r = classes.Resource("some_name", check_existence=False)
        cstate = r.cstate()
        self.assertEqual(self.env.shell.run_commands[-1], ('/sbin/drbdadm', 'cstate', 'some_name'))
        self.assertEqual(cstate, "Connected")

    def test_dstate(self):
        r = classes.Resource("some_name", check_existence=False)
        dstate = r.dstate()
        self.assertEqual(self.env.shell.run_commands[-1], ('/sbin/drbdadm', 'dstate', 'some_name'))
        self.assertEqual(dstate, ["UpToDate", "UpToDate"])

    def test_verify(self):
        r = classes.Resource("some_name", check_existence=False)
        r.verify()
        self.assertEqual(self.env.shell.run_commands[-1], ('/sbin/drbdadm', 'verify', 'some_name'))

    def test_pause_sync(self):
        r = classes.Resource("some_name", check_existence=False)
        r.pause_sync()
        self.assertEqual(self.env.shell.run_commands[-1], ('/sbin/drbdadm', 'pause-sync', 'some_name'))

    def test_resume_sync(self):
        r = classes.Resource("some_name", check_existence=False)
        r.resume_sync()
        self.assertEqual(self.env.shell.run_commands[-1], ('/sbin/drbdadm', 'resume-sync', 'some_name'))

    def test_repr(self):
        r = classes.Resource("some_name", check_existence=False)
        self.assertEqual(repr(r), """drbd.Resource("some_name")""")
