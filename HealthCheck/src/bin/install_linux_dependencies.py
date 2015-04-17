import platform

pkgmgr= None
dependencies=None
linuxflavor=platform.dist()[0]
if linuxflavor.lower() == 'centos' or  linuxflavor.lower() == 'redhat' or linuxflavor.lower() == 'fedora':
        from infi.pkgmgr import RedHatPackageManager
        pkgmgr = RedHatPackageManager()
        dependencies=['gcc','python-devel','zlib-devel','freetype','freetype-devel','libjpeg-devel']
elif linuxflavor.lower() == 'ubuntu':
        from infi.pkgmgr import UbuntuPackageManager
        pkgmgr = UbuntuPackageManager()
        dependencies=['gcc','build-essential','libfreetype6-dev','python-dev','python-imaging']

for name in dependencies :
        print "Installing "+ name
        pkgmgr.install_package(name)
        print name+ "Installation finished"
