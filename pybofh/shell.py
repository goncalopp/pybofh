import subprocess

def check_call(command):
    subprocess.check_call(command)

def check_output(command):
    return subprocess.check_output(command)

