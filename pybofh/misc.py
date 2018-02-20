import os
from pybofh import shell
import shutil

def read_file(path, size=None):
    f = open(path)
    return f.read() if size is None else f.read(size)

def list_dir(directory):
    return os.listdir(directory)

def patch_file( path, replacements={} ):
    '''given a file, replaces all occurences of the keys in REPLACEMENTS in the file with their values'''
    assert os.path.isfile(path)
    shutil.copy(path, path+".bak")
    n_replac=0
    with open(path+".bak") as original:
       with open(path, 'w') as rewritten:
           for line in original:
               for k,v in replacements.items():
                   replacement=line.replace(k,v)
                   n_replac+= int(line!=replacement)
                   line=replacement
               rewritten.write(line)
    os.remove(path+".bak")
    return n_replac

def sfilter( pattern, string_list ):
    '''similar to grep'''
    if isinstance(string_list, str):
        string_list= string_list.splitlines()
    return list(filter(lambda x: pattern in x, string_list))

def rsplit( string, delimiter=' ' ):
    '''similar to str.split, but ignores repeated delimiters'''
    return list(filter(lambda x: x!='', string.split(delimiter)))

def file_type( path ):
    return shell.get().check_output(("file", "--special", "--dereference", path))

def gcd(a,b):
    '''Greatest common denominator'''
    a,b= min(a,b), max(a,b)
    c= b%a
    if c==0:
        return a
    else:
        return gcd(a, c)

def lcm(*args):
    '''Least common multiple'''
    if len(args)>2:
        return lcm(lcm(args[0], args[1]), *args[2:])
    a,b= args
    result= abs(a*b)/gcd(a,b)
    assert result <= a * b
    return result
