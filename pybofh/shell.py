import subprocess

def check_call(command):
    run_process(command)

def check_output(command):
    return run_process(command)

def run_subprocess(command):
    result = subprocess.check_output(command)
    return result

