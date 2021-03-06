#!/usr/bin/env python

from os import path
from subprocess import Popen, PIPE
import errno
import glob
import logging.handlers
import optparse
import os
import signal
import sys
import time

class BootstrapException(Exception): pass
class TarException(BootstrapException): pass
class PBuildException(BootstrapException): pass
class CBuildException(BootstrapException): pass
class PackageInstallException(BootstrapException): pass
class DException(BootstrapException): pass

def call(*popenargs, **kwargs):
        log.info("Calling %s" % (popenargs))
        if "shell" not in kwargs:
                kwargs["shell"] = True
        process = Popen(*popenargs, **kwargs)
        process.wait()
        return process.returncode

def installPython(base, check, commands):
        global rpath 
        
        log.info("Installing %s", base)

        try:
                exec("import " + check)
                log.info("%s already installed, checked with 'import %s'", base, check)
                return
        except ImportError:
                pass
    
        extractDistribution(base, '/tmp')
        
        distDir = glob.glob(os.path.join("/tmp", base+'*'))[0] # Need glob as os.chdir doesn't expand
        log.info("Changing directory to %s" %(distDir))
        os.chdir(distDir)
        
        if call("python setup.py %s -f" % commands):
                log.error("Failed to install %s with commands %s", base, commands)
                raise PBuildException("Unable to install %s with commands %s" %(base, commands))
            
        log.info("Successfully installed %s", base)

def installC(base, check):
        global rpath
        
        log.info("Installing %s", base)
        
        if os.path.exists(check):
                log.info("%s already installed, found file %s", base, check)
                return

        extractDistribution(base, '/tmp')
        
        distDir = glob.glob(os.path.join("/tmp", base+'*'))[0] # Need glob as os.chdir doesn't expand
        log.info("Changing directory to %s" %(distDir))
        os.chdir(distDir)
        
        if call("./configure") or call("make") or call("make install"):
                log.error("Failed to install %s", base)
                raise CBuildException("Unable to install %s" % base)
            
        log.info("Successfully installed %s", base)

def installPreBuilt(base):
    global rpath
    
    log.info("Installing %s", base)
    
    extractDistribution(base, '/tmp')
            
    distDir = glob.glob(os.path.join("/tmp", base+'*'))[0] # Need glob as os.chdir doesn't expand
    log.info("Changing directory to %s" %(distDir))
    os.chdir(distDir)
    
    if call("sudo rsync bin/* /usr/local/bin/"):
            log.error("Failed to install %s", base)
            raise CBuildException("Unable to install %s" % base)
        
    log.info("Successfully installed %s", base)
        
def extractDistribution(base, destDir):
    global rpath
    log.info("Extracting %s to %s" %(base, destDir))
    
    paths = [os.path.join(rpath, 'tarfiles', '%s*' %(base)), os.path.join(rpath, '%s*' %(base))]
    fail = False
    for path in paths:
            if call("tar -C %s -xzf %s" % (destDir, path)):
                    fail = True
            else:
                    fail = False
                    break

    if fail:
            raise TarException("Failed to untar %s" % base)
    
    log.info("Successfully extracted %s to %s" %(base, destDir))
    
def isInstalled(program):
        try:
                import subprocess
                subprocess.call(program, stdout=open('/dev/null', 'w'), stderr=subprocess.STDOUT)
                return True
        except:
                return False

def installPackage(yum_pkg_name, apt_pkg_name):
    if isInstalled('yum'):
        log.info("Installing package %s", yum_pkg_name)
        if call("yum install -y %s", yum_pkg_name):
            log.error("Failed to install %s", yum_pkg_name)
            raise PackageInstallException("Unable to install %s" %yum_pkg_name)
        log.info("Successfully installed %s", yum_pkg_name)
    elif isInstalled('apt-get'):
        log.info("Installing package %s", apt_pkg_name)
        if call("apt-get -qq install -y %s" % apt_pkg_name):
            log.error("Failed to install %s", apt_pkg_name)
            raise PackageInstallException("Unable to install %s" %apt_pkg_name)
        log.info("Successfully installed %s", apt_pkg_name)
    
def verifyPythonDevel():
        import distutils.sysconfig as c
        if not os.path.exists(os.path.join(c.get_python_inc(), 'Python.h')):
                try:
                    installPackage(yum_pkg_name="python-devel", apt_pkg_name="python-dev")
                except:
                    pass
        if not os.path.exists(os.path.join(c.get_python_inc(), 'Python.h')):
                log.error("Python development not installed, nor can we use the local package manager to do so")
                
def is_os_64bit():
        import platform
        return platform.machine().endswith('64')

def is_running(pid):        
    try:
        os.kill(pid, 0)
    except OSError as err:
        if err.errno == errno.ESRCH:
            return False
    return True

if __name__ == '__main__':
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        global rpath 
        
        optparser = optparse.OptionParser(description="Bootstrap script that can be used to install, configure, and start MAGI")
        optparser.add_option("-p", "--distpath", dest="rpath", default="/share/magi/current", help="Location of the distribution") 
        optparser.add_option("-U", "--noupdate", dest="noupdate", action="store_true", default=False, help="Do not update the system before installing Magi")
        optparser.add_option("-N", "--noinstall", dest="noinstall", action="store_true", default=False, help="Do not install magi and the supporting libraries") 
        optparser.add_option("-v", "--verbose", dest="verbose", action="store_true", default=False, help="Include debugging information") 
        optparser.add_option("-e", "--expconf", dest="expconf", action="store", default=None, help="Path to the experiment wide configuration file")  
        optparser.add_option("-c", "--nodeconf", dest="nodeconf", action="store", default=None, help="Path to the node specific configuration file. Cannot use along with -f (see below)")
        optparser.add_option("-n", "--nodedir", dest="nodedir", default="/var/log/magi", help="Directory to put MAGI daemon specific files") 
        optparser.add_option("-f", "--force", dest="force", action="store_true", default=False, help="Recreate node configuration file, even if present. Cannot use along with -c (see above)")
        optparser.add_option("-D", "--nodataman", dest="nodataman", action="store_true", default=False, help="Do not install and setup data manager") 
        optparser.add_option("-o", "--logfile", dest="logfile", action='store', default="/tmp/magi_bootstrap.log", help="Log file. Default: %default")
                
        (options, args) = optparser.parse_args()

        if options.nodeconf and options.force == True:
                optparser.error("Options -c and -f are mutually exclusive. Please specify only one")
                
        log_format = '%(asctime)s.%(msecs)03d %(name)-12s %(levelname)-8s %(message)s'
        log_datefmt = '%m-%d %H:%M:%S'
        
        # Check if log exists and should therefore be rolled
        # Need to check existence of file before creating the handler instance
        # This is because handler creation creates the file if not existent 
        needRoll = False
        if path.isfile(options.logfile):
            needRoll = True
        
        handler = logging.handlers.RotatingFileHandler(options.logfile, backupCount=5)
        handler.setFormatter(logging.Formatter('%(asctime)s.%(msecs)03d %(name)-12s %(levelname)-8s %(message)s'))
        
        if needRoll:
            handler.doRollover()
            
        log = logging.getLogger()
        log.setLevel(logging.INFO)
        log.addHandler(handler)

        rpath = options.rpath 

        if (sys.version_info[0] == 2) and (sys.version_info[1] < 5):
                sys.exit("Only works with python 2.5 or greater")

        try:
            
            if (not options.noupdate) and (not options.noinstall):  # double negative
                    if isInstalled('yum'):
                            call("yum update")
                    elif isInstalled('apt-get'):
                            call("apt-get -y update")
                    else:
                            msg = 'I do not know how to update this system. Platform not supported. Run with --noupdate or on a supported platform (yum or apt-get enabled).'
                            log.critical(msg)
                            sys.exit(msg)  # write msg and exit with status 1
                                    
            verifyPythonDevel()
    
            if not options.noinstall:                 
                    try:
                            installC('yaml', '/usr/local/lib/libyaml.so')
                            import yaml 
                    except:
                            log.info("unable to install libyaml, will using pure python version: %s", sys.exc_info()[1])
    
                    try:
                            installPython('PyYAML', 'yaml', 'install')
                    except PBuildException:
                            installPython('PyYAML', 'yaml', '--without-libyaml install')  # try without libyaml if build error
            
                    installPython('unittest2', 'unittest2', 'install')
                    installPython('networkx', 'networkx', 'install')
                    #installPython('SQLAlchemy', 'sqlalchemy', 'install')
                    magidist = 'MAGI-1.6.0'
                    installPython(magidist, 'alwaysinstall', 'install')
                    
                    installPackage(yum_pkg_name="python-setuptools", apt_pkg_name="python-setuptools")
                    installPython('pymongo', 'pymongo', 'install')
                    
                    #updating sys.path with the installed packages
                    import site
                    site.main()
    
            # Now that MAGI is installed on the local node, import utilities 
            from magi import __version__
            from magi.util import config, helpers
            
            try:
                # 7/24/2014 The messaging overlay and the database configuration is now explicitly defined
                # in an experiment wide configuration file. The experiment wide configuration file format 
                # is documented in magi/util/config.py. The experiment wide configuration file contains the messaging 
                # overlay configuration and the database configuration.
                # 
                # In the absence of messaging overlay configuration, the bootstrap process defines a simple messaging 
                # overlay that starts two servers; one externally facing for the experimenter to connect to the experiment
                # and one internally facing to forward magi messages to all the experiment nodes. 
                # The node that hosts both the servers is chosen as follows:
                #    - it checks to see if a node named "control" is present in the experiment 
                #      If present, it is chosen 
                #   -  else, the first node in an alpha-numerically sorted  
                #      list of all node names is used  
                #
                # In the absence of database configuration, the bootstrap process defines a simple configuration, with
                # each sensor collecting data locally. The database config node is also chosen using the above steps.
                # 
                
                config.setNodeDir(options.nodedir)
                
                log.info("Checking to see if a experiment configuration is provided")
                if not options.expconf:
                        log.info("MAGI experiment configuration file has not been provided as an input argument")
                        log.info("Testing to see if one is present")
                        
                        createExperimentConfig = False 
                        
                        # Create a MAGI experiment configuration file if one is not present or needs to be recreated 
                        if options.force == True:
                                log.info("force flag set. Need to (re)create node configuration file.")  
                                createExperimentConfig  = True
                        else:
                            experimentConfigFile = config.getExperimentConfFile()
                            if os.path.exists(experimentConfigFile):
                                    log.info("Found an experiment configuration file at %s. Using it.", experimentConfigFile) 
                                    experimentConfig = config.loadExperimentConfig(experimentConfig=experimentConfigFile, 
                                                                                   distributionPath=rpath, 
                                                                                   isDBEnabled=not options.nodataman)
                            else:
                                    # Experiment configuration file does not exist
                                    log.info("No valid experiment configuration file found at %s. Need to create one.", experimentConfigFile)
                                    createExperimentConfig = True 

                        if createExperimentConfig: 
                                log.info("Creating a new experiment configuration file")
                                experimentConfig = config.createExperimentConfig(distributionPath=rpath, isDBEnabled=not options.nodataman)
                                
                else:
                        log.info("Using experiment configuration file at %s", options.expconf)
                        experimentConfig = config.loadExperimentConfig(options.expconf, distributionPath=rpath, isDBEnabled=not options.nodataman)
                                                
                # create a MAGI node configuration file only if one is not explicitly specified 
                if not options.nodeconf:
                        log.info("MAGI node configuration file has not been provided as an input argument")
                        log.info("Testing to see if one is present")
                        
                        createNodeConfig = False 
                        # Create a MAGI node configuration file if one is not present or needs to be recreated 
                        if options.force == True:
                                log.info("force flag set. Need to (re)create node configuration file.")  
                                createNodeConfig  = True
                        elif os.path.exists(config.getNodeConfFile()):
                                log.info("Found a node configuration file at %s. Using it.", config.getNodeConfFile()) 
                                nodeConfig = config.loadNodeConfig(nodeConfig=config.getNodeConfFile(), experimentConfig=experimentConfig) 
                        else:
                                # Node configuration file does not exist
                                log.info("No valid node configuration file found at %s. Need to create one.", config.getNodeConfFile())
                                createNodeConfig = True 

                        if createNodeConfig: 
                                log.info("Creating a new node configuration file")
                                # Use the experiment configuration to create node specific configuration
                                nodeConfig = config.createNodeConfig(experimentConfig=experimentConfig) 
                
                else:
                        log.info("Using node configuration file at %s", options.nodeconf)
                        nodeConfig = config.loadNodeConfig(nodeConfig=options.nodeconf, experimentConfig=experimentConfig) 
                        
                helpers.makeDir(os.path.dirname(config.getNodeConfFile()))
                helpers.writeYaml(nodeConfig, config.getNodeConfFile())
                log.info("Created a node configuration file at %s", config.getNodeConfFile())
                
                helpers.makeDir(os.path.dirname(config.getExperimentConfFile()))
                helpers.writeYaml(experimentConfig, config.getExperimentConfFile())
                log.info("Created a experiment configuration file at %s", config.getExperimentConfFile()) 
            
            except:
                    log.exception("MAGI configuration failed, things probably aren't going to run")
                                
            if (config.getNodeName() == config.getServer()):
                import shutil
                log.info("Copying experiment.conf to testbed experiment directory %s" %(config.getExperimentDir()))
                shutil.copy(config.getExperimentConfFile(), config.getExperimentDir())
                                        
            # Now that the system is configured, import database library
            from magi.util import database
            
            if database.isDBEnabled:
                    if (database.isCollector or database.isConfigHost):
                            if not options.noinstall:
                                    #installPackage('mongodb', 'mongodb') #Package installer starts mongodb with default configuration
                                    #Copying prebuilt binaries for mongodb
                                    if is_os_64bit():
                                            installPreBuilt('mongodb-linux-x86_64')
                                    else:
                                            installPreBuilt('mongodb-linux-i686')
                    else:
                            log.info("Database server is not required on this node")
                            
            else:
                log.info("Database setup is disabled")
                    
            # Get the pid for the daemon process from the pid file 
            # Note that if the daemon was started externally, without bootstrap, the pid file would not have 
            # the correct pid 
            # Note the magi_daemon.py does record the pid correctly in /var/log/mgi/magi.pid 
            # TODO: walk the /proc directory, check the /proc/pid/status. get the name and kill process if name is magi_daemon.py 
           
            # currenty, check if the magi.pid file exsist, if exists, try to kill  
            # Note the file is created by the magi_daemon.py script  
            magiPidFile =  config.getMagiPidFile()
            log.info("Testing to see if a MAGI Daemon process is already running (pid at %s)", magiPidFile)
            if os.path.exists(magiPidFile) and os.path.getsize(magiPidFile) > 0:
                    fpid = open (magiPidFile, 'r')
                    pid = int(fpid.read())
                    
                    log.info("Daemon is running with pid %d", pid)
                    log.info("Trying to stop daemon gracefully. Sending SIGTERM.")
                    try:
                            os.kill(pid, signal.SIGTERM)
                    except OSError, e:
                            if e.args[0] == errno.ESRCH:
                                    log.info("No process %d found", pid)
                            else:
                                    log.info("Cannot kill process %d", pid) 
                    
                    terminated = False
                    
                    #wait for daemon to terminate
                    for i in range(10):
                        if is_running(pid):
                            time.sleep(0.5)
                        else:
                            log.info("Process %d terminated successfully", pid)
                            terminated = True 
                            break
                    
                    if not terminated:
                        log.info("Could not stop daemon gracefully. Sending SIGKILL.")
                        try:
                                os.kill(pid, signal.SIGKILL)
                        except OSError, e:
                                if e.args[0] == errno.ESRCH:
                                        log.info("No process %d found", pid)
                                else:
                                        log.info("Cannot kill process %d", pid) 
                    
                    #wait for daemon to die
                    for i in range(10):
                        if is_running(pid):
                            time.sleep(0.5)
                        else:
                            log.info("Process %d killed successfully", pid)
                            terminated = True 
                            break
                        
                    if not terminated:
                        log.error("Could not stop already running daemon process. "
                                  "Another one might not start successfully. "
                                  "Still trying.")
                        
            else:
                    log.info("No %s file found", magiPidFile)
    
            log.info("Starting daemon")
            daemon = ['/usr/local/bin/magi_daemon.py']
            daemon += ['--nodeconf', config.getNodeConfFile()]
    
            if options.verbose:
                    log.info("Starting daemon with debugging")
                    daemon += ['-l', 'DEBUG']
                    
            log.info(daemon)
            
            pid = Popen(daemon, stdout=PIPE, stderr=PIPE).pid
     
            log.info("MAGI Version: %s", __version__) 
            log.info("Started daemon with pid %s", pid)
        
        except Exception, e:
            log.exception("Exception while bootstraping")
            sys.exit(e)
