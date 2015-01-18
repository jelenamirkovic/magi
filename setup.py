#!/usr/bin/env python

from distutils.cmd import Command
from distutils.command.build_py import build_py
from distutils.core import setup
from magi import __version__, __author__
import os
import subprocess

# these are defined in ./magi/__init__.py as magi module variables. 

class ToShare(Command):
    user_options = [('path=', 'p', 'directory to place files'), ('static=','s','location of static source and tar file')]
    def initialize_options(self):
        # print __version__ 
        # Generate the default path from the version string 
        vpath = "v" + ''.join(__version__.split('.')[:3])
        self.path = os.path.join('/share/magi/',vpath)
        self.static = '/share/magi/tarfiles'
        
    def finalize_options(self):
        # check if a directory exists at the path, if not create one 
        if os.path.isdir(self.path) is not True:
            try:
                os.makedirs(self.path)
                print "Creating a distribution at ", self.path
            except OSError:
                print "Error in setup script" 
                raise
        else:
            print "Overwriting Distribution at  ", self.path
            
    def linksrcs(self):
        # link the static sources located at /share/magi/tarfiles. 
        # Typically ['source', 'yaml-0.1.3.tar.gz', 'unittest2-0.5.1.tar.gz', 'SQLAlchemy-0.7.6.tar.gz', 'PyYAML-3.10.tar.gz']
        
        if os.path.exists(self.static):
            os.symlink(os.path.join(self.static),os.path.join(self.path, 'tarfiles'))
            os.symlink(os.path.join(self.static, 'source'),os.path.join(self.path, 'source'))
            print "Created a link to static files in ", self.path
        else:
            print "Cannot find the static files at ", self.static 
            
    def run(self):
        self.call("cp dist/MAGI*gz %s" % self.path)
        self.call("cp tools/helpers.py %s" % self.path)
        self.call("cp tools/magi_bootstrap.py %s" % self.path)
        self.call("cp tools/magi_orchestrator.py %s" % self.path)
        self.call("cp tools/magi_status.py %s" % self.path)
        self.call("cp tools/magi_graph.py %s" % self.path)
        self.call("cp scripts/magi_query.py %s" % self.path)
        self.call("cp AUTHORS %s" % self.path) 
        self.call("cp GPLv3-LICENSE.txt %s" % self.path)
        
        # Not sure why a copy of the source code is required in the distribution 
        # Let it stay for now 
        # self.call("cp -R . %s/backend" % self.path)
        #self.call("ln -s %s/backend/magi %s" % (self.path, self.path))
        self.linksrcs()
        
    def call(self, cmd):
        print "Running ", cmd
        subprocess.call(cmd, shell=True)
        
class build_py_X(build_py):
    def find_data_files (self, package, src_dir):
        ret = build_py.find_data_files(self, package, src_dir)
        return ret
    
#try:
    #os.unlink('MANIFEST') # remove autogenerated thing by sdist
#except:
#	pass

setup(name='MAGI',
	version=__version__,
	description='Montage AGent Infrastructure',
	long_description='A framework for deploying and orchestrating experimentation agents in networking and cybersecurity testbeds',
	url='http://montage.deterlab.net/backend', 
	author=__author__,
	author_email='hussain@isi.edu', 
	download_url='git://montage.deterlab.net/magi',
	platforms=['DeterLab', 'Emulab'], 
	packages=['magi', 'magi.daemon', 'magi.messaging', 'magi.testbed', 'magi.db', 'magi.modules', 
              'magi.util', 'magi.orchestrator', 'magi.tests', 'magi.modules.dataman'],
	package_data={'magi.modules.dataman': ['*.idl'], 'magi.tests': ['*.pem', '*.aal', '*/*']},
	scripts=['scripts/magi_daemon.py', 'tools/magi_orchestrator.py', 'tools/magi_status.py', 'tools/magi_graph.py' ],
	license="GPLV3",
	cmdclass={'toshare':ToShare, 'build_py':build_py_X},
)


