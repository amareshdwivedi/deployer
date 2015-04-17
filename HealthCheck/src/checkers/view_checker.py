from __future__ import division
from bdb import effective
__author__ = 'anand nevase'
from requests.exceptions import ConnectionError
import string
import warnings
from pyVim import connect
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import pyVmomi
from base_checker import *
from prettytable import PrettyTable
import sys
import fnmatch
import datetime
import getpass
from utility import Validate,Security,Logger
import utility
from colorama import Fore
import web
from web import form
import os
import re
import base64
import atexit

loggerObj = Logger()

file_name = os.path.basename(__file__)

def exit_with_message(message):
    print message
    sys.exit(1)

def collect_properties(service_instance, view_ref, obj_type, path_set=None,
                       include_mors=False):
    """
    Collect properties for managed objects from a view ref

    Check the vSphere API documentation for example on retrieving
    object properties:

        - http://goo.gl/erbFDz

    Args:
        si          (ServiceInstance): ServiceInstance connection
        view_ref (pyVmomi.vim.view.*): Starting point of inventory navigation
        obj_type      (pyVmomi.vim.*): Type of managed object
        path_set               (list): List of properties to retrieve
        include_mors           (bool): If True include the managed objects
                                       refs in the result

    Returns:
        A list of properties for the managed objects

    """
    collector = service_instance.content.propertyCollector

    # Create object specification to define the starting point of
    # inventory navigation
    obj_spec = pyVmomi.vmodl.query.PropertyCollector.ObjectSpec()
    obj_spec.obj = view_ref
    obj_spec.skip = True

    # Create a traversal specification to identify the path for collection
    traversal_spec = pyVmomi.vmodl.query.PropertyCollector.TraversalSpec()
    traversal_spec.name = 'traverseEntities'
    traversal_spec.path = 'view'
    traversal_spec.skip = False
    traversal_spec.type = view_ref.__class__
    obj_spec.selectSet = [traversal_spec]

    # Identify the properties to the retrieved
    property_spec = pyVmomi.vmodl.query.PropertyCollector.PropertySpec()
    property_spec.type = obj_type

    if not path_set:
        property_spec.all = True

    property_spec.pathSet = path_set

    # Add the object and property specification to the
    # property filter specification
    filter_spec = pyVmomi.vmodl.query.PropertyCollector.FilterSpec()
    filter_spec.objectSet = [obj_spec]
    filter_spec.propSet = [property_spec]

    # Retrieve properties
    props = collector.RetrieveContents([filter_spec])

    data = []
    for obj in props:
        properties = {}
        for prop in obj.propSet:
            properties[prop.name] = prop.val

        if include_mors:
            properties['obj'] = obj.obj

        data.append(properties)
    return data


def get_container_view(service_instance, obj_type, container=None):
    """
    Get a vSphere Container View reference to all objects of type 'obj_type'

    It is up to the caller to take care of destroying the View when no longer
    needed.

    Args:
        obj_type (list): A list of managed object types

    Returns:
        A container view ref to the discovered managed objects

    """
    if not container:
        container = service_instance.content.rootFolder

    view_ref = service_instance.content.viewManager.CreateContainerView(
        container=container,
        type=obj_type,
        recursive=True
    )
    return view_ref

def checkgroup(group_name, description, category,expected_result):
    def outer(func):
        def inner(*args, **kwargs):
            args[0].reporter.notify_progress(args[0].reporter.notify_checkName, description)
            return func(*args, **kwargs)
        inner.group = group_name
        inner.descr = description
        inner.category = category
        inner.expected_result = expected_result
        return inner
    return outer

