import subprocess
import os
import shutil
import time
import sys

print "Creating Egg..."

os.chdir(".."+os.path.sep+".."+os.path.sep)

cmd = 'python setup_egg.py bdist_egg --exclude-source-files'
p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
out, err = p.communicate()

if err:
	print "Failed with error #errorlevel."
	sys.exit(0)

print "Removing Temporary Files..."

shutil.rmtree(os.getcwd()+os.path.sep+"build", ignore_errors=True)
shutil.rmtree(os.getcwd()+os.path.sep+"service_toolkit.egg-info", ignore_errors=True)
time.sleep(2)

print "Egg Created Successfully at: " + os.getcwd()+os.path.sep+"dist"