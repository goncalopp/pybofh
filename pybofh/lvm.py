import os
import subprocess
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
            raise Exception("VG {} does not exist".format(name))

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
        return "{}<{},{}>".format(self.__class__.__name__, self.vg, self.name)

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
    command="/sbin/lvcreate {vg} --name {name} --size {size}".format(**locals())
    subprocess.check_call(command, shell=True)

def removeLV(vg, name, force=True):
    print "deleting LV {name}".format(**locals())
    force_flag= "-f" if force else ""
    command="/sbin/lvremove {force_flag} {vg}/{name}".format(**locals())
    subprocess.check_call(command, shell=True)
 
def createPV(device, force=True):
    print "creating PV {device}".format(**locals())
    force_flag= "-f" if force else ""
    command="/sbin/pvcreate {force_flag} {device}".format(**locals())
    subprocess.check_call(command, shell=True)

def createVG(name, pvdevice):
    print "creating VG {name} with PV {pvdevice}".format(**locals())
    command="/sbin/vgcreate {name} {pvdevice}".format(**locals())
    subprocess.check_call(command, shell=True)

def removeVG(name):
    print "deleting VG {name}".format(**locals())
    command="/sbin/vgremove {name}".format(**locals())
    subprocess.check_call(command, shell=True)

def removePV(device):
    print "deleting PV {device}".format(**locals())
    command="/sbin/pvremove {device}".format(**locals())
    subprocess.check_call(command, shell=True)

def _parse_vgdisplay():
    EXPECTED_KEYS = ['Cur PV', 'PE Size', 'VG Status', 'Format', 'VG Access', 
        'Alloc PE / Size', 'VG Size', 'Free  PE / Size', 'Open LV', 'Max PV', 
        'Metadata Sequence No', 'MAX LV', 'System ID', 'Total PE', 'VG UUID', 
        'Metadata Areas', 'Act PV', 'VG Name', 'Cur LV']
    is_separator_line= lambda line: '--- Volume group ---' in line
    def parse_line(line):
        if "System ID" in line:
            #no value data for this one? brakes assertions
            return ("System ID", None) 
        assert line.startswith("  ") 
        assert line[2]!=" " # first column
        assert line[23]==" " # before second column
        assert line[24]!=" " # second column
        tup= (line[2:24].strip(), line[24:].strip())
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
    out= subprocess.check_output("/sbin/vgdisplay")
    lines= out.splitlines()
    lines= [line for line in lines if line.strip()!='']
    sep_lines_idx= [i for i,line in enumerate(lines) if is_separator_line(line)]
    sep_lines_idx.append(len(lines))
    assert len(sep_lines_idx)>=1 # TODO: what if there are no VGs?
    vg_dicts={}
    for vg_i in range(len(sep_lines_idx) - 1):
        start_line= sep_lines_idx[vg_i] + 1
        end_line= sep_lines_idx[vg_i+1] 
        vg_lines= lines[start_line:end_line]
        assert 10 <= len(vg_lines) <= 30
        vg_tuples= map(parse_line, vg_lines)
        vg_tuples2= map(convert_line_tup, vg_tuples)
        vg_dict= dict(vg_tuples2)
        assert set(vg_dict) >= set(EXPECTED_KEYS)
        vg_name= vg_dict['VG Name']
        vg_dicts[vg_name]= vg_dict
    return vg_dicts

blockdevice.register_data_class("LVM2 PV", PV)