class HorizonViewChecker(CheckerBase):

    _NAME_ = "view"

    def __init__(self):
        super(HorizonViewChecker, self).__init__(HorizonViewChecker._NAME_)
        
        if sys.platform.startswith("win") :
            self.config_form =  form.Form( 
                form.Textbox("Server",value=self.authconfig['view_ip']),
                form.Textbox("User",value=self.authconfig['view_user']),
                form.Password("Password",value=Security.decrypt(self.authconfig['view_pwd'])),
                form.Textbox("VC Server",value=self.authconfig['view_vc_ip']),
                form.Textbox("VC Port",value=self.authconfig['view_vc_port']),
                form.Textbox("VC User",value=self.authconfig['view_vc_user']),
                form.Password("VC Password",value=Security.decrypt(self.authconfig['view_vc_pwd'])))()
        else:
            '''VMware Horizon View Health Check works on windows only.
                config_form is set to None so that on WEB UI condition is check if it none, not supported OS message is shown
            '''
            self.config_form = None
            
        self.si = None
        self.categories=['performance','availability']
        self.category=None

    def get_name(self):
        return HorizonViewChecker._NAME_

    def get_desc(self):
        return "Performs Vmware Horizon View health checks"

    def configure(self, config, knowledge_pool, reporter):
        self.config = config
        self.knowledge_pool = knowledge_pool[self.get_name()]
        self.reporter = reporter
        self.authconfig=self.get_auth_config(self.get_name())
        CheckerBase.validate_config(self.authconfig, "view_ip")
        CheckerBase.validate_config(self.authconfig, "view_user")
        CheckerBase.validate_config(self.authconfig, "view_pwd")
        CheckerBase.validate_config(self.authconfig, "view_vc_ip")
        CheckerBase.validate_config(self.authconfig, "view_vc_user")
        CheckerBase.validate_config(self.authconfig, "view_vc_pwd")
        CheckerBase.validate_config(self.authconfig, "view_vc_port")

        checks_list = [k for k in config.keys() if k.endswith('checks')]
        #print checks_list
        for checks in checks_list:
            metrics = config[checks]
            if len(metrics) == 0:
                raise RuntimeError("At least one metric must be specified in "+ checks + "configuration file");

    def usage(self, message=None):
        x = PrettyTable(["Name", "Short help"])
        x.align["Name"] = "l"
        x.align["Short help"] = "l" # Left align city names
        x.padding_width = 1 # One space between column edges and contents (default)
        checks_list = [k for k in self.config.keys() if k.endswith('checks')]

        for checks in checks_list:
            x.add_row([checks,"Run "+checks])
        
        for category in self.categories:
            x.add_row([category,"Run "+category+' category'])
        x.add_row(["run_all", "Run all Horizon View checks"])
        x.add_row(["setup", "Set Vmware Horizon View Configuration"])
        message = message is None and str(x) or "\nERROR: "+ message + "\n\n" + str(x)
        exit_with_message(message)

    def setup(self):
        print "\nConfiguring VMware Horizon View Server:\n"
        
        if sys.platform.startswith("win") :
            current_vc_ip = self.authconfig['view_ip'] if ('view_ip' in self.authconfig.keys()) else "Not Set"
            vc_ip=raw_input("Enter VMware Horizon View Server IP [default: "+current_vc_ip+"]: ")
            vc_ip=vc_ip.strip()
            if vc_ip == "":
                if(current_vc_ip == "Not Set"):
                    loggerObj.LogMessage("error",file_name + " :: Error: Set VMware Horizon View Server IP.")
                    exit_with_message("Error: Set VMware Horizon View Server IP.")
                vc_ip=current_vc_ip
            
            if Validate.valid_ip(vc_ip) == False:
                loggerObj.LogMessage("error",file_name + " :: Error: Invalid VMware Horizon View Server IP address")
                exit_with_message("\nError: Invalid VMware Horizon View Server IP address")
                    
            current_vc_user=self.authconfig['view_user'] if ('view_user' in self.authconfig.keys()) else "Not Set"
            vc_user=raw_input("Enter VMware Horizon View Server User Name [default: "+current_vc_user+"]: ")
            vc_user=vc_user.strip()
            if vc_user == "":
                if(current_vc_user == "Not Set"):
                    loggerObj.LogMessage("error",file_name + " :: Error: Set VMware Horizon View Server User Name.")
                    exit_with_message("Error: Set VMware Horizon View Server User Name.")
                vc_user=current_vc_user
                
                
            current_pwd=self.authconfig['view_pwd'] if  ('view_pwd' in self.authconfig.keys()) else "Not Set"
            new_vc_pwd=getpass.getpass('Enter VMware Horizon View Server Password [Press enter to use previous password]: ')
            
            if new_vc_pwd == "":
                if(current_pwd == "Not Set"):
                    loggerObj.LogMessage("error",file_name + " :: Error: Set VMware Horizon View Server Password.")
                    exit_with_message("Error: Set VMware Horizon View Server Password.")
                vc_pwd = current_pwd
            else:
                confirm_pass=getpass.getpass('Re-Enter VMware Horizon View Server Password: ')
                if new_vc_pwd !=confirm_pass :
                    loggerObj.LogMessage("error",file_name + " :: Error: Password miss-match.")                    
                    exit_with_message("\nError: Password miss-match.Please run \"view setup\" command again")
                vc_pwd=Security.encrypt(new_vc_pwd)
           
            #Test Connection Status
            print "Checking VMware Horizon View Server Connection Status:",
             
    #         if not sys.platform.startswith("win"):
    #             exit_with_message("Plateform Not supported \n Windows system required to run VMware Horizon View Checks")
            status, message = self.check_connectivity(vc_ip, vc_user, vc_pwd)
            if status == True:
                print Fore.GREEN+" Connection successful"+Fore.RESET
            else:
               print Fore.RED+" Connection failure"+Fore.RESET
               exit_with_message(message)
    
            current_view_vc_ip = self.authconfig['view_vc_ip'] if ('view_vc_ip' in self.authconfig.keys()) else "Not Set"
            view_vc_ip=raw_input("Enter View vCenter Server IP [default: "+current_view_vc_ip+"]: ")
            view_vc_ip=view_vc_ip.strip()
            if view_vc_ip == "":
                if(current_view_vc_ip == "Not Set"):
                    loggerObj.LogMessage("error",file_name + " :: Error: Set View vCenter Server IP.")                    
                    exit_with_message("Error: Set View vCenter Server IP.")
                view_vc_ip=current_view_vc_ip
            
            if Validate.valid_ip(view_vc_ip) == False:
                loggerObj.LogMessage("error",file_name + " :: Error: Invalid View vCenter Server IP address.")                
                exit_with_message("\nError: Invalid View vCenter Server IP address.")
                    
            current_view_vc_user=self.authconfig['view_vc_user'] if ('view_vc_user' in self.authconfig.keys()) else "Not Set"
            view_vc_user=raw_input("Enter View vCenter Server User Name [default: "+current_view_vc_user+"]: ")
            view_vc_user=view_vc_user.strip()
            if view_vc_user == "":
                if(current_view_vc_user == "Not Set"):
                    loggerObj.LogMessage("error",file_name + " :: Error: Set View  vCenter Server User Name.")                    
                    exit_with_message("Error: Set View  vCenter Server User Name.")
                view_vc_user=current_view_vc_user
                
                
            view_current_pwd=self.authconfig['view_vc_pwd'] if  ('view_vc_pwd' in self.authconfig.keys()) else "Not Set"
            new__view_vc_pwd=getpass.getpass('Enter View vCenter Server Password [Press enter to use previous password]: ')
            
            if new__view_vc_pwd == "":
                if(view_current_pwd == "Not Set"):
                    loggerObj.LogMessage("error",file_name + " :: Error: Set View vCenter Server Password.")                                        
                    exit_with_message("Error: Set View vCenter Server Password.")
                new__view_vc_pwd = view_current_pwd
            else:
                confirm_pass=getpass.getpass('Re-Enter View vCenter Server Password: ')
                if new__view_vc_pwd !=confirm_pass :
                    loggerObj.LogMessage("error",file_name + " :: Error: Password miss-match.")                                        
                    exit_with_message("\nError: Password miss-match.Please run \"view setup\" command again")
                new__view_vc_pwd=Security.encrypt(new__view_vc_pwd)
            
            current_view_vc_port=self.authconfig['view_vc_port'] if  ('view_vc_port' in self.authconfig.keys()) else "Not Set"
            view_vc_port=raw_input("Enter vCenter Server Port [default: "+str(current_view_vc_port)+"]: ")
            #vc_port=vc_port.strip()
            if view_vc_port == "":
                if(current_view_vc_port == "Not Set"):
                    loggerObj.LogMessage("error",file_name + " :: Error: Set vCenter Server Port.")                                                            
                    exit_with_message("Error: Set vCenter Server Port.")
                view_vc_port=int(current_view_vc_port)
            else:
                view_vc_port=int(view_vc_port)
            if isinstance(view_vc_port, int ) == False:
                loggerObj.LogMessage("error",file_name + " :: Error: Port number is not a numeric value.")                                                        
                exit_with_message("\nError: Port number is not a numeric value.")
            
            #Test Connection Status
            print "Checking View vCenter Server Connection Status:",
            status, message = self.check_view_vc_connectivity(view_vc_ip, view_vc_user, new__view_vc_pwd, view_vc_port)
            if status == True:
                print Fore.GREEN+" Connection successful"+Fore.RESET
            else:
               print Fore.RED+" Connection failure"+Fore.RESET
               exit_with_message(message)      
            #print "vc_ip :"+vc_ip+" vc_user :"+vc_user+" vc_pwd : "+vc_pwd+ " vc_port:"+str(vc_port)+" cluster : "+cluster+" host : "+hosts
     
            view_auth = dict()
            view_auth["view_ip"]=vc_ip;
            view_auth["view_user"]=vc_user;
            view_auth["view_pwd"]=vc_pwd;
            view_auth["view_vc_ip"]=view_vc_ip;
            view_auth["view_vc_user"]=view_vc_user;
            view_auth["view_vc_pwd"]=new__view_vc_pwd;
            view_auth["view_vc_port"]=view_vc_port;
            
            CheckerBase.save_auth_into_auth_config(self.get_name(),view_auth)
            loggerObj.LogMessage("info",file_name + " :: VMware Horizon View Server is configured Successfully.")                                                                    
            exit_with_message("VMware Horizon View Server is configured Successfully.")
        else:
            loggerObj.LogMessage("info",file_name + " :: VMware Horizon View Health Check not supported on this operating system. Please use windows machine.")                                                                    
            exit_with_message("VMware Horizon View Health Check not supported on this operating system. Please use windows machine.")
        return
    
    def run_local_command(self,cmd):
         proc= os.popen(cmd)
         output=proc.read()
         exit_code=proc.close()
         return output.strip().lower(),exit_code
    
    def get_vc_connection(self):
        SI = None
        
        if self.si !=None:
            return self.si
        
        try:
            SI = connect.SmartConnect(host=self.authconfig['view_vc_ip'],
                                      user=self.authconfig['view_vc_user'],
                                      pwd=Security.decrypt(self.authconfig['view_vc_pwd']),
                                      port=self.authconfig['view_vc_port'])
            atexit.register(connect.Disconnect, SI)
        except IOError, ex:
            loggerObj.LogMessage("error",file_name + " :: Error getting SI" + ex.message)                                                                    
            pass
        
        if not SI:
            return 'View-VC-Error'
        else:
           return SI
    
    def get_vc_vms(self,search,search_by='ip'):
        """
        Return VI VM(virtual machine) object.
        @param  string search     search vm either IP or DNS or UUID
        @param string search_by     search option by IP or DNS or UUID
        """
        VM = None
        
        #get Vcneter Connection object
        SI=self.get_vc_connection()
   
        if search_by=='uuid':
            loggerObj.LogMessage("info",file_name + " :: get_vc_vms search by uuid.")                                                                                
            VM = SI.content.searchIndex.FindByUuid(None, search,
                                           True,
                                           True)
        elif search_by=='dns':
            loggerObj.LogMessage("info",file_name + " :: get_vc_vms search by dns.")                                                                                
            VM = SI.content.searchIndex.FindByDnsName(None, search,
                                                      True)
        elif search_by=='ip':
            loggerObj.LogMessage("info",file_name + " :: get_vc_vms search by ip.")                                                                                
            VM = SI.content.searchIndex.FindByIp(None, search, True)
        
        return VM
    
    def get_vc_all_vms(self,vm_properties=None):
        """
        Return     dict                    containing VM object, and property of VM.
        @param     array vm_properties     properties to be fetch if None VM object is return
        """
        service_instance=self.get_vc_connection()
        root_folder = service_instance.content.rootFolder
        view = get_container_view(service_instance,
                                           obj_type=[vim.VirtualMachine])
        vm_data = collect_properties(service_instance, view_ref=view,
                                              obj_type=vim.VirtualMachine,
                                              path_set=vm_properties,
                                              include_mors=True)
        
        return vm_data
     
    def check_view_vc_connectivity(self,vc_ip,vc_user,vc_pwd,vc_port, reqType="cmd"):
        si=None
        warnings.simplefilter('ignore')
        try:
            si = SmartConnect(host=vc_ip, user=vc_user, pwd=Security.decrypt(vc_pwd), port=vc_port)
            return True,None
        except vim.fault.InvalidLogin:
            loggerObj.LogMessage("error",file_name + " :: Error : Invalid vCenter Server Username or password.")                                                                                
            if reqType == "cmd":
                return False,"Error : Invalid vCenter Server Username or password\n\nPlease run \"vc setup\" command again!!"
            else:
                return False,"Error : Invalid vCenter Server Username or password"
        except ConnectionError as e:
            loggerObj.LogMessage("error",file_name + " :: Error : Connection Error.")
            if reqType == "cmd":                                                                              
                return False,"Error : Connection Error"+"\n\nPlease run \"vc setup\" command again!!"
            else:
                return False,"Error : Connection Error"
        finally:
            Disconnect(si)
         
    def check_connectivity(self,host_ip,host_username,host_password):
            
            #check winrm running on local machine
            output,exit_code=self.run_local_command("powershell (get-service winrm).status")
            if output != 'running':
                #print 'Starting winrm service'
                output,exit_code=self.run_local_command("powershell (start-service winrm)")
                if exit_code!=None:
                    loggerObj.LogMessage("error",file_name + " :: winrm clinet not installed or configured properly on this machine.")                                                                                
                    return False, 'winrm clinet not installed or configured properly on this machine.'
            
            #get trusted host
            trustedhost,exit_code=self.run_local_command('POWERSHELL "Get-WSManInstance -ResourceURI winrm/config/client | select -ExpandProperty TrustedHosts"')
      
            if host_ip not in  trustedhost.split(','):
                #print 'Adding '+host_ip+' to trsuted list'
                if trustedhost !='':
                    knows_host='winrm s winrm/config/client @{TrustedHosts="'+trustedhost+','+host_ip+'"}'
                else:
                    knows_host='winrm s winrm/config/client @{TrustedHosts="'+host_ip+'"}'
                output,exit_code=self.run_local_command(knows_host)
                
                if exit_code != None:
                    return False,output.strip()
            
            powershell_cmd=HorizonViewChecker.powershell_encode("Add-PSSnapin VMware.View.Broker ;echo test")
            power_shell_text = """winrs -r:{0} -u:{1} -p:{2} powershell -EncodedCommand {3} 2>&1""".format(
                                 host_ip,host_username,Security.decrypt(host_password),powershell_cmd)
            #print power_shell_text
            proc= os.popen(power_shell_text)
            output=proc.read()
            exit_code=proc.close()
            #print output , exit_code
            if exit_code == None:
                return True,output.strip()
            else:
                knows_host='winrm s winrm/config/client @{TrustedHosts="'+trustedhost+'"}'
                test_output,exit_code=self.run_local_command(knows_host)
                return False,output.strip()
    
    def execute(self, args, reqType="cmd"):

        if len(args) == 0:
            self.usage()

        check_groups = [k for k,v in self.config.items() if k.endswith('checks')]
        check_groups_run = []

        if args[0] == "help":
            self.usage()
        elif args[0] in self.categories:
            self.category=args[0]
            check_groups_run = check_groups
            if len(args) > 1:
                self.usage("Parameter not expected after categories")
        elif args[0] == "run_all":
            check_groups_run = check_groups
            if len(args) > 1:
                self.usage("Parameter not expected after run_all")
        elif args[0] == 'setup':
            self.setup()
        else:
            for group in args:
                if group not in check_groups:
                    self.usage("Group " + group + " is not a valid check group")
                check_groups_run.append(group)

        self.reporter.notify_progress(self.reporter.notify_info,"Starting VMware Horizon View Checks")
        self.result = ViewCheckerResult("view",self.authconfig)
        warnings.simplefilter('ignore')

        
        check_functions = {}
        for func in dir(self):
            func_obj = getattr(self, func)
            if callable(func_obj) and func.startswith("check_") and hasattr(func_obj, 'group'):
                group_name = func_obj.group
                group_functions = check_functions.get(group_name)
                if group_functions:
                    group_functions.append(func_obj)
                else:
                    check_functions[group_name] = [func_obj]
        
        #Check weather OS is windows if not execute view setup command message is shown
        if not sys.platform.startswith("win") :
            loggerObj.LogMessage("error",file_name + " :: Error : Horizon View Connection Error on windows platform")                                                                                            
            if reqType == "cmd":
                exit_with_message("Error : Horizon View Connection Error"+"\n\nPlease run \"view setup\" command to configure VMware Horizon View Server")
            else:
                return self.result, "Error : Horizon View Connection Error"    
        #check view server connectivity
        status, message = self.check_connectivity(self.authconfig['view_ip'],self.authconfig['view_user'],self.authconfig['view_pwd'])
        if status == False:
            loggerObj.LogMessage("error",file_name + " :: Error : Horizon View Connection Error")                                                                                            
            if reqType == "cmd":
                exit_with_message("Error : Horizon View Connection Error"+"\n\nPlease run \"view setup\" command to configure VMware Horizon View Server")
            else:
                return self.result, "Error : Horizon View Connection Error"
        vcstatus, vcmessage = self.check_view_vc_connectivity(self.authconfig['view_vc_ip'],self.authconfig['view_vc_user'],self.authconfig['view_vc_pwd'],self.authconfig['view_vc_port'])         
        
        if vcstatus == False:
            loggerObj.LogMessage("error",file_name + " :: Error : View VC Connection Error")
            if reqType == "cmd":
                exit_with_message("Error : View VC Connection Error"+"\n\nPlease run \"view setup\" command to configure VMware Horizon View VC Server")
            else:
                return self.result, "Error : Horizon View Connection Error"
            
        passed_all = True
        
        for check_group in check_groups_run:          
            self.reporter.notify_progress(self.reporter.notify_checkGroup,check_group)
           
            for check in self.config[check_group]:
                self.reporter.notify_progress(self.reporter.notify_checkName,check['name'])              
                
                if utility.glob_stopExecution:
                    return self.result, "Stopped"

                if self.category!=None: #condition for category 
                    if self.category not in check['category']:
                        continue

                if check['property_type'].lower()== "powershell":
                    check_name=check['name']
                    operator=check['operator']
                    expected=check['ref-value']
                    actual = self.get_view_property(check['property'])
                    passed=HorizonViewChecker.apply_operator(actual, expected, operator)
                    message=''
                    if operator == '=':
                        message="Actual:="+actual + " (Expected:= " + expected+ ")"
                    else:
                        message="Actual:="+actual + " (Expected:= " + operator + expected+ ")"
                    self.reporter.notify_progress(self.reporter.notify_checkLog,message, passed and "PASS" or "FAIL")
                    message=", "+message+'#'+str(passed and "Pass" or "Fail")

                    if passed:
                        self.result.add_check_result(ViewCheckerResult(check_name, None, passed,message,category=check['category'], expected_result=check['expectedresult']))
                    else:
                        self.result.add_check_result(ViewCheckerResult(check_name, None, passed, message, check['category'], None, check['expectedresult'], self.knowledge_pool.get(check_name, None)))
                    #self.reporter.notify_one_line(check_name, str(passed))
                #self.result.add_check_result(CheckerResult(check['name'], None, passed, message, check['category'],None,check['expectedresult']))

                    try:
                        self.realtime_results = json.load(open("display_json.json","r"))
                        all_prop,props = [ x for x in message.split(', ') if x != ''], []
                        for xprop in all_prop:
                            xprop,xstatus = xprop.split("#")

                            xprop_msg, xprop_actual, xprop_exp = xprop.split(":=")                        
                            xprop_actual = xprop_actual.split(' (')[0] or xprop_actual.split(' ')[0] or "None"
                            props.append({"Status":xstatus,"Expected":xprop_exp[:-1] , "Actual":xprop_actual })

                        self.realtime_results['view']['checks'].append({'Message':check['name'],'Status': (passed and "PASS" or "FAIL"),"Properties": props, "knowledge" : self.knowledge_pool.get(check['name'], None)})
                        #self.realtime_results['view']['checks'].append({'Name':check_name ,'Status': passed and "PASS" or "FAIL"})
                        with open("display_json.json", "w") as myfile:
                            json.dump(self.realtime_results, myfile)
                    except:
                        pass  

                passed_all = passed_all and passed

            if check_group in check_functions:
                for check_function in check_functions[check_group]:

                    if utility.glob_stopExecution:
                        return self.result, "Stopped"
 
                    if self.category!=None:#condition for category for custom checks 
                        if self.category not in check_function.category:
                            continue                      
                    passed, message,path = check_function()

                    if passed:
                        self.result.add_check_result(ViewCheckerResult(check_function.descr, None, passed, message,category=check_function.category,expected_result=check_function.expected_result))
                    else:
                        self.result.add_check_result(ViewCheckerResult(check_function.descr, None, passed, message, check_function.category, check_function.expected_result, self.knowledge_pool.get(check_function.descr, None)))

                    try:
                        self.realtime_results = json.load(open("display_json.json","r"))
                        all_prop,props = [ x for x in message.split(', ') if x != ''], []
                        for xprop in all_prop:
                            xprop,xstatus = xprop.split("#")
                            xprop_msg, xprop_actual, xprop_exp = xprop.split(":=")
                            xprop_actual = xprop_actual.split(' (')[0] or xprop_actual.split(' ')[0] or "None"
                            props.append({"Status":xstatus,"Expected":xprop_exp[:-1] , "Actual":xprop_actual })

                        self.realtime_results['view']['checks'].append({'Message':check_function.descr,'Status': (passed and "PASS" or "FAIL"),"Properties": props, "knowledge" : self.knowledge_pool.get(check_function.descr, None)})
                        #self.realtime_results['view']['checks'].append({'Name':check_name ,'Status': passed and "PASS" or "FAIL"})
                        with open("display_json.json", "w") as myfile:
                            json.dump(self.realtime_results, myfile)
                    except:
                        pass  
 
                    passed_all = passed_all and passed
            self.reporter.notify_progress(self.reporter.notify_checkName,"")
        

