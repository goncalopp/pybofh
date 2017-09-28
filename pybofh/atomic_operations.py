"""This module contains classes and functions for executing functions with side
effects and reverting them"""
import sys
import functools
import logging
log = logging.getLogger(__name__)

class SequenceError(Exception):
    """Raised when RevertibleOperationSequence encounters a sequence ordering/length problem"""

class RevertCalculationError(Exception):
    """Raised when calculating the revert function fails"""
    def __init__(self, f, f_args, f_kwargs, msg=""):
        self.f, self.f_args, self.f_kwargs = f, f_args, f_kwargs
        Exception.__init__(self, "Failed to calculate the revert function for {}(*{}, **{}): {}".format(f, f_args, f_kwargs, msg))

class RevertError(Exception):
    """Raised when a rollback function fails"""
    def __init__(self, cause):
        assert isinstance(cause, BaseException)
        self.cause = cause
        msg = "Failed to run rollback function. One or more side effects may have not been reverted. Cause: \n" + str(cause)
        Exception.__init__(self, msg)

def find_reverse(f, f_args, f_kwargs, reverse_function):
    """Given a function f, its arguments, and a reverse_function such that
    reverse_function(f, f_args, f_kwargs) == (g, g_args, g_kwargs), where g is
    the function that reverts the side effects of f, this function returns
    (g, g_args, g_kwargs). f can be a RevertibleFunction - in that case,
    reverse_function is not used and the reverse is calculated by
    RevertibleFunction."""
    if isinstance(f, RevertibleFunction):
        g, g_args, g_kwargs = f.compute_revert(f_args, f_kwargs)
    else:
        if reverse_function is None:
            raise RevertCalculationError(f, f_args, f_kwargs, "reverse_function is None")
        try:
            g, g_args, g_kwargs = reverse_function(f, f_args, f_kwargs)
        except Exception as e:
            new_e = RevertCalculationError(f, f_args, f_kwargs, "revert function raised " + str(e))
            raise new_e, None, sys.exc_info()[2] # preserve stack trace
    if not callable(g):
        raise RevertCalculationError(f, f_args, f_kwargs, "calculated reverse function is not callable: {}".format(g))
    return  g, g_args, g_kwargs

class RevertibleOperationSequence(object):
    """Allows step execution of a sequence of functions with side effects
    ensuring that each step is revertible, by deriving a rollback function
    for every function in the sequence.
    """
    def __init__(self, reverse_function=None):
        """reverse_function is a function that, given three arguments
        (f,f_args,f_kwargs) representing a function call, returns a three-tuple
        (g, g_args, g_kwargs) representing the function call that reverts it.
        reverse_function may be None - then only RevertibleFunction instances
        are accepted on append().
        """
        self._reverse_function = reverse_function
        self._f_seq = [] # sequence of functions that are executed
        self._g_seq = [] # sequence of reverse functions that revert f_seq (same order)
        self._exec_step = 0 # index of the next f to be executed

    def append(self, f, f_args, f_kwargs):
        """Appends a new function (and its call arguments) to the sequence.
        f may be a RevertibleFunction instance.
        The function is NOT called immediately.
        """
        if not callable(f):
            raise TypeError("Given f is not callable: {}".format(f))
        assert callable(f)
        assert len(self._f_seq) == len(self._g_seq)
        assert 0 <= self._exec_step <= len(self._f_seq)
        g, g_args, g_kwargs = find_reverse(f, f_args, f_kwargs, self._reverse_function)
        self._f_seq.append((f, f_args, f_kwargs))
        self._g_seq.append((g, g_args, g_kwargs))

    def step(self):
        """Steps the sequence forward - executes the next f in the sequence.
        Returns f()'s return.
        """
        # pylint: disable = star-args
        if self.finished:
            raise SequenceError("Already executed all functions in the sequence")
        f, f_args, f_kwargs = self._f_seq[self._exec_step]
        ret = f(*f_args, **f_kwargs) # execute forward function
        self._exec_step += 1 # only step after f() finished without raising exception
        return ret

    def step_back(self):
        """Steps the sequence backwards - rollbacks the last executed f
        by calling the rollback function g.
        Returns g()'s return.
        """
        # pylint: disable = star-args
        if not self.started:
            raise SequenceError("Already rollbacked all functions in the sequence")
        g, g_args, g_kwargs = self._g_seq[self._exec_step - 1]
        try:
            log.info("Rolling back {}".format((g, g_args, g_kwargs)))
            ret = g(*g_args, **g_kwargs) # execute rollback function
        except BaseException as e: # catch all, including KeyboardInterrupt
            raise RevertError(e), None, sys.exc_info()[2] # preserve stack trace
        self._exec_step -= 1 # only step after g() finished without raising exception
        return ret

    def revert_all(self):
        while self.started:
            self.step_back()


    @property
    def started(self):
        return self._exec_step > 0

    @property
    def finished(self):
        return self._exec_step >= len(self._f_seq)

class RevertibleFunction(object):
    """Wrapper around a function with side-effects"""
    def __init__(self, f, g, revert_args=None):
        """f: The function with side-effects.
        g: The function that reverts the side-effects of f.
        revert_args: a function that, given the args and kwargs of a call to f,
        calculates the args and kwargs of the call to g.
        """
        self.f = f
        self.g = g
        self.revert_args = revert_args or (lambda args, kwargs: (args, kwargs))

    def compute_revert(self, args, kwargs):
        """Returns the 3-tuple (g, g_args, g_kwargs) such that calling
        g(*g_args, **g_kwargs) reverts a call to f(*args, **kwargs).
        """
        g_args, g_kwargs = self.revert_args(args, kwargs)
        assert isinstance(g_args, tuple)
        assert isinstance(g_kwargs, dict)
        return self.g, g_args, g_kwargs

    def __call__(self, *args, **kwargs):
        return self.f(*args, **kwargs)

class AtomicContext(object):
    """Context manager that allows running a sequence of function with side
    effects as if it was a single atomic operation. If any exception is raised
    while inside a Atomic context, side effects will be reverted by calling
    a rollback function for every executed function.
    Every function with side effects needs to be wrapped using a call to the context manager.

    Example:
    with Atomic(reverse_function) as atomic:
        f()               # f is a function with no side effects
        atomic(g)()       # g is a function with side effects
        atomic(h)(1, a=3) # h is a function with side effects
        raise Exception   # side effects of h() and g() are reverted on context exit
    """
    def __init__(self, reverse_function=None):
        self._seq = RevertibleOperationSequence(reverse_function)

    def _execute(self, f, *args, **kwargs):
        """Executes the function f"""
        if not self._seq.finished:
            # we want the function to execute immediately
            raise SequenceError("The sequence has queued functions")
        self._seq.append(f, args, kwargs)
        return self._seq.step()

    def __call__(self, f):
        return functools.partial(self._execute, f)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            return
        # A exception occurred
        log.info("AtomicContext: Exception occurred. Rolling back...")
        self._seq.revert_all()
        log.info("AtomicContext: Rollback finished successfully.")
        raise exc_type, exc_value, traceback

def has_reverse(g, revert_args=None):
    """Decorator for a function f with side effects that defines the reverse
    operation g that reverts the side effects, and a function (revert_args)
    that maps the arguments (args, kwargs) of f to the arguments of g.
    """
    return functools.partial(RevertibleFunction, g=g, revert_args=revert_args)
