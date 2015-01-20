import os
import shutil

def patch_file( path, replacements={} ):
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
