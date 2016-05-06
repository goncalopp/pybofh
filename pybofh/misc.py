import os
import subprocess
import shutil

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
    return subprocess.check_output( ["file", "--special", "--dereference", path])
