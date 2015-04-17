import os
import time
import subprocess
import threading
import sys
import shutil
import platform

if sys.version_info[0] != 2 or sys.version_info[1] < 7:
    print "You are running python version - " + platform.python_version()
    print "Please un-install this version and install version 2.7." 
    print "Once version 2.7 in installed, unzip the installation zip to a new folder and run the installation again."
    sys.exit(1)

current_directory = os.getcwd()    
os.chdir(current_directory + os.path.sep +'scripts'+ os.path.sep)
cmd = 'python get_pip.py'
p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
out, err = p.communicate()

from distutils.sysconfig import get_python_lib;
default_install = get_python_lib()

if not os.path.exists(default_install):
    print "Installation directory does not exists"
    exit()
else :
    shutil.rmtree(default_install + os.path.sep + "service_toolkit", ignore_errors=True)
    default_install+=os.path.sep+'service_toolkit'
    os.makedirs(default_install)    

returncode = 0
print "Starting Nutanix Service Toolkit Installation..."
depInstalled = 0
def progress_bar():
    for i in range(21):
        sys.stdout.write('\r')
        sys.stdout.write("[%-20s] %d%%" % ('#'*i, 5*i))
        sys.stdout.flush()
        time.sleep(0.40)
    sys.stdout.write('\r')
        
def installing_dependencies():
    try:
        log_file = current_directory + os.path.sep + "install_log.log"
        with open(log_file, "w+") as output:
            install_helper="install_helper.py"
            subprocess.check_call(["python", install_helper,default_install,log_file],stderr=output,stdout=output);
    except subprocess.CalledProcessError as cpe:
        global returncode
        returncode = cpe.returncode
        
threads = []
thread_installing_dep = threading.Thread(target=installing_dependencies)
thread_progress_bar = threading.Thread(target=progress_bar)
thread_progress_bar.start()
thread_installing_dep.start()
threads.append(thread_progress_bar)
threads.append(thread_installing_dep)
for t in threads:
    t.join()