#         Disconnect(self.si)
        self.result.passed = ( passed_all and "PASS" or "FAIL" )
        self.result.message = "View Checks completed with " + (passed_all and "success" or "failure")
        self.reporter.notify_progress(self.reporter.notify_info," VMware Horizon View Checks complete")

        return self.result, "Complete"

    def get_view_property(self,powershell_cmd):
        actual=HorizonViewChecker.run_powershell(self.authconfig['view_ip'],self.authconfig['view_user'],Security.decrypt(self.authconfig['view_pwd']),powershell_cmd)
        return actual
        
    @staticmethod
    def powershell_encode(data):
        # blank command will store our fixed unicode variable
        blank_command = ""
        powershell_command = ""
        # Remove weird chars that could have been added by ISE
        n = re.compile(u'(\xef|\xbb|\xbf)')
        # loop through each character and insert null byte
        for char in (n.sub("", data)):
            # insert the nullbyte
            blank_command += char + "\x00"
        # assign powershell command as the new one
        powershell_command = blank_command
        # base64 encode the powershell command
        powershell_command = base64.b64encode(powershell_command)
        return powershell_command
    
    @staticmethod
    def run_powershell(host_ip,host_username,host_password,powershell_cmd):
            #print host_ip,host_username,host_password,command
            #powershell_cmd = powershell_cmd.replace('"', '\'')
    #         power_shell_text = """winrs -r:{0} -u:{1} -p:{2} powershell Add-PSSnapin VMware.View.Broker ;{3} 2>&1""".format(
    #                             host_ip,host_username,host_password,powershell_cmd)
            powershell_cmd=HorizonViewChecker.powershell_encode("Add-PSSnapin VMware.View.Broker ;"+powershell_cmd)
            power_shell_text = """winrs -r:{0} -u:{1} -p:{2} powershell -EncodedCommand {3} 2>&1""".format(
                                 host_ip,host_username,host_password,powershell_cmd)
            #print power_shell_text
            proc= os.popen(power_shell_text)
            output=proc.read()
            exit_code=proc.close()
            #print output , exit_code
            if exit_code == None:
                return output.strip()
            else:
                return "command-error"
    
    @staticmethod
    def apply_operator(actual, expected, operator):
        
        if actual == 'Not-Configured' or expected  == 'Not-Configured':
            return  False
        
        if operator == "=":
            return expected == str(actual)

        elif operator == "<":
            return int(actual) < int(expected)
        elif operator == "<=":
            return int(actual) <= int(expected)
        elif operator == ">=":
            return int(actual) >= int(expected)
        elif operator == ">":
            return int(actual) > int(expected)
        elif operator == "!=":
            return expected != str(actual)

        # Handle others operators as needed
        else:
            raise RuntimeError("Unexpected operator " + operator)
    
    @checkgroup("view_components_checks", "Verify View Connection Brokers runs on a supported operating system",["availability"],"[Windows Server 2008 R2 (64 bit),Windows Server 2008 R2 SP1 (64 bit),Windows 2012 R2 (64 bit)]")
    def check_connectionbroker_os(self):
