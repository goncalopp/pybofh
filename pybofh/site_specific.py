#his file contains site-specific values or functions with such knowledge

import os
from functools import partial
import drbd


#------DISKS-------------------------------------------------------------

def decrypted_path( encrypted_disk_path ):
    decrypted_name= os.path.basename(encrypted_disk_path )
    return "/dev/mapper/"+decrypted_name
