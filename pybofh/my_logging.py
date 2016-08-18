import logging

PACKAGE_NAME= 'pybofh'

log= logging.getLogger(PACKAGE_NAME) #logger for the whole package
#formatter = logging.Formatter('%(asctime)s\t%(levelname)s\t%(name)s\t%(module)s\t%(funcName)s\t%(message)s')
formatter = logging.Formatter('%(module)s\t%(message)s')
hdlr = logging.StreamHandler()
hdlr.setFormatter(formatter)
log.addHandler(hdlr)
log.setLevel(logging.DEBUG)

def get_logger(module_name):
    '''Get a logger for a particular module of the package'''
    assert module_name.startswith(PACKAGE_NAME + '.')
    return logging.getLogger(module_name)