#         powershell_cmd="(Get-WmiObject Win32_OperatingSystem ).Caption + (Get-WmiObject -class Win32_OperatingSystem).OSArchitecture"
#         output=self.get_view_property(powershell_cmd)
        loggerObj.LogMessage("info",file_name + " :: check_connectionbroker_os - Enter")                                                                                                        
    
        powershell_cmd='foreach ( $cb in get-ConnectionBroker){ if($cb.type -match "Connection Server") {$cb.externalURL}}'
        connection_brokers=self.get_view_property(powershell_cmd)
        message = ""
        passed_all = True
        import urlparse
        
        for connection_broker in connection_brokers.split('\n'):
            p = '(?:http.*://)?(?P<host>[^:/ ]+).?(?P<port>[0-9]*).*'
            hostname= re.search(p,connection_broker).group('host')
            vm=None
            if Validate.valid_ip(hostname):
                vm=self.get_vc_vms(hostname)
            else:
                vm=self.get_vc_vms(hostname,'dns')
            status=False
            expected = ['Microsoft Windows Server 2008 R2 (64-bit)','Microsoft Windows Server 2008 R2 SP1 (64-bit)', 'Microsoft Windows Server 2012 R2 (64-bit)']
            if vm == None:
                self.reporter.notify_progress(self.reporter.notify_checkLog, "Actual:="+hostname+" VM-Not-Found (Expected:="+';'.join(expected)+")", (status and "PASS" or "FAIL"))
                message+=", "+"Actual:="+hostname+" VM-Not-Found (Expected:="+';'.join(expected)+")#"+(status and "Pass" or "Fail")
            else:
                os=vm.summary.config.guestFullName

                if os in expected:
                    status = True
                
                self.reporter.notify_progress(self.reporter.notify_checkLog, "Actual:=For Server["+hostname+"]: "+os+" (Expected:="+str(';'.join(expected))+")", (status and "PASS" or "FAIL"))
                message+=", "+"Actual:=For Server["+hostname+"]: "+os+" (Expected:="+';'.join(expected)+")#"+(status and "Pass" or "Fail")
            passed_all = passed_all and status 
       
        loggerObj.LogMessage("info",file_name + " :: check_connectionbroker_os - Exit")                                                                                                        
        
        return passed_all , message,None
    
    @checkgroup("view_components_checks", "View Connection Brokers has correct CPUs",["performance"],"For 1-50 Desktop; CB cpu >=2 ,for 51-2000 Desktop; CB cpu >=4, for 2001-5000 Desktop; CB CPU >=6")
    def check_connectionbroker_cpu(self):  
