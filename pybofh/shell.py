import subprocess
import logging

log = logging.getLogger(__name__)

def check_call(command):
    run_process(command)

def check_output(command):
    return run_process(command)

def run_process(command):
    logging.debug("Running command: %s", lambda: "".join(command))
    result = subprocess.check_output(command)
    return result

