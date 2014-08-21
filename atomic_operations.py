from functools import partial

class FakeContainer( object ):
    '''Given vars(SOMETHING), where SOMETHING is a class/module/...                 
    acts as if it were SOMETHING on attribute access.                                   
    works recursively, so our attributes are FakeContainer too, unless
    stop_criteria( attribute ) == True. If it is, return wrap_function( attribute )'''
    
    def __init__(self, context, stop_criteria, wrap_function):
        self._context= context
        self._stop_criteria= stop_criteria
        self._wrap= wrap_function
    
    def __getattr__( self, atr ):
        obj= self._context.get(atr)
        if obj is None:
            raise AttributeError(atr)
        if self._stop_criteria(obj):
            return self._wrap(obj)
        return FakeContainer( vars(obj), self._stop_criteria, self._wrap ) 


class AtomicOperationSequence( FakeContainer ): 
    '''Context manager that allows execution of a sequence of functions as if it was a atomic
    operation, by applying rollback functions if any of the functions fail (throw a exception)'''
    def __init__(self, reverse_function, vars=None):
        '''reverse_function is a function that, given three arguments (f,f_args,f_kwargs) representing a function call,
           returns a three-tuple (g, g_args, g_kwargs) representing the function call that reverts it.
           vars are the locals of the caller. If None, will try to obtain them'''
        if vars is None:
            import inspect
            vars= inspect.currentframe().f_back.f_locals
        self.reverse_function= reverse_function
        FakeContainer.__init__(self, vars, lambda x: callable(x), lambda x: partial( self._run_reversible_function, x )) 
    
    def _run_reversible_function( self, f, *args, **kwargs ):
        '''wrapper function that execute the wrapped one and schedule the reverse operation on self'''
        reverse_f, reverse_args, reverse_kwargs= self.reverse_function(f, args, kwargs)
        assert callable(reverse_f)
        f(*args, **kwargs)
        self.reverse_operations.append( partial(reverse_f, *reverse_args, **reverse_kwargs) )
 
    def __enter__(self):
        self.reverse_operations=[]
        return self

    def __exit__(self, type, value, traceback):
        if type is None:
            return
        #A exception occurred
        print "AtomicOperationSequence: Exception detected. Rolling back..."
        for f in self.reverse_operations:
            try:
                f()
            except Exception as e:
                import sys
                raise Exception("AtomicOperationSequence: FAILED ON ROLLBACK"), None, sys.exc_info()[2]


def test():
    def f1():
        print "f1 executed"
    def f2(arg, bad=True):
        print "f2 executed with arguments({arg}, {bad})".format(**locals())
    def g1():
        print "reverted results of f1"
    def g2(arg, bad):
        raise Exception
        print "reverted results of f2( {arg}, {bad} )".format(**locals())
    def reverse(f, args, kwargs):
        if f==f1:
            return g1, (), {} 
        if f==f2:
            return g2, args, kwargs
        raise Exception("reverse function not found")
    
    with AtomicOperationSequence(reverse) as atomic:
        atomic.f1()
        raise Exception
        atomic.f2("bla", True)

if __name__=='__main__':
    test()
    

        