if returncode == 0:
    
    print "Creating healthcheck script..."

    healthchecklines=["#!"+sys.executable+"\n" if sys.platform.startswith("linux") else '','import os,sys',
    'lib_path = ' + "'" + default_install + "'",
    'os.environ["PYTHONPATH"] = lib_path',
    'if not os.path.exists(os.getcwd() + os.path.sep +"reports"):',
    '     os.mkdir("reports")',
    'executable_path="python "+lib_path+os.path.sep+"service_toolkit-1.0.0-py2.7.egg"+os.path.sep+"src"+os.path.sep+"health_check.pyc "',
    'os.system(executable_path+ " ".join(sys.argv[1:]))']

    health_check_pyfile=open(default_install+os.path.sep+"healthcheck.py","wb")
    for line in healthchecklines:
        health_check_pyfile.writelines(line+"\n")
    health_check_pyfile.close()
    time.sleep(2)

    print "Creating webhealthcheck script..."

    webhealthchecklines=["#!"+sys.executable+"\n" if sys.platform.startswith("linux") else '','import os,sys',
    'lib_path = ' + "'" + default_install + "'",
    'os.environ["PYTHONPATH"] = lib_path',
    'cur_dir = os.getcwd()',
    'if not os.path.exists(cur_dir + os.path.sep +"reports"):',
    '     os.mkdir("reports")',
    'os.chdir(lib_path+os.path.sep+"service_toolkit-1.0.0-py2.7.egg"+os.path.sep+"src"+os.path.sep)',
    'executable_path="python web_health_check.pyc 127.0.0.1:8080 " + cur_dir',
    'os.system(executable_path)']

    web_health_check_pyfile=open(default_install+os.path.sep+"webhealthcheck.py","wb")
    for line in webhealthchecklines:
        web_health_check_pyfile.writelines(line+"\n")
    web_health_check_pyfile.close()
    time.sleep(2)

    print "Creating IaaSProvisioning script..."

    iaasProvisioning_lines=["#!"+sys.executable+"\n" if sys.platform.startswith("linux") else '','import os,sys',
    'lib_path = ' + "'" + default_install + "'",
    'os.environ["PYTHONPATH"] = lib_path',
    'if not os.path.exists(os.getcwd() + os.path.sep +"reports"):',
    '     os.mkdir("reports")',
    'executable_path="python "+lib_path+os.path.sep+"service_toolkit-1.0.0-py2.7.egg"+os.path.sep+"src"+os.path.sep+"iaasProvisioning.pyc "',
    'os.system(executable_path+sys.argv[1]+" \'"+sys.argv[2]+"\'")']

    provisioning_pyfile=open(default_install+os.path.sep+"iaasProvisioning.py","wb")
    for line in iaasProvisioning_lines:
        provisioning_pyfile.writelines(line+"\n")
    provisioning_pyfile.close()
    time.sleep(2)

    print "Creating DPaaSProvisioning script..."
    dpaasProvisioning_lines=["#!"+sys.executable+"\n" if sys.platform.startswith("linux") else '','import os,sys',
    'lib_path = ' + "'" + default_install + "'",
    'os.environ["PYTHONPATH"] = lib_path',
    'executable_path="python "+lib_path+os.path.sep+"service_toolkit-1.0.0-py2.7.egg"+os.path.sep+"src"+os.path.sep+"foundation"+os.path.sep+"DPaaSOperations.pyc "',
    'os.system(executable_path+" \'"+sys.argv[1]+"\'")']

    dpass_pyfile=open(default_install+os.path.sep+"dpaasProvisioning.py","wb")
    for line in dpaasProvisioning_lines:
        dpass_pyfile.writelines(line+"\n")
    dpass_pyfile.close()
    time.sleep(2)


    shutil.copy(default_install+os.path.sep+"healthcheck.py",current_directory)
    shutil.copy(default_install+os.path.sep+"webhealthcheck.py",current_directory)
    shutil.copy(default_install+os.path.sep+"iaasProvisioning.py",current_directory)
    shutil.copy(default_install+os.path.sep+"dpaasProvisioning.py",current_directory)


    if sys.platform.startswith("linux"):
        os.chmod(current_directory+os.path.sep+"healthcheck.py",0755)
        os.chmod(current_directory+os.path.sep+"webhealthcheck.py",0755)


    if sys.platform.startswith("win"):
        #add to system path
        print "Setting environment path variable..."
        subprocess.call(['setx','Path','%Path%;'+default_install])

    if sys.platform.startswith("linux"):
        shutil.copy(default_install+os.path.sep+"healthcheck.py","/bin/healthcheck.py")
        shutil.copy(default_install+os.path.sep+"webhealthcheck.py","/bin/webhealthcheck.py")
        os.chmod("/bin/healthcheck.py",0755)
        os.chmod("/bin/webhealthcheck.py",0755)
        

    print "Creating uninstall script..."

    uninstall_lines=["#!"+sys.executable+"\n" if sys.platform.startswith("linux") else '','import os,sys,shutil,time',
    'print "Starting HealthCheck Un-installation..."',                 
    'install_dir = ' + "'" + default_install + "'",                               
    'shutil.rmtree(install_dir, ignore_errors=True)',
    'os.remove(\'/bin/healthcheck.py\')' if sys.platform.startswith("linux") else '',
    'os.remove(\'/bin/webhealthcheck.py\')' if sys.platform.startswith("linux") else '',
    'time.sleep(2)',
    'print "Nutanix Service Toolkit Un-installation Successfull..."']

    uninstall_pyfile=open(default_install+os.path.sep+"uninstall.py","wb")
    for line in uninstall_lines:
        uninstall_pyfile.writelines(line+"\n")
    uninstall_pyfile.close()
    time.sleep(2)

    print "Nutanix Service Toolkit Installation Successfull..."

else:
    print "Exception occured during installation process..."
#    if sys.platform.startswith("win"):
#        print "Please Check if Microsoft Visual C++ Compiler for Python 2.7 is installed on your machine (Download from - http://aka.ms/vcpython27)" 
    print "Please refer install_log for details"        
