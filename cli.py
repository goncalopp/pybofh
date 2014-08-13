import sys

def python_cli(available_functions):
    fs= [x for x in available_functions if callable(x) and x.__name__!="python_cli"]
    f_names= [x.__name__ for x in fs]
    if len(sys.argv)<2:
        print "usage: ./scriptname functionname arg1 arg2 ..."
        print "available functions:"
        print "\t"+"\n\t".join(f_names) 
        exit(1)
    try:
        f=fs[f_names.index(sys.argv[1])]
    except ValueError:
        print "function does not exist:",sys.argv[1]
        exit(2)
    assert callable(f)
    result=f(*sys.argv[2:])
    if not result is None:
        print result
