from pybofh import shell

DRBDADM = "/sbin/drbdadm"

def attach(resource, options=()):
    shell.get().check_call((DRBDADM, "attach") + options + (resource,))

def detach(resource, options=()):
    shell.get().check_call((DRBDADM, "detach") + options + (resource,))

def connect(resource, options=()):
    shell.get().check_call((DRBDADM, "connect") + options + (resource,))

def disconnect(resource, options=()):
    shell.get().check_call((DRBDADM, "disconnect") + options + (resource,))

def up(resource, options=()):
    shell.get().check_call((DRBDADM, "up") + options + (resource,))

def down(resource, options=()):
    shell.get().check_call((DRBDADM, "down") + options + (resource,))

def primary(resource, options=()):
    shell.get().check_call((DRBDADM, "primary") + options + (resource,))

def secondary(resource, options=()):
    shell.get().check_call((DRBDADM, "secondary") + options + (resource,))

def invalidate(resource, options=()):
    shell.get().check_call((DRBDADM, "invalidate") + options + (resource,))

def invalidate_remote(resource, options=()):
    shell.get().check_call((DRBDADM, "invalidate-remote") + options + (resource,))

def create_md(resource, options=()):
    shell.get().check_call((DRBDADM, "create-md") + options + (resource,))

def adjust(resource, options=()):
    shell.get().check_call((DRBDADM, "adjust") + options + (resource,))

def role(resource, options=()):
    out= shell.get().check_output((DRBDADM, "role") + options + (resource,))
    assert len(out)==1
    out=out[0]
    roles= out.split("/")
    assert len(roles)==2
    return roles

def cstate(resource, options=()):
    out= shell.get().check_output((DRBDADM, "cstate") + options + (resource,))
    assert len(out)==1
    out=out[0]
    return out

def dstate(resource, options=()):
    out= shell.get().check_output((DRBDADM, "dstate") + options + (resource,))
    assert len(out)==1
    out=out[0]
    states= out.split("/")
    assert len(states)==2
    return states

def verify(resource, options=()):
    shell.get().check_call((DRBDADM, "verify") + options + (resource,))

def pause_sync(resource, options=()):
    shell.get().check_call((DRBDADM, "pause-sync") + options + (resource,))

def resume_sync(resource, options=()):
    shell.get().check_call((DRBDADM, "resume-sync") + options + (resource,))
