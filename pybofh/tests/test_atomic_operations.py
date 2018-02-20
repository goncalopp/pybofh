"""Tests for atomic_operations.py"""
# pylint: disable = no-member, protected-access, unused-argument, too-many-public-methods, attribute-defined-outside-init
import unittest
import mock
from pybofh.atomic_operations import RevertibleOperationSequence, AtomicContext, SequenceError, RevertError, RevertCalculationError, has_reverse

def setup_functions(testcase, wrap=False):
    """If wrap == True, saves functions wrapped in ReversibleFunction, and returns empty reverse function.
    Otherwise, returns plain functions and a complete reverse function.
    """
    testcase.f1_return = 563543 #random number
    testcase.f2_return = 234095
    testcase.g1_return = 348959
    testcase.g2_return = 205235
    testcase.f1 = mock.Mock(return_value=testcase.f1_return)
    testcase.f2 = mock.Mock(return_value=testcase.f2_return)
    testcase.g1 = mock.Mock(return_value=testcase.g1_return)
    testcase.g2 = mock.Mock(return_value=testcase.g2_return)
    def reverse_full(f, args, kwargs):
        if f == testcase.f1:
            return testcase.g1, args, kwargs
        if f == testcase.f2:
            return testcase.g2, args, kwargs
        raise Exception("Failed to find reverse for {}".format(f))
    def reverse_empty(f, args, kwargs):
        raise Exception("Failed to find reverse for {}".format(f))
    if wrap:
        # wrap functions
        testcase.f1 = has_reverse(testcase.g1)(testcase.f1) # decorator
        testcase.f2 = has_reverse(testcase.g2)(testcase.f2)
    testcase.reverse = reverse_empty if wrap else reverse_full

class RevertibleOperationSequenceTest(unittest.TestCase):
    def setUp(self):
        setup_functions(self)

    def tearDown(self):
        mock.patch.stopall()

    def test_init(self):
        ros = RevertibleOperationSequence(lambda: None)
        self.assertIsInstance(ros, RevertibleOperationSequence)

    def test_append(self):
        ros = RevertibleOperationSequence(lambda x: (None, (), {}))
        with self.assertRaises(RevertCalculationError): # lambda must take 3 args
            ros.append(self.f1, (), {})
        ros = RevertibleOperationSequence(lambda f, args, kwargs: None)
        with self.assertRaises(RevertCalculationError): # lambda must return be 3-tuple
            ros.append(self.f1, (), {})
        ros = RevertibleOperationSequence(lambda f, args, kwargs: (None, (), {}))
        with self.assertRaises(RevertCalculationError): # returned g must be callable
            ros.append(self.f1, (), {})
        ros = RevertibleOperationSequence(lambda f, args, kwargs: (f, (), {}))
        ros.append(self.f1, (), {})

    def _test_stepping_aux(self, ros, n_f1, n_f2, n_g1, n_g2, step, started, finished): #pylint: disable = too-many-arguments
        self.assertEqual(len(self.f1.mock_calls), n_f1)
        self.assertEqual(len(self.f2.mock_calls), n_f2)
        self.assertEqual(len(self.g1.mock_calls), n_g1)
        self.assertEqual(len(self.g2.mock_calls), n_g2)
        self.assertEqual(ros._exec_step, step)
        self.assertEqual(ros.started, started)
        self.assertEqual(ros.finished, finished)

    def test_stepping(self):
        ros = RevertibleOperationSequence(self.reverse)
        ros.append(self.f1, (1, "a"), {"x":2, "y":3})
        ros.append(self.f2, (11, "aa"), {"ax":12, "ay":13})
        self._test_stepping_aux(ros, 0, 0, 0, 0, 0, False, False)
        # step 1
        ret = ros.step()
        self.assertEqual(ret, self.f1_return)
        self.f1.assert_called_with(1, "a", x=2, y=3)
        self._test_stepping_aux(ros, 1, 0, 0, 0, 1, True, False)
        # step 2
        ret = ros.step()
        self.assertEqual(ret, self.f2_return)
        self.f2.assert_called_with(11, "aa", ax=12, ay=13)
        self._test_stepping_aux(ros, 1, 1, 0, 0, 2, True, True)
        # step 3 should fail
        with self.assertRaises(SequenceError):
            ros.step()
        self._test_stepping_aux(ros, 1, 1, 0, 0, 2, True, True)
        # step 3 should fail
        # step back 2
        ret = ros.step_back()
        self.assertEqual(ret, self.g2_return)
        self.g2.assert_called_with(11, "aa", ax=12, ay=13)
        self._test_stepping_aux(ros, 1, 1, 0, 1, 1, True, False)
        # step back 1
        ret = ros.step_back()
        self.assertEqual(ret, self.g1_return)
        self.g1.assert_called_with(1, "a", x=2, y=3)
        self._test_stepping_aux(ros, 1, 1, 1, 1, 0, False, False)
        # step back 0 should fail
        with self.assertRaises(SequenceError):
            ros.step_back()
        self._test_stepping_aux(ros, 1, 1, 1, 1, 0, False, False)

    def test_stepping_wrapped(self):
        """Tests stepping with functions wrapped in has_reverse"""
        setup_functions(self, wrap=True) # overrides setUp
        ros = RevertibleOperationSequence(self.reverse)
        ros.append(self.f1, (1, "a"), {"x":2, "y":3})
        self.assertEqual(len(self.f1.f.mock_calls), 0)
        # step 1
        ret = ros.step()
        self.assertEqual(ret, self.f1_return)
        self.assertEqual(len(self.f1.f.mock_calls), 1)
        self.f1.f.assert_called_with(1, "a", x=2, y=3)
        self.assertEqual(len(self.g1.mock_calls), 0)
        # step back 1
        ret = ros.step_back()
        self.assertEqual(ret, self.g1_return)
        self.assertEqual(len(self.f1.f.mock_calls), 1)
        self.g1.assert_called_with(1, "a", x=2, y=3)
        self.assertEqual(len(self.g1.mock_calls), 1)

