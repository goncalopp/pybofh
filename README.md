pybofh
======

A Linux system administration automation toolset.

Abstracts common CLIs into python functions and classes.

Current command modules:
 - blockdevice
 - btrfs
 - encryption (cryptsetup)
 - drbd
 - lvm
 - xen

Example
-------

Start all Xen DomUs

    from pybofh import xen

    for domu in xen.allDomus():
        if not xen.isDomuRunning(domu):
            xen.startDomu( domu )


Features
========

Site-specific configuration
---------------------------

Customize `site_specific.py` to match your local environment

Atomic operations
-----------------

Having a automated administration tool that leaves a talk half-finished is worse than having no automated administration tool.

`pybofh` supports context managers:


    TMP_MNTS= ["/media/tmp", "/media/tmp2"]
    mountpool= blockdevice.MountPool( TMP_MNTS )
    with mountpool.mount( '/dev/sda1' ) as sda1_mountpoint:
        #/dev/sda1 is now mounted
        with mountpoint.mount( '/dev/sda2') as sda2_mountpoint:
            #/dev/sda2 is now mounted
            with mountpoint.mount( '/dev/sda3') as sda3_mountpoint:
                #fails, no more mountpoints available
                pass
     #/dev/sda1 and /dev/sda2 are now unmounted
     
But, of course, not all operations make sense as a context manager. Take, for example, creating a new VM from disk on LVM:

    lvm.createLV("my_vg", "my_vm", "10gb")
    blockdevice.create_filesystem( '/dev/my_vg/my_vm')
    #...

What happens if `create_filesystem` fails? You'll may be left with a inconsistent filesystem on the LV. Worse, once you fix the problem and try to run this again, `createLV` will fail, because the LV is already there, so you'll have to either create the VM manually or fix your script.

A context manager makes no sense in this case: you don't want to delete the LV if all operations succeed. You have to keep track of the operations you performed, and rollback if something fails. You could do that by hand, of course, but that's no fun:

    with Atomic() as atomic:
        atomic.lvm.createLV("my_vg", "my_vm", "10gb")
        blockdevice.create_filesystem( '/dev/my_vg/my_vm')

Now, the LV will be deleted only *if **any** operation inside the context manager fails*. If you have multiple `atomic` calls, it will keep track of them, and rollback them in the reverse order they were executed on. 

While `Atomic` pre-packages some knowledge, `AtomicOperationSequence` is operation agnostic - it works by defining rollback functions:

    def f1():
        print "f1 executed"
    
    def reverse(f, args, kwargs):
         if f==f1:
             print "f1 reversed"
    
    with AtomicOperationSequence(reverse) as atomic:
        atomic.f1()

FAQ
===

pybofh? What kind of name is that?
----------------------------------
It's a tribute to the [Bastard Operator From Hell](http://en.wikipedia.org/wiki/Bastard_Operator_From_Hell) stories

Where does development happen?
------------------------------
https://github.com/goncalopp/pybofh