#         cpu_powershell='$cpu=0;ForEach ($obj in  Get-WmiObject -class win32_processor) { $cpu+=$obj.NumberOfCores}; $cpu'
#         cpu=self.get_view_property(cpu_powershell)
        loggerObj.LogMessage("info",file_name + " :: check_connectionbroker_cpu - Enter")                                                                                                        

        vms=self.get_view_property('(Get-DesktopVM).length')
        
        powershell_cmd='foreach ( $cb in get-ConnectionBroker){ if($cb.type -match "Connection Server") {$cb.externalURL}}'
        connection_brokers=self.get_view_property(powershell_cmd)
           
        message = ""
        passed= True
        passed_all=True
        actual=None
        expected=None
        
        if connection_brokers == 'command-error' or  vms == 'command-error':
            return None, None,None
        else:
            for connection_broker in connection_brokers.split('\n'):
                p = '(?:http.*://)?(?P<host>[^:/ ]+).?(?P<port>[0-9]*).*'
                hostname= re.search(p,connection_broker).group('host')
                vm=None
                if Validate.valid_ip(hostname):
                    vm=self.get_vc_vms(hostname)
                else:
                    vm=self.get_vc_vms(hostname,'dns')
                passed=True
                if vm != None:                 
                    cpu=int(vm.summary.config.numCpu)
                    vms=int(vms)
                    if vms >0 and vms <= 50: 
                        if cpu <2:
                             passed= False
                        expected = "For 1-50 Desktops; Number of Cpu:>=6"
                    elif vms >50 and vms <=2000: 
                        if cpu <4:
                             passed= False
                        expected = "For 51-2000 Desktops; Number of Cpu:>=4"
                    elif vms >2000 and vms <=5000: 
                        if cpu <6:
                             passed= False
                        expected = "For 2001-5000 Desktops; Number of Cpu:>=6"
                    actual= "For Server["+hostname+"]; Number of Cpu:"+str(cpu)+"; Number of Desktop:"+str(vms)
                     
                    self.reporter.notify_progress(self.reporter.notify_checkLog, "Actual:="+actual+" (Expected:="+str(expected)+")", (passed and "PASS" or "FAIL"))
                    message +=", "+ "Actual:="+actual+" (Expected:="+str(expected)+")#"+(passed and "Pass" or "Fail")
                else:
                    message +=", "+ "Actual:="+hostname+" not-found (Expected:=Connection Broker Server CPU's)#"+(False and "Pass" or "Fail")
                    passed=False
                passed_all = passed_all and passed

        loggerObj.LogMessage("info",file_name + " :: check_connectionbroker_cpu - Exit")                                                                                                        
          
        return passed_all , message,None
       
    @checkgroup("view_components_checks", "View Connection Brokers has correct Memory",["performance"],"For 1-50 Desktop; CB Memory >=4GB ,for 51-2000 Desktop; CB cpu >=10GB, for 2001-5000 Desktop; CB CPU >=12GB")
    def check_connectionbroker_memory(self):

        loggerObj.LogMessage("info",file_name + " :: check_connectionbroker_memory - Enter")                                                                                                        
         
        #memory=self.get_view_property(memory_powershell)
        vms=self.get_view_property('(Get-DesktopVM).length')
         
        #memory_powershell='(Get-WmiObject CIM_PhysicalMemory).Capacity / 1GB'
        powershell_cmd='foreach ( $cb in get-ConnectionBroker){ if($cb.type -match "Connection Server") {$cb.externalURL}}'
        connection_brokers=self.get_view_property(powershell_cmd) 
                   
        message = ""
        passed= True
        passed_all=True
        actual=None
        expected=None
        if connection_brokers == 'command-error' or  vms == 'command-error':
            return None, None,None
        else:
            for connection_broker in connection_brokers.split('\n'):
                p = '(?:http.*://)?(?P<host>[^:/ ]+).?(?P<port>[0-9]*).*'
                hostname= re.search(p,connection_broker).group('host')
                vm=None
                if Validate.valid_ip(hostname):
                    vm=self.get_vc_vms(hostname)
                else:
                    vm=self.get_vc_vms(hostname,'dns')
                passed=True
                if vm != None:
                    memory=int(vm.summary.config.memorySizeMB)*(0.001) # convert to GB
                    vms=int(vms)
                    if vms >0 and vms <= 50: 
                        if memory <4:
                             passed= False
                        expected = "For 1-50 Desktops; Memory:>=4GB"
                    elif vms >50 and vms <=2000: 
                        if memory <10:
                             passed= False
                        expected = "For 51-2000 Desktops; Memory:>=10GB"
                    elif vms >2000 and vms <=5000: 
                        if memory <12:
                             passed= False
                        expected = "For 2001-5000 Desktops; Memory:>=12GB"
                    actual= "For Server["+hostname+"]; Memory:"+str(memory)+"GB; Number of Desktop:"+str(vms)
                    self.reporter.notify_progress(self.reporter.notify_checkLog, "Actual:="+actual+" (Expected:="+str(expected)+")", (passed and "PASS" or "FAIL"))
                    message+=", "+ "Actual:="+actual+" (Expected:="+str(expected)+")#"+(passed and "Pass" or "Fail")
                else:
                    message +=", "+ "Actual:="+hostname+" not-found (Expected:=Connection Broker Server CPU's)#"+(False and "Pass" or "Fail")
                    passed=False
                passed_all = passed_all and passed
                    #passed_all = passed_all and passed

        loggerObj.LogMessage("info",file_name + " :: check_connectionbroker_memory - Exit")                                                                                                        
           
        return passed , message,None
      
    @checkgroup("view_components_checks", "Verify that the Maximum number of desktops in a pool is no more than 1000",["availability"],"<=1000 Desktops")
    def check_max_desktop_per_pool(self):
        loggerObj.LogMessage("info",file_name + " :: check_max_desktop_per_pool - Enter")                                                                                                        
        
        powershell_cmd='ForEach($Pool in Get-Pool){Write-Host $Pool.displayName = $Pool.maximumCount}'
        output=self.get_view_property(powershell_cmd)
           
        if output == 'command-error':
            return None,None,None
           
        pools= output.split("\n")
        message = ""
        passed_all = True
        expected="Max Desktop <=10000"
        is_pool_found=False
        error=False
        try:
             
            for pool in pools:
                pool_name, max_vm_in_pool= pool.split("=")
                pool_name=pool_name.strip()
                max_vm_in_pool=max_vm_in_pool.strip()
                 
                if pool_name == '' and max_vm_in_pool =='':
                    continue
                is_pool_found=True
                max_vm_in_pool=int(max_vm_in_pool.strip())
                flag=True
                if max_vm_in_pool >1000:
                    flag=False
                output="Pool :"+pool_name + " Max Desktop :"+str(max_vm_in_pool)
                 
                self.reporter.notify_progress(self.reporter.notify_checkLog, "Actual:="+output+" (Expected:="+str(expected)+")", (flag and "PASS" or "FAIL"))
                message+=", "+ "Actual:="+output+" (Expected:="+str(expected)+")#"+(flag and "Pass" or "Fail") 
                passed_all = flag and passed_all
        except ValueError:
            error = True
            passed_all=False
            self.reporter.notify_progress(self.reporter.notify_checkLog, "Actual=:Get-Pool Command Error (Expected:="+str(expected)+")", (False and "PASS" or "FAIL")) 
            message+=", "+ "Actual:=Get-Pool Command Error (Expected:="+str(expected)+")#"+(False and "Pass" or "Fail")
        #passed_all = passed_all and passed
        
        if is_pool_found == False and error ==False:
            self.reporter.notify_progress(self.reporter.notify_checkLog, "Actual:=Pool-Not-Found (Expected:="+str(expected)+")", (False and "PASS" or "FAIL"))
            message+=", "+ "Actual:=Pool-Not-Found (Expected:="+str(expected)+")#"+(False and "Pass" or "Fail")
            passed_all=False

        loggerObj.LogMessage("info",file_name + " :: check_max_desktop_per_pool - Exit")                                                                                                        
         
        return passed_all , message,None
      
    @checkgroup("view_components_checks", "Verify Desktop Pool Status",["availability"],"true")
    def check_desktop_pool_enabled(self):
        loggerObj.LogMessage("info",file_name + " :: check_desktop_pool_enabled - Enter")                                                                                                        
        
        powershell_cmd='ForEach($Pool in Get-Pool){Write-Host $Pool.displayName = $Pool.enabled}'
        output=self.get_view_property(powershell_cmd)
           
        if output == 'command-error':
            return None,None,None
           
        pools= output.split("\n")
        message = ""
        passed_all = True
        is_pool_found=False
        error=False
        expected="true"
        try:
            for pool in pools:
                pool_name, pool_status= pool.split("=")
                pool_name=pool_name.strip()
                pool_status=pool_status.strip()
                 
                if pool_name =='' and pool_status == '':
                    continue
                is_pool_found=True
                 
                flag=True
                if pool_status == 'false':
                    flag=False
                output="Pool :"+pool_name + " Enabled:"+pool_status
                passed_all = flag and passed_all
                self.reporter.notify_progress(self.reporter.notify_checkLog, "Actual:="+output+" (Expected:="+str(expected)+")", (flag and "PASS" or "FAIL"))
                message+=", "+ "Actual:="+output+" (Expected:="+str(expected)+")#"+(flag and "Pass" or "Fail") 
         
        except ValueError:
            error=True
            passed_all = False and passed_all
            self.reporter.notify_progress(self.reporter.notify_checkLog, "Actual:=Get-Pool Command Error (Expected:="+str(expected)+")", (False and "PASS" or "FAIL"))
            message+= ", "+"Actual:=Get-Pool Command Error (Expected:="+str(expected)+")#"+(False and "Pass" or "Fail")
        
        if is_pool_found == False and error == False:
            self.reporter.notify_progress(self.reporter.notify_checkLog, "Actual:=Pool-Not-Found (Expected:="+str(expected)+")", (False and "PASS" or "FAIL"))
            message+=", "+ "Actual:=Pool-Not-Found (Expected:="+str(expected)+")#"+(False and "Pass" or "Fail")
            passed_all=False
        #passed_all = passed_all and passed
        loggerObj.LogMessage("info",file_name + " :: check_desktop_pool_enabled - Exit")                                                                                                        
           
        return passed_all , message,None
      
    @checkgroup("view_components_checks", "Verify Connection Broker Server configured with static IP",["availability"],"true")
    def check_connection_broker_has_static_ip(self):
        loggerObj.LogMessage("info",file_name + " :: check_connection_broker_has_static_ip - Enter")                                                                                                        
        
        powershell_cmd='foreach ( $cb in get-ConnectionBroker){ if($cb.type -match "Connection Server") {$cb.externalURL}}'
        connection_brokers=self.get_view_property(powershell_cmd)
        message = ""
        passed_all = True
        import urlparse
        
        for connection_broker in connection_brokers.split('\n'):
            p = '(?:http.*://)?(?P<host>[^:/ ]+).?(?P<port>[0-9]*).*'
            hostname= re.search(p,connection_broker).group('host')
            vm=None
            if Validate.valid_ip(hostname):
                vm=self.get_vc_vms(hostname)
            else:
                vm=self.get_vc_vms(hostname,'dns')
            status=False
            if vm == None:
                continue
            else:
                nic_info=vm.guest.net
                for nic in nic_info:
                    
                    is_static_ip=nic.ipConfig.dhcp.ipv4.enable
                    ipaddress=','.join(nic.ipAddress)
                    actual=None
                    if is_static_ip:
                        actual="Actual:=Server["+hostname+"] configured with DHCP IP's ["+ipaddress+"]"
                    else:
                        actual="Actual:=Server["+hostname+"] configured with Static IP's ["+ipaddress+"]"
                        
                    self.reporter.notify_progress(self.reporter.notify_checkLog, actual+" (Expected:=Static IP's", (not is_static_ip and "PASS" or "FAIL"))
                    message+=", "+actual+" (Expected:=Static IP's)#"+(not is_static_ip and "Pass" or "Fail")
                    passed_all = passed_all and (not is_static_ip) 

        loggerObj.LogMessage("info",file_name + " :: check_connection_broker_has_static_ip - Exit")                                                                                                        
       
        return passed_all , message,None
      
    @checkgroup("view_components_checks", "Verify number of Desktop configured in View",["availability"],"Number of desktop < 10000 or (2000 x number of brokers) ")
    def check_desktop_configured(self):
        loggerObj.LogMessage("info",file_name + " :: check_desktop_configured - Enter")                                                                                                        
        
        connection_broker_cmd='((get-connectionbroker | where {$_.type -like "Connection Server"}) | measure).count'
        no_of_connection_broker=self.get_view_property(connection_broker_cmd)
        message = "" 
        desktop_cmd='(Get-DesktopVM).length'
        no_of_desktop=self.get_view_property(desktop_cmd)
        if no_of_desktop == 'command-error' or no_of_connection_broker == 'command-error':
            return None,None,None
          
        no_of_desktop=int(no_of_desktop)
        no_of_connection_broker=int(no_of_connection_broker)
          
        passed=False
        if (no_of_desktop < 1000) or (no_of_desktop < (2000* no_of_connection_broker)):
            passed = True
        output="No.of Desktops: "+str(no_of_desktop)+"; No.of Connection Brokers: "+str(no_of_connection_broker)
        expected="No.of desktop < 10000 or (2000 x No.of Connection Brokers)"
        self.reporter.notify_progress(self.reporter.notify_checkLog, "Actual:="+output+" (Expected:="+str(expected)+")", (passed and "PASS" or "FAIL"))
        message+=", "+"Actual:="+output+" (Expected:="+str(expected)+")#"+(passed and "Pass" or "Fail")

        loggerObj.LogMessage("info",file_name + " :: check_desktop_configured - Exit")                                                                                                        
        
        return passed , message,None
     
    @checkgroup("view_components_checks", "Verify vCenter servers have at least 4 vCPUs and 6 GBs of RAM",["Performance"],"vCPUs:>=4 and RAM:>=6 GBs")
    def check_view_vc(self):
        loggerObj.LogMessage("info",file_name + " :: check_view_vc - Enter")                                                                                                        
        
        vm=self.get_vc_vms(self.authconfig['view_vc_ip'])
        expected='>=4 vCPUs and >=6 GBs of RAM'
        passed=True
        message=""
        if vm is None:
              self.reporter.notify_progress(self.reporter.notify_checkLog, "Actual:=VCenter-Server-Not-Found (Expected:="+str(expected)+")", (False and "PASS" or "FAIL"))
              message+=", "+ "Actual:=VCenter-Server-Not-Found (Expected:="+str(expected)+")#"+(False and "Pass" or "Fail") 
              passed=False
        else:
            vm_config=vm.summary.config 
            vm_cpu= int(vm_config.numCpu)
            vm_memory=int(vm_config.memorySizeMB)*(0.001) # convert to GB
            passed=False
            if(vm_cpu >=4 and vm_memory >=6):
                passed=True
            output='vCPUs:'+str(vm_cpu)+' and RAM:'+str(vm_memory)+'GB'
            self.reporter.notify_progress(self.reporter.notify_checkLog, "Actual:="+output+" (Expected:="+str(expected)+")", (passed and "PASS" or "FAIL"))
            message+=", "+ "Actual:="+output+" (Expected:="+str(expected)+")#"+(passed and "Pass" or "Fail")

        loggerObj.LogMessage("info",file_name + " :: check_view_vc - Exit")                                                                                                        
                        
        return passed , message,None
    
    @checkgroup("view_components_checks", "Verify Desktop VM disk controller is an LSI Logic Controller",["Performance"],"true")
    def check_view_desktop_vm_has_LSI_controller(self):
        loggerObj.LogMessage("info",file_name + " :: check_view_desktop_vm_has_LSI_controller - Enter")                                                                                                        
        
        desktop_vms_name=self.get_view_property('Foreach ($vm in get-DesktopVM) {$vm.Name}')
        if desktop_vms_name == 'command-error':
            return None,None,None
        
        desktop_vms_names=desktop_vms_name.split('\n')
        vm_data=self.get_vc_all_vms(vm_properties=["name","config.hardware.device[1000].deviceInfo.summary"])
        passed=True
        message=""
        any_view_vm_found=False
        for vm in vm_data:
            vm_name=vm["name"]
            if vm_name in desktop_vms_names:
                '''check is VM is part of VMware View Desktop VM'''
                
                controller=None
                try:
                    controller=vm["config.hardware.device[1000].deviceInfo.summary"]
                except KeyError:
                    continue
                
                any_view_vm_found=True
                if controller!=None:
                    LSI_found=False
                    if 'LSI' in controller:
                        LSI_found=True
                    passed=passed and LSI_found
                    self.reporter.notify_progress(self.reporter.notify_checkLog, "Actual:=For Desktop VM ["+vm_name+"]: Disk controller["+controller+"]+ :"+str(LSI_found)+" (Expected:=LSI controller : True)", (LSI_found and "PASS" or "FAIL"))
                    message+=", "+ "Actual:=For DesktopVM ["+vm_name+"]; Disk controller["+controller+"] :"+str(LSI_found)+" (Expected:=LSI controller : True)#"+(LSI_found and "Pass" or "Fail")
                else:
                    passed=passed and False
                    self.reporter.notify_progress(self.reporter.notify_checkLog, "Actual:=For Desktop VM ["+vm_name+"]: LSI controller not found (Expected:=LSI controller : True)", (False and "PASS" or "FAIL"))
                    message+=", "+ "Actual:=For DesktopVM ["+vm_name+"]; LSI controller not found (Expected:=LSI controller : True)#"+(False and "Pass" or "Fail")
        if any_view_vm_found==False:
            passed=False
            self.reporter.notify_progress(self.reporter.notify_checkLog, "Actual:=No-Desktop-VM-Found (Expected:=LSI controller : True)", (False and "PASS" or "FAIL"))
            message+=", "+ "Actual:=No-Desktop-VM-Found (Expected:=LSI controller : True)#"+(False and "Pass" or "Fail")
            
        loggerObj.LogMessage("info",file_name + " :: check_view_desktop_vm_has_LSI_controller - Exit")                                                                                                        
            
        return passed, message, None