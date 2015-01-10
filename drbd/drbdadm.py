import subprocess

def attach(resource, options=""):
    subprocess.check_call("drbdadm attach {options} {resource}".format(**locals()), shell=True)

def detach(resource, options=""):
    subprocess.check_call("drbdadm detach {options} {resource}".format(**locals()), shell=True)

def connect(resource, options=""):
    subprocess.check_call("drbdadm connect {options} {resource}".format(**locals()), shell=True)

def disconnect(resource, options=""):
    subprocess.check_call("drbdadm disconnect {options} {resource}".format(**locals()), shell=True)

def up(resource, options=""):
    subprocess.check_call("drbdadm up {options} {resource}".format(**locals()), shell=True)

def down(resource, options=""):
    subprocess.check_call("drbdadm down {options} {resource}".format(**locals()), shell=True)

def primary(resource, options=""):
    subprocess.check_call("drbdadm primary {options} {resource}".format(**locals()), shell=True)

def secondary(resource, options=""):
    subprocess.check_call("drbdadm secondary {options} {resource}".format(**locals()), shell=True)

def invalidate(resource, options=""):
    subprocess.check_call("drbdadm invalidate {options} {resource}".format(**locals()), shell=True)

def invalidate_remote(resource, options=""):
    subprocess.check_call("drbdadm invalidate-remote {options} {resource}".format(**locals()), shell=True)

def create_md(resource, options=""):
    subprocess.check_call("drbdadm create-md {options} {resource}".format(**locals()), shell=True)

def adjust(resource, options=""):
    subprocess.check_call("drbdadm adjust {options} {resource}".format(**locals()), shell=True)

def role(resource, options=""):
    out= subprocess.check_output("drbdadm role {options} {resource}".format(**locals()), shell=True).splitlines()
    assert len(out)==1
    out=out[0]
    roles= out.split("/")
    assert len(roles)==2
    return roles

def cstate(resource, options=""):
    out= subprocess.check_output("drbdadm cstate {options} {resource}".format(**locals()), shell=True).splitlines()
    assert len(out)==1
    out=out[0]
    return out

def dstate(resource, options=""):
    out= subprocess.check_output("drbdadm dstate {options} {resource}".format(**locals()), shell=True).splitlines()
    assert len(out)==1
    out=out[0]
    states= out.split("/")
    assert len(states)==2
    return states

def verify(resource, options=""):
    subprocess.check_call("drbdadm verify {options} {resource}".format(**locals()), shell=True)

def pause_sync(resource, options=""):
    subprocess.check_call("drbdadm pause-sync {options} {resource}".format(**locals()), shell=True)

def resume_sync(resource, options=""):
    subprocess.check_call("drbdadm resume-sync {options} {resource}".format(**locals()), shell=True)
