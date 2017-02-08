import os
from pybofh import shell as subprocess
from misc import sfilter, rsplit
from pybofh import blockdevice


REMOVED= '[REMOVED]'

class PV(blockdevice.Data):
    def create(self, **kwargs):
        createPV(self.blockdevice.path, **kwargs)

    def createVG(self, name, **kwargs):
        createVG(name, self.blockdevice.path, **kwargs)
        return VG(name)

    def remove(self):
        removePV(self.blockdevice.path)
        self.blockdevice= REMOVED
    
    @property
    def size(self):
        raise NotImplementedError

    @property
    def resize_granularity(self):
        raise NotImplementedError

    def _resize(self, byte_size, minimum, maximum, interactive):   
        raise NotImplementedError

class VG(object):
    def __init__(self, vg_name):
        self.name= vg_name
        if not self.name in getVGs():
            raise Exception("VG {} does not exist".format(vg_name))

    @property
    def path(self):
        return "/dev/{}/".format(self.name)

    def getLVs(self):
        names= getLVs(self.name, full_path=False)
        lvs= [ LV(self, name) for name in names ]
        return lvs


    def createLV( self, name, *args, **kwargs ):
        createLV( self.name, name, *args, **kwargs)
        return LV( self, name )

    def lv(self, lv_name):
        return LV(self, lv_name)

    def __repr__(self):
        return "{}<{}>".format(self.__class__.__name__, self.name)

    def remove(self):
        removeVG(self.name)
        self.name= REMOVED

class LV(blockdevice.BaseBlockDevice):
    def __init__( self, vg, lv_name ):
        if not isinstance(vg, VG):
            vg= VG(vg)
        if not lv_name in getLVs(vg.name, full_path=False):
            raise Exception("LV {} does not exist on VG {}".format(lv_name, vg.name))
        self.vg= vg
        self.name= lv_name
        super(LV, self).__init__(self.path)

    @property
    def path(self):
        return os.path.join(self.vg.path, self.name)
    
    def __repr__(self):
        return "{}<{}>".format(self.__class__.__name__, self.name)

    def remove( self, *args, **kwargs ):
        removeLV( self.vg.name, self.name, *args, **kwargs)
        self.vg= REMOVED
        self.name= REMOVED

    @property
    def resize_granularity(self):
        vg_name= self.vg.name
        all_vg_info= _parse_vgdisplay()
        vg_info= all_vg_info[vg_name]
        pe_size= vg_info['PE Size'] #physical extent size
        assert 1 * 2**20 <= pe_size <= 32 * 2**20 #sanity check
        return pe_size

    def _resize(self, byte_size, minimum, maximum, interactive):
        if minimum or maximum:
            raise Exception("Options not supported: minimum, maximum")
        ssize= str(byte_size) + "b"
        options=[]
        if not interactive:
            options.append("-f")
        subprocess.check_call( ["lvresize"] + options + ["--size", ssize, self.path])

    def rename(self, new_name):
        renameLV(self.vg.name, self.name, new_name)
        self.name = new_name


def getVGs():
    out= subprocess.check_output("vgdisplay")
    vg_lines= sfilter('VG Name', out)
    vgs= [rsplit(x)[2] for x in vg_lines]
    return vgs

def getLVs(vg, full_path=True):
    dir="/dev/"+vg
    disks= os.listdir(dir)
    if full_path:
        return [os.path.join(dir, x) for x in disks]
    else:
        return disks

def createLV(vg, name, size):
    if not isinstance(size, basestring):
        size= str(size)+"B"
    print "creating LV {name} with size={size}".format(**locals())
    command = ("/sbin/lvcreate", vg, "--name", name, "--size", size)
    subprocess.check_call(command)

def removeLV(vg, name, force=True):
    print "deleting LV {name}".format(**locals())
    force_flag= ("-f",) if force else ()
    command = ("/sbin/lvremove",) + force_flag + ("{vg}/{name}".format(**locals()),)
    subprocess.check_call(command)

def renameLV(vg, name, new_name):
    print "renaming LV {name}".format(**locals())
    command= ["/sbin/lvrename", vg, name, new_name]
    subprocess.check_call(command)
 
def createPV(device, force=True):
    print "creating PV {device}".format(**locals())
    force_flag= ("-f",) if force else ()
    command= ("/sbin/pvcreate",) + force_flag + (device,)
    subprocess.check_call(command)

