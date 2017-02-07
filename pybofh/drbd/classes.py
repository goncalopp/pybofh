import inspect
import os
from functools import partial

import drbdadm

class Resource(object):
    '''object oriented management of resources. Example: Resource('resource_name').connect()'''
    def __init__(self, resource_name, check_existence=True):
        self._name= resource_name #private. changing this variable will have unexpected results
        def is_resource_function( f ):
            if not callable(f):
                return False
            return inspect.getargspec(f).args[0]=='resource' #check the first function argument is named resource
        resource_functions= filter( is_resource_function, vars(drbdadm).values() )
        for f in resource_functions:
            setattr(self, f.__name__, partial(f,self._name))
        if check_existence:
            try:
                self.role()
            except Exception as e:
                raise Exception("Failed to create resource {}: {}".format(self._name, e))

    @property
    def device(self):
        path= "/dev/drbd_"+self._name
        assert os.path.exists(path)
        return path
