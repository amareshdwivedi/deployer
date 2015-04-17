import os
import sys
import struct
from setuptools.command import easy_install
import subprocess

install_dir=sys.argv[1]
log_file=sys.argv[2]
libs=['web.py-0.37.tar.gz','colorama-0.3.2.tar.gz','pycrypto-2.6.1.tar.gz','ecdsa-0.11.tar.gz','paramiko-1.15.1.tar.gz','prettytable-0.7.2.tar.gz','six-1.8.0.tar.gz','requests-2.4.3.tar.gz','pyvmomi-5.5.0.2014.1.1.tar.gz','Pillow-2.6.1.tar.gz','reportlab-3.1.8.tar.gz','service_toolkit-1.0.0-py2.7.egg','LEPL-5.1.3.tar.gz']
lib_path=os.path.abspath(os.path.dirname(__file__))+os.path.sep+".."+os.path.sep +"libs"+os.path.sep

if not os.path.exists(install_dir):
    os.makedirs(install_dir)
os.environ["PYTHONPATH"] = install_dir


if sys.platform.startswith("linux") :
   infi_pkgs=['sentinels-0.0.6.tar.gz','pyforge-1.2.0.tar.gz', 'infi.monotonic_time-0.1.5.tar.gz','mock-1.0.1.tar.gz',
               'emport-1.0.0.tar.gz','infi.execute-0.1.tar.gz','infi.pyutils-1.0.8.tar.gz','infi.run_as_root-0.1.4.tar.gz','munch-2.0.2.tar.gz','infi.execute-0.1.tar.gz','infi.pkgmgr-0.1.8.tar.gz']
   for infi_pkg in  infi_pkgs:
        easy_install.main(["-Z", "--install-dir", install_dir, lib_path + infi_pkg])
   with open(log_file, "a") as output:
        install_linux_dependencies=os.path.abspath(os.path.dirname(__file__))+os.path.sep+'install_linux_dependencies.py'
        subprocess.call(["python",install_linux_dependencies],stdout=output,stderr=output);

for lib in libs:
    if "Pillow" in lib:
        if sys.platform == "win32" or sys.platform == "win64":
            if (8 * struct.calcsize("P")) == 32:  # for 32bit python compiler 
                easy_install.main(["-Z", "--install-dir", install_dir, lib_path + 'Pillow-2.6.1-py2.7-win32.egg'])
            elif (8 * struct.calcsize("P")) == 64:  # for 64bit python compiler
                easy_install.main(["-Z", "--install-dir", install_dir, lib_path + 'Pillow-2.6.1-py2.7-win-amd64.egg'])
        else:
            easy_install.main(["-Z", "--install-dir", install_dir, lib_path + lib])
    elif "pycrypto" in lib:
        if sys.platform == "win32" or sys.platform == "win64":
            if (8 * struct.calcsize("P")) == 32:  # for 32bit python compiler 
                easy_install.main(["-Z", "--install-dir", install_dir, lib_path + 'pycrypto-2.6.win32-py2.7.exe'])
            elif (8 * struct.calcsize("P")) == 64:  # for 64bit python compiler
                easy_install.main(["-Z", "--install-dir", install_dir, lib_path + 'pycrypto-2.6.win-amd64-py2.7.exe'])
        else:
            easy_install.main(["-Z", "--install-dir", install_dir, lib_path + lib])            
    else :
        easy_install.main(["-Z", "--install-dir", install_dir, lib_path + lib])