class AtomicContextTest(unittest.TestCase):
    def setUp(self):
        setup_functions(self)

    def tearDown(self):
        mock.patch.stopall()

    def test_context(self):
        with AtomicContext(self.reverse) as atomic:
            # initial conditions
            self.assertEqual(len(self.f1.mock_calls), 0)
            self.assertEqual(len(self.f2.mock_calls), 0)
            # execute f2
            ret = atomic(self.f2)(1, "a", x=2, y=3)
            self.assertEqual(ret, self.f2_return)
            self.assertEqual(len(self.f1.mock_calls), 0)
            self.assertEqual(len(self.f2.mock_calls), 1)
            self.f2.assert_called_with(1, "a", x=2, y=3)
            # execute f2
            tmp = atomic(self.f2)
            ret = tmp(z=1)
            self.assertEqual(ret, self.f2_return)
            self.assertEqual(len(self.f1.mock_calls), 0)
            self.assertEqual(len(self.f2.mock_calls), 2)
            self.f2.assert_called_with(z=1)
            # execute f1
            ret = atomic(self.f1)(1, "a", x=2, y=3)
        # exit context
        self.assertEqual(ret, self.f1_return)
        self.assertEqual(len(self.f1.mock_calls), 1)
        self.assertEqual(len(self.f2.mock_calls), 2)
        self.f1.assert_called_with(1, "a", x=2, y=3)
        self.assertEqual(len(self.g1.mock_calls), 0)
        self.assertEqual(len(self.g2.mock_calls), 0)

    def test_context_rollback(self):
        def raiseerr(*args, **kwargs):
            raise OSError("fake")
        self.f1 = mock.Mock(side_effect=raiseerr)
        with self.assertRaises(OSError):
            with AtomicContext(self.reverse) as atomic:
                # initial conditions
                # execute f2
                atomic(self.f2)(1, "a", x=2, y=3)
                # execute f2
                atomic(self.f2)(x=3)
                # execute f1 (and fail)
                atomic(self.f1)(z=1) # should throw OSError
                self.assertEqual(True, False) # should not be reached
        self.assertEqual(len(self.g1.mock_calls), 0) # f1 did not finish, so g1 is not called
        self.assertEqual(len(self.g2.mock_calls), 2)
        self.g2.assert_called_with(1, "a", x=2, y=3) # last g2 reverts first f2 call

    def test_context_rollback_failure(self):
        def raiseerr(*args, **kwargs):
            raise OSError("fake")
        self.f1 = mock.Mock(side_effect=raiseerr)
        self.g2 = mock.Mock(side_effect=raiseerr)
        with self.assertRaises(RevertError):
            with AtomicContext(self.reverse) as atomic:
                # initial conditions
                # execute f2
                atomic(self.f2)(1, "a", x=2, y=3)
                # execute f2
                atomic(self.f2)(x=3)
                # execute f1 (and fail)
                atomic(self.f1)(z=1) # should throw OSError
                self.assertEqual(True, False) # should not be reached
        self.assertEqual(len(self.g1.mock_calls), 0) # f1 did not finish, so g1 is not called
        self.assertEqual(len(self.g2.mock_calls), 1) # the first g2 failed
        self.g2.assert_called_with(x=3) # last g2 reverts first f2 call

if __name__ == '__main__':
    unittest.main()