def createVG(name, pvdevice):
    print "creating VG {name} with PV {pvdevice}".format(**locals())
    command = ("/sbin/vgcreate", name, pvdevice)
    subprocess.check_call(command)

def removeVG(name):
    print "deleting VG {name}".format(**locals())
    command = ("/sbin/vgremove", name)
    subprocess.check_call(command)

def removePV(device):
    print "deleting PV {device}".format(**locals())
    command = ("/sbin/pvremove", device)
    subprocess.check_call(command)

def _parse_xxdisplay(output, expected_keys, is_separator_line, name_key, column2_start=24):
    '''Generic parser for output of pvdisplay, vgdisplay and lvdisplay'''
    def parse_line(line):
        if "System ID" in line:
            #no value data for this one? brakes assertions
            return ("System ID", None) 
        assert line.startswith("  ") 
        assert line[2]!=" " # first column
        assert line[column2_start-1]==" "
        assert line[column2_start]!=" " # second column
        tup= (line[2:column2_start].strip(), line[column2_start:].strip())
        assert len(tup[0]) > 0 and len(tup[1]) > 0
        return tup
    def convert_line_tup(tup):
        SIZE_SUFFIXES= {'KiB': 2**10, 'MiB': 2**20, 'GiB': 2**30, 'TiB': 2**40}
        if tup[0].endswith('Size'):
            tokens= tup[1].split()
            assert tokens[-1] in SIZE_SUFFIXES
            if len(tokens)==2: #only a number and a prefix
                size= int(float(tokens[0]) * SIZE_SUFFIXES[tokens[1]])
                tup= (tup[0], size)
        return tup
    lines= output.splitlines()
    lines= [line for line in lines if line.strip()!='']
    sep_lines_idx= [i for i,line in enumerate(lines) if is_separator_line(line)]
    sep_lines_idx.append(len(lines))
    assert len(sep_lines_idx)>=1 # TODO: what if there are no VGs?
    xx_dicts={}
    for xx_i in range(len(sep_lines_idx) - 1):
        start_line= sep_lines_idx[xx_i] + 1
        end_line= sep_lines_idx[xx_i+1]
        xx_lines= lines[start_line:end_line]
        assert 8 <= len(xx_lines) <= 30
        xx_tuples= map(parse_line, xx_lines)
        xx_tuples2= map(convert_line_tup, xx_tuples)
        xx_dict= dict(xx_tuples2)
        assert set(xx_dict) >= set(expected_keys)
        xx_name= xx_dict[name_key]
        xx_dicts[xx_name]= xx_dict
    return xx_dicts

def _parse_pvdisplay():
    EXPECTED_KEYS = [ 'PV Name', 'VG Name', 'PV Size', 'Allocatable',
        'PE Size', 'Total PE', 'Free PE', 'Allocated PE', 'PV UUID']
    is_separator_line= lambda line: '--- Physical volume ---' in line
    out= subprocess.check_output("/sbin/pvdisplay")
    name_key='PV Name'
    return _parse_xxdisplay(out, EXPECTED_KEYS, is_separator_line, name_key)

def _parse_vgdisplay():
    EXPECTED_KEYS = ['Act PV', 'Alloc PE / Size', 'Cur LV', 'Cur PV',
        'Format', 'Free  PE / Size', 'MAX LV', 'Max PV', 'Metadata Areas',
        'Metadata Sequence No', 'Open LV', 'PE Size', 'System ID', 'Total PE',
        'VG Access', 'VG Name', 'VG Size', 'VG Status', 'VG UUID']
    is_separator_line= lambda line: '--- Volume group ---' in line
    out= subprocess.check_output("/sbin/vgdisplay")
    name_key='VG Name'
    return _parse_xxdisplay(out, EXPECTED_KEYS, is_separator_line, name_key)


def _parse_lvdisplay():
    EXPECTED_KEYS = [ 'LV Path', 'LV Name', 'VG Name', 'LV UUID',
            'LV Write Access', 'LV Creation host, time', 'LV Status',
            '# open', 'LV Size', 'Current LE', 'Segments', 'Allocation',
            'Read ahead sectors', '- currently set to', 'Block device']
    is_separator_line= lambda line: '--- Logical volume ---' in line
    out= subprocess.check_output("/sbin/lvdisplay")
    name_key='LV Name'
    return _parse_xxdisplay(out, EXPECTED_KEYS, is_separator_line, name_key, column2_start=25)

blockdevice.register_data_class("LVM2 PV", PV)
