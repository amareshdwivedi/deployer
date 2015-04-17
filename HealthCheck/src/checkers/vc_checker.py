'''
    This module is to run health check against the VCenter Server.
'''
from __future__ import division
from bdb import effective
__author__ = 'subash atreya'
from requests.exceptions import ConnectionError
import string
import warnings
import paramiko
import socket
import requests
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
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
import time

LOGGER_OBJ = Logger()
FILE_NAME = os.path.basename(__file__)

def exit_with_message(message):
    print message
    sys.exit(1)


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

class VCChecker(CheckerBase):

    _NAME_ = "vc"
    resource_pool_config={}
    vcenter_stats_config={}
    responseHostsJson={}
    responseClusterJson={}
    vcenter_server_ssh = None
    esxi_ssh = None
    cvm_ssh = None
    ipmi_ssh = None

    def __init__(self):
        super(VCChecker, self).__init__(VCChecker._NAME_)
        self.config_form =  form.Form( form.Textbox("vCenter Server IP",value=self.authconfig['vc_ip']),
                form.Textbox("vCenter Server Port",value=self.authconfig['vc_port']),
                form.Textbox("vCenter Server Username",value=self.authconfig['vc_user']),
                form.Password("vCenter Server Password",value=Security.decrypt(self.authconfig['vc_pwd'])),
                form.Textbox("Clusters(Comma Seperated List)",value=self.authconfig['cluster']),
                form.Textbox("Hosts(Comma Seperated List)",value=self.authconfig['host']))() 

        self.si = None
        self.categories=['security','performance','availability','manageability','recoverability','reliability','configurability','supportability','post-install']
        self.category=None

    def get_name(self):
        return VCChecker._NAME_

    def get_desc(self):
        return "Performs vCenter Server health checks"

    def configure(self, config, knowledge_pool, reporter):
        self.config = config
        self.knowledge_pool = knowledge_pool[self.get_name()]
        self.reporter = reporter
        self.authconfig=self.get_auth_config(self.get_name())
        CheckerBase.validate_config(self.authconfig, "vc_ip")
        CheckerBase.validate_config(self.authconfig, "vc_user")
        CheckerBase.validate_config(self.authconfig, "vc_pwd")
        CheckerBase.validate_config(self.authconfig, "vc_port")

        checks_list = [k for k in config.keys() if k.endswith('checks')]
        #print checks_list
        for checks in checks_list:
            metrics = config[checks]
            if len(metrics) == 0:
                raise RuntimeError("At least one metric must be specified in "+ checks + "configuration file");

    def usage(self, message=None):
        p_table = PrettyTable(["Name", "Short help"])
        p_table.align["Name"] = "l"
        p_table.align["Short help"] = "l" 
        p_table.padding_width = 1 
        checks_list = [k for k in self.config.keys() if k.endswith('checks')]

        for checks in checks_list:
            p_table.add_row([checks,"Run "+checks])

        for category in self.categories:
            p_table.add_row([category,"Run "+category+' category'])
        p_table.add_row(["run_all", "Run all VC checks"])
        p_table.add_row(["setup", "Set vCenter Server Configuration"])
        message = message is None and str(p_table) or "\nERROR: "+ message + "\n\n" + str(p_table)
        exit_with_message(message)

    def setup(self):
        print "\nConfiguring vCenter Server:\n"

        current_vc_ip = self.authconfig['vc_ip'] if ('vc_ip' in self.authconfig.keys()) else "Not Set"
        vc_ip = raw_input("Enter vCenter Server IP [default: "+current_vc_ip+"]: ")
        vc_ip = vc_ip.strip()
        if vc_ip == "":
            if(current_vc_ip == "Not Set"):
                LOGGER_OBJ.LogMessage("error", FILE_NAME + " :: Error: Set vCenter Server IP.")
                exit_with_message("Error: Set vCenter Server IP.")
            vc_ip = current_vc_ip
        
        if Validate.valid_ip(vc_ip) == False:
            LOGGER_OBJ.LogMessage("error", FILE_NAME + " :: Error: Invalid vCenter Server IP address.")
            exit_with_message("\nError: Invalid vCenter Server IP address.")

        current_vc_user = self.authconfig['vc_user'] if ('vc_user' in self.authconfig.keys()) else "Not Set"
        vc_user=raw_input("Enter vCenter Server Username [default: "+current_vc_user+"]: ")
        vc_user=vc_user.strip()
        if vc_user == "":
            if(current_vc_user == "Not Set"):
                LOGGER_OBJ.LogMessage("error", FILE_NAME + " :: Error: Set vCenter Server Username.")
                exit_with_message("Error: Set vCenter Server Username.")
            vc_user=current_vc_user

        current_pwd=self.authconfig['vc_pwd'] if  ('vc_pwd' in self.authconfig.keys()) else "Not Set"
        new_vc_pwd=getpass.getpass('Enter vCenter Server Password [Press enter to use previous password]: ')

        if new_vc_pwd == "":
            if(current_pwd == "Not Set"):
                LOGGER_OBJ.LogMessage("error", FILE_NAME + " :: Error: Set vCenter Server Password.")
                exit_with_message("Error: Set vCenter Server Password.")
            vc_pwd = current_pwd
        else:
            confirm_pass = getpass.getpass('Re-Enter vCenter Server Password: ')
            if new_vc_pwd != confirm_pass :
                exit_with_message("\nError: Password miss-match.Please run \"vc setup\" command again")
            vc_pwd = Security.encrypt(new_vc_pwd)

        current_vc_port=self.authconfig['vc_port'] if  ('vc_port' in self.authconfig.keys()) else "Not Set"
        vc_port = raw_input("Enter vCenter Server Port [default: "+str(current_vc_port)+"]: ")

        if vc_port == "":
            if(current_vc_port == "Not Set"):
                LOGGER_OBJ.LogMessage("error", FILE_NAME + " :: Error: Set vCenter Server Port.")
                exit_with_message("Error: Set vCenter Server Port.")
            vc_port = int(current_vc_port)
        else:
            vc_port=int(vc_port)
        if isinstance(vc_port, int ) == False:
            LOGGER_OBJ.LogMessage("error", FILE_NAME + " :: Error: Port number is not a numeric value.")
            exit_with_message("\nError: Port number is not a numeric value.")

        current_host=self.authconfig['host'] if ('host' in self.authconfig.keys()) else "Not Set"        
#         cluster=raw_input("Enter Cluster Name [default: "+current_cluster+"] {multiple names separated by comma(,); blank to include all clusters}: ")
#         cluster=cluster.strip()
#          
#         current_host=self.authconfig['host'] if ('host' in self.authconfig.keys()) else "Not Set"
#         hosts=raw_input("Enter Host IP [default: "+current_host+"] {multiple names separated by comma(,); blank to include all hosts}: ")

        #Test Connection Status
        print "Checking vCenter Server Connection Status:",
        status, message = self.check_connectivity(vc_ip, vc_user, vc_pwd, vc_port)
        if status == True:
            print Fore.GREEN+" Connection successful"+Fore.RESET
            vc_auth = dict()
            vc_auth["vc_ip"] = vc_ip;
            vc_auth["vc_user"] = vc_user;
            vc_auth["vc_pwd"] = vc_pwd;
            vc_auth["vc_port"] = vc_port;
            vc_auth["cluster"] = "";
            vc_auth["host"] = "";
            CheckerBase.save_auth_into_auth_config(self.get_name(),vc_auth)

            cluster_map,message = self.get_cluster_list(vc_ip, vc_user, vc_pwd, vc_port) 
            if len(cluster_map) == 0:
                cluster = ""
                pass
            else:
                current_cluster=self.authconfig['cluster'] if ('cluster' in self.authconfig.keys()) else "Not Set"
                print "\nSelect one or more cluster names to run Healthcheck on from below list:"
                for key,value in cluster_map.iteritems():
                    print key, ':' , value
                cluster = raw_input("Enter Cluster Name [default: "+current_cluster+"] {multiple names separated by comma(,); blank to include all clusters}: ")
                cluster = cluster.strip().replace(' ', '*')

                vc_auth["cluster"] = self.authconfig["cluster"] = cluster
                CheckerBase.save_auth_into_auth_config(self.get_name(),vc_auth)

                if cluster != '':
                    host_map,message = self.get_host_list(vc_ip, vc_user, vc_pwd, vc_port,cluster)
                else:
                    host_map = {}

                if len(host_map) == 0:
                    hosts=""
                    pass
                else:
                    current_host=self.authconfig['host'] if ('host' in self.authconfig.keys()) else "Not Set"
                    print "\nSelect one or more host IPs to run Healthcheck on from below list:"
                    for key,value in host_map.iteritems():
                        print key, ':' , value
                    hosts=raw_input("Enter Host IP [default: "+current_host+"] {multiple names separated by comma(,); blank to include all hosts}: ")
                    hosts=hosts.strip()
                    vc_auth["host"] = self.authconfig["host"] = hosts
                    CheckerBase.save_auth_into_auth_config(self.get_name(),vc_auth)
        else:
            print Fore.RED+" Connection failure"+Fore.RESET
            exit_with_message(message) 

        Disconnect(self.si)
        exit_with_message("vCenter Server is Configured Successfully ")
        return


    def check_connectivity(self, vc_ip, vc_user, vc_pwd, vc_port, reqType="cmd"):
        self.si=None
        warnings.simplefilter('ignore')
        try:
            self.si = SmartConnect(host=vc_ip, user=vc_user, pwd=Security.decrypt(vc_pwd), port=vc_port)
            return True,None
        except vim.fault.InvalidLogin:
            LOGGER_OBJ.LogMessage("error", FILE_NAME + " :: Error : Invalid vCenter Server Username or password.")
            if reqType == "cmd":
                return False,"Error : Invalid vCenter Server Username or password\n\nPlease run \"vc setup\" command again!!"
            else:
                return False,"Error : Invalid vCenter Server Username or password"
        except ConnectionError as e:
            LOGGER_OBJ.LogMessage("error", FILE_NAME + " :: Error : Connection Error.")
            if reqType == "cmd":
                return False,"Error : Connection Error"+"\n\nPlease run \"vc setup\" command again!!"
            else:
                return False,"Error : Connection Error"
 
 
    def get_cluster_list(self,vc_ip,vc_user,vc_pwd,vc_port):
        warnings.simplefilter('ignore')
        cluster_map = {}
        key = 0
        try:
            path='content.rootFolder.childEntity.hostFolder.childEntity'
            clusters_map = self.get_vc_property(path)
            for clusters_key, clusters in clusters_map.iteritems():
                if clusters!="Not-Configured":
                    for cluster in clusters:
                        key+=1
                        cluster_name=cluster.name
                        cluster_map[key] = cluster_name
            return cluster_map,None
        except vim.fault.InvalidLogin:
            LOGGER_OBJ.LogMessage("error", FILE_NAME + " :: Connection Failure.")
            return cluster_map,"Error : Connection Failure"
        except ConnectionError as e:
            LOGGER_OBJ.LogMessage("error", FILE_NAME + " :: Connection Failure.")
            return cluster_map,"Error : Connection Failure"

    def get_host_list(self,vc_ip,vc_user,vc_pwd,vc_port,cluster):
        warnings.simplefilter('ignore')
        hosts_map = {}
        key = 0
        cluster_list = []
        try:
            cluster_path='content.rootFolder.childEntity.hostFolder.childEntity[name='+cluster+'].host'
            cluster_map = self.get_vc_property(cluster_path)
            for datacenter, host_list in cluster_map.iteritems():
                if host_list == "Not-Configured" :
                    continue
                elif len(host_list)==0: 
                    continue

                for host in host_list:
                    host_ip=host.name
                    key+=1
                    hosts_map[key] = host_ip
            return hosts_map,None
        except vim.fault.InvalidLogin:
            LOGGER_OBJ.LogMessage("error", FILE_NAME + " :: Connection Failure.")
            return hosts_map,"Error : Connection Failure"
        except ConnectionError as e:
            LOGGER_OBJ.LogMessage("error", FILE_NAME + " :: Connection Failure.")
            return hosts_map,"Error : Connection Failure"

    def execute(self, args, requestType="cmd"):

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

        self.reporter.notify_progress(self.reporter.notify_info,"Starting VC Checks")
        self.result = CheckerResult("vc",self.authconfig)
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

        try:
            self.si = SmartConnect(host=self.authconfig['vc_ip'], user=self.authconfig['vc_user'], pwd=Security.decrypt(self.authconfig['vc_pwd']), port=self.authconfig['vc_port'])
        except vim.fault.InvalidLogin:
            LOGGER_OBJ.LogMessage("error", FILE_NAME + " :: Error : Invalid vCenter Server Username or password.")
            if requestType == "cmd":
                exit_with_message("Error : Invalid vCenter Server Username or password\n\nPlease run \"vc setup\" command to configure vc")
            else:
                return self.result, "Error : Invalid vCenter Server Username or password"
        except ConnectionError as e:
            LOGGER_OBJ.LogMessage("error", FILE_NAME + " :: Error : Connection Error.")
            if requestType == "cmd":
                exit_with_message("Error : Connection Error"+"\n\nPlease run \"vc setup\" command to configure vc")
            else:
                return self.result, "Error : Connection Error"

        passed_all = True
        for check_group in check_groups_run:
            self.reporter.notify_progress(self.reporter.notify_checkGroup,check_group)

            for check in self.config[check_group]:
                if utility.glob_stopExecution:
                    return self.result, "Stopped"

                self.reporter.notify_progress(self.reporter.notify_checkName,check['name'])
                if self.category!=None: #condition for category 
                    if self.category not in check['category']:
                        continue

                passed, message=self.validate_vc_property(check['path'], check['operator'], check['ref-value'])
                try:
                    self.realtime_results = json.load(open("display_json.json","r"))
                    all_prop,props = [ x for x in message.split(', ') if x != ''], []
                    for xprop in all_prop:

                        xprop,xstatus = xprop.split("#")
                        xprop_msg, xprop_actual, xprop_exp = xprop.split("=")
                        if xprop_msg == "":
                            xprop_msg = check['name']
                        xprop_actual = xprop_actual.split(' (')[0] or xprop_actual.split(' ')[0] or "None"

                        if check['operator'] == "=": 
                            xprop_exp = check['ref-value'] or "None"
                        elif check['operator'] == "!=":
                            xprop_exp = "Not equal to "+(check['ref-value']  or "None")
                        elif check['operator'] == "<=":
                            if check['ref-value'].startswith("content."):
                                xprop_exp = xprop_exp.split(')')[0] or xprop_exp.split(') ')[0] or "None"
                                xprop_exp = "Less than or Equal to "+xprop_exp
                            else:
                                xprop_exp = "Less than or Equal to "+( check['ref-value'] or "None" )

                        if xprop_exp == "none":
                            xprop_exp = "None"
                        if xprop_actual == "none":
                            xprop_actual = "None"

                        #props.append({"Message":xprop_msg,"Status":xstatus,"Expected":xprop_exp , "Actual":xprop_actual })
                        xporp_act_msg = xprop_msg.replace('NoName@','').replace("NoName",'').replace('@','.')
                        props.append({"Message":xporp_act_msg,"Status":xstatus,"Expected":xprop_exp , "Actual":xprop_actual })

                    self.realtime_results['vc']['checks'].append({'Message' : check['name'], 'Status' : (passed and "PASS" or "FAIL"), "Properties" : props, "knowledge" : self.knowledge_pool.get(check['name'], None)})
                    with open("display_json.json", "w") as myfile:
                        json.dump(self.realtime_results, myfile)
                except:
                    # Need to handle temp-file case for command line
                    pass

                if passed:
                    self.result.add_check_result(CheckerResult(check['name'], None, passed, message, check['category'], check['path'], check['expectedresult']))
                else:
                    self.result.add_check_result(CheckerResult(check['name'], None, passed, message, check['category'], check['path'], check['expectedresult'], self.knowledge_pool.get(check['name'], None)))
                passed_all = passed_all and passed

            if check_group in check_functions:
                for check_function in check_functions[check_group]:
                    if utility.glob_stopExecution:
                        return self.result, "Stopped"

                    if self.category!=None:#condition for category for custom checks 
                        if self.category not in check_function.category:
                            continue

                    passed, message,path = check_function()
                    try:
                        self.realtime_results = json.load(open("display_json.json","r"))
                        all_prop,props = [ x for x in message.split(', ') if x != ''], []
                        for xprop in all_prop:
                            xprop,xstatus = xprop.split("#")
                            xprop_msg, xprop_actual, xprop_exp = xprop.split("=")
                            xprop_actual = xprop_actual.split('(')[0] or  xprop_actual.split(' (')[0] or xprop_actual.split(' ')[0] or "None"
                            xprop_exp = xprop_exp.split(")")[0] or xprop_exp.split(" )")[0] or "None"

                            if xprop_exp == "none":
                                xprop_exp = "None"
                            if xprop_actual == "none":
                                xprop_actual = "None"

                            #props.append({"Message":xprop_msg,"Status":xstatus,"Expected":xprop_exp , "Actual":xprop_actual })
                            xporp_act_msg = xprop_msg.replace('NoName@','').replace("NoName",'').replace('@','.')
                            props.append({"Message":xporp_act_msg,"Status":xstatus,"Expected":xprop_exp , "Actual":xprop_actual })

                        self.realtime_results['vc']['checks'].append({'Message':check_function.descr ,'Status': (passed and "PASS" or "FAIL"),"Properties": props})
                        with open("display_json.json", "w") as myfile:
                            json.dump(self.realtime_results, myfile)
                    except:
                        pass
                    #self.result.add_check_result(CheckerResult(check_function.descr, None, passed, message, check_function.category, path,check_function.expected_result))
                    if passed:
                        self.result.add_check_result(CheckerResult(check_function.descr, None, passed, message, check_function.category, path, check_function.expected_result))
                    else:
                        print "GAMGAM :", check_function.descr, self.knowledge_pool.get(check_function.descr, None)
                        self.result.add_check_result(CheckerResult(check_function.descr, None, passed, message, check_function.category, path, check_function.expected_result, self.knowledge_pool.get(check_function.descr, None)))

                    passed_all = passed_all and passed
            self.reporter.notify_progress(self.reporter.notify_checkName,"")

        Disconnect(self.si)
        VCChecker.resource_pool_config={}
        VCChecker.vcenter_stats_config={}
        VCChecker.responseHostsJson={}
        VCChecker.responseClusterJson={}
        VCChecker.vcenter_server_ssh = None
        VCChecker.esxi_ssh = None
        VCChecker.ipmi_ssh = None
        VCChecker.cvm_ssh = None

        self.result.passed = ( passed_all and "PASS" or "FAIL" )
        self.result.message = "VC Checks completed with " + (passed_all and "success" or "failure")
        self.reporter.notify_progress(self.reporter.notify_info,"VC Checks complete")
        return self.result, "Complete"


    def validate_vc_property(self, path, operator, expected):

        props = self.get_vc_property(path)
        message_all = ""
        passed_all = True

#         if props == None:
#             passed =  VCChecker.apply_operator(props, expected, operator)
#             message = path + "=" + "None" + " (Expected: " + operator + expected + ") "
#             message_all += (", "+message+"#"+(passed and "PASS" or "FAIL")) 
#             passed_all = passed_all and passed
#             self.reporter.notify_progress(self.reporter.notify_checkLog, message, passed and "PASS" or "FAIL")
#             return False, message_all

        if expected.startswith("content"):
            # Reference to another object
            expected_props = self.get_vc_property(expected)

        for path, property in props.iteritems():
            expected_val = expected
            if expected.startswith("content"):
                expected_val = str(expected_props[path])

            passed = VCChecker.apply_operator(property, expected_val, operator)
            passed_all = passed_all and passed
            if isinstance(property, list):
                property = ','.join(property)
            message = path + "=" + str(property) + " (Expected: " + operator + expected_val + ") "
            #if not passed:
            #    message_all += ("," + message)
            self.reporter.notify_progress(self.reporter.notify_checkLog,message, passed and "PASS" or "FAIL")
            message_all += (", "+message+"#"+(passed and "PASS" or "FAIL")) 
        if passed_all:
            return True, message_all
        else:
            return False, message_all

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
        elif operator == "!=":
            return expected != str(actual)
        # Handle others operators as needed
        else:
            raise RuntimeError("Unexpected operator " + operator)


    def matches_filter(self, xpath, cur_obj, expected, filter_names,filter_operator):
        try:
            attr = getattr(cur_obj, xpath[0])
        except AttributeError:
            return {}
        except:
            print "Unknow error"   

        if hasattr(cur_obj, "name"):
            filter_names.append(cur_obj.name)

        if len(xpath) == 1:
            if filter_operator == '=':
                for expected_val in expected.split(','):
                    if fnmatch.fnmatch(attr, expected_val):
                        return True
                return False
            elif filter_operator == '!=':
                for expected_val in expected.split(','):
                    if not fnmatch.fnmatch(attr, expected_val):
                        return True
                return False

        if isinstance(attr, list):
            matches = True
            for item in attr:
                matches = matches and self.matches_filter(xpath[1:], item, expected, filter_names,filter_operator)
            return matches
        else:
            return self.matches_filter(xpath[1:], attr, expected, filter_names,filter_operator)

    def apply_filter(self, cur_obj, filter, filter_names):
        if filter is None:
            return True
        if'!=' in filter:
            filter_prop, filter_val = filter.split("!=")
            filter_operator = '!='
        elif '=' in filter:    
            filter_prop, filter_val = filter.split("=")
            filter_operator = '=' 
        filter_prop_xpath = string.split(filter_prop, '-')

        return self.matches_filter(filter_prop_xpath, cur_obj, filter_val, filter_names, filter_operator)

    def retrieve_vc_property(self, xpath, cur_obj, name, cluster_level_entity=False):
        if "[" in xpath[0]:
            node,filter = xpath[0].split("[")
            filter = filter[:-1]
        else:
            node = xpath[0]
            filter = None

        if node == "hostFolder":
            cluster_level_entity = True

        if node == "childEntity" and cluster_level_entity:
            if self.authconfig['cluster'] != "":
                filter = "name="+self.authconfig['cluster']
        if node == "host":
            if self.authconfig['host'] != "":
                filter = "name="+self.authconfig['host']
        try:
            attr = getattr(cur_obj, node)
        except AttributeError:
            return {"@".join(name): "Not-Configured"}
        except:
            return {"@".join(name): "Not-Configured"}

        name_added = False
        if hasattr(cur_obj, "name"):  #and cur_obj.name not in name:
            name.append(cur_obj.name)
            name_added = True
        else:
            name.append("NoName")

        if len(xpath) == 1:
            return {"@".join(name): attr}

        if isinstance(attr, list):
            vals = {}
            for item in attr:
                filter_names = []
                filter_pass = self.apply_filter(item, filter, filter_names)

                if filter_pass:
                    attr_val = self.retrieve_vc_property(xpath[1:], item, name + filter_names,cluster_level_entity)
                    if attr_val:
                        vals.update(attr_val)
#             if name_added:
#                 name.pop()
            if vals == {}:
                vals={"@".join(name): "Not-Configured"}
            return vals
        else:
            filter_names = []
            filter_pass = self.apply_filter(attr, filter, filter_names)
            result = filter_pass and self.retrieve_vc_property(xpath[1:], attr, name + filter_names,cluster_level_entity) or None
#             if name_added:
#                 name.pop()
            return result


    def get_vc_property(self, path):
        return self.retrieve_vc_property(string.split(path, '.'), self.si, [])


    # Manual checks

    @checkgroup("cluster_checks", "Cluster Advance Settings das.ignoreInsufficientHbDatastore", ["availability","post-install"], "True")
    def check_cluster_das_ignoreInsufficientHbDatastore(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_cluster_das_ignoreInsufficientHbDatastore - Enter")
        path = 'content.rootFolder.childEntity.hostFolder.childEntity'
        cluster_map = self.get_vc_property(path)
        passed = True
        message = ""
        message_all = ""
        for clusters_key, clusters in cluster_map.iteritems():
            if clusters!="Not-Configured":
                for cluster in clusters:
                    cluster_name=cluster.name

                    if self.authconfig['cluster']!='':
                        if cluster_name not in self.authconfig['cluster']:
                            #print "skipping "+cluster_name
                            continue

                    if not isinstance(cluster, vim.ClusterComputeResource):
                        #condition to check if any host attached to datacenter without adding to any cluster
                        continue

                    heartbeatDatastoreInfos=cluster.RetrieveDasAdvancedRuntimeInfo.__call__().heartbeatDatastoreInfo
                    if len(heartbeatDatastoreInfos)>=1:
                        is_option_set=False
                        for option in cluster.configuration.dasConfig.option:
                            if option.key=="das.ignoreInsufficientHbDatastore":
                                #print cluster_name , option.value
                                passed = False
                                if option.value=='true':
                                    self.reporter.notify_progress(self.reporter.notify_checkLog,  clusters_key  +'@'+cluster_name+ "=true (Expected: =true)", (True and "PASS" or "FAIL"))
                                    message += ", "+clusters_key  +'@'+cluster_name+ "=true (Expected: =true)#"+(True and "PASS" or "FAIL")
                                else:
                                    self.reporter.notify_progress(self.reporter.notify_checkLog,  clusters_key  +'@'+cluster_name+ "=false (Expected: =true)", (False and "PASS" or "FAIL"))
                                    message += ", "+clusters_key  +'@'+cluster_name+ "=false (Expected: =true)#"+(False and "PASS" or "FAIL")
                                is_option_set=True
                                break

                        if is_option_set == False:
                            passed = False
                            self.reporter.notify_progress(self.reporter.notify_checkLog, clusters_key + '@' + cluster_name + "=Not-Configured (Expected: =true)", (False and "PASS" or "FAIL"))
                            message += ", "+clusters_key +"=Not-Configured (Expected: =true)#"+(False and "PASS" or "FAIL")

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_cluster_das_ignoreInsufficientHbDatastore - Exit")
        return passed, message,path


    @checkgroup("cluster_checks", "Validate Datastore Heartbeat", ["availability"],"Heatbeat Datastore Name")
    def check_datastore_heartbeat(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_datastore_heartbeat - Enter")
        path = 'content.rootFolder.childEntity.hostFolder.childEntity'
        cluster_map=self.get_vc_property(path)
        passed = True
        message = ""
        message_all = ""
        for clusters_key, clusters in cluster_map.iteritems():
            if clusters!="Not-Configured":
                for cluster in clusters:
                    cluster_name=cluster.name

                    if self.authconfig['cluster'] !='':
                        if cluster_name not in self.authconfig['cluster']:
                            #print "skipping "+cluster_name
                            continue

                    if not isinstance(cluster, vim.ClusterComputeResource):
                        #condition to check if any host attached to datacenter without adding to any cluster
                        continue
                    heartbeatDatastoreInfos=cluster.RetrieveDasAdvancedRuntimeInfo.__call__().heartbeatDatastoreInfo
                    if len(heartbeatDatastoreInfos)==0:
                        passed = False
                        self.reporter.notify_progress(self.reporter.notify_checkLog,clusters_key+"@"+cluster_name+"=Not-Configured (Expected: =Datastore Name) " , (False and "PASS" or "FAIL"))
                        message += ", " +clusters_key+"@"+cluster_name+"=Not-Configured (Expected: =Datastore Name) "+"#"+(False and "PASS" or "FAIL")
                    else:
                        datastore_names=[]
                        for heartbeatDatastoreInfo in heartbeatDatastoreInfos:
                            datastore_names.append(heartbeatDatastoreInfo.datastore.name)
                        names=','.join(datastore_names)
                        self.reporter.notify_progress(self.reporter.notify_checkLog,clusters_key+"@"+cluster_name+"="+names+" (Expected: =Datastore Name) " , (True and "PASS" or "FAIL"))
                        message += ", " +clusters_key+"@"+cluster_name+"="+names+" (Expected: =Datastore Name) "+"#"+(True and "PASS" or "FAIL")

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_datastore_heartbeat - Exit")
        return passed, message,path


    @checkgroup("cluster_checks", "VSphere Cluster Nodes in Same Version", ["availability"],"All Nodes in Same Version")
    def check_vSphere_cluster_nodes_in_same_version(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_vSphere_cluster_nodes_in_same_version - Enter")
        path='content.rootFolder.childEntity'
        root = self.get_vc_property(path) or {}
        message = ""
        passed_all = True

        for dc, dcInfo in root.iteritems():
            for xdc in dcInfo:
                for xcluster in xdc.hostFolder.childEntity:
                    if self.authconfig['cluster']!='':
                        if xcluster.name not in self.authconfig['cluster']:
                            #print "skipping "+xcluster.name
                            continue
                    passed = True
                    mult_vers_flag, versions = False, [] 
                    hosts = xcluster.host

                    for xhost in hosts:
                        nodeInfo = xhost.config.product 
                        if len(versions) == 0:
                            versions.append(nodeInfo.version)
                        else:
                            if nodeInfo.version not in versions:
                                passed = False
                                versions.append(nodeInfo.version)
                                mult_vers_flag = True

                    if len(versions) == 0: # to test weather any HOST configured to cluster
                        mult_vers_flag = True
                        versions = "Not-Configured"

                    self.reporter.notify_progress(self.reporter.notify_checkLog,"Datacenters."+xdc.name+"."+xcluster.name + "=" + str(versions) + " (Expected: =Multiple versions not present) " , (not mult_vers_flag and "PASS" or "FAIL"))
                    message += ", "+"@Datacenters@"+xdc.name+"@"+xcluster.name + "="+str(versions)+" (Expected: =Multiple versions not present)#"+(not mult_vers_flag and "PASS" or "FAIL")   
                    passed_all = passed_all and passed    

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_vSphere_cluster_nodes_in_same_version - Exit")
        return passed_all, message,path

    @checkgroup("cluster_checks", "Cluster Advance Settings das.isolationaddress1", ["availability","post-install"],"IP Address of any Nutanix CVM")
    def check_cluster_das_isolationaddress1(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_cluster_das_isolationaddress1 - Enter")
        path = 'content.rootFolder.childEntity.hostFolder.childEntity'
        all_cluster = self.get_vc_property(path) or {}
        message = ""
        passed_all = True
        passed = False
        for datacenter, clusters in all_cluster.iteritems():
            try:
                if len(clusters)==0:
                    raise AttributeError

                for cluster in clusters:
                    passed = False
                    cluster_name=cluster.name

                    if self.authconfig['cluster']!='':
                        if cluster_name not in self.authconfig['cluster']:
                            #print "skipping "+cluster_name
                            continue

                    nics=self.get_vc_property('content.rootFolder.childEntity.hostFolder.childEntity[name=' + cluster_name + '].configurationEx.dasVmConfig.key[name=NTNX*CVM].guest.net')
                    cluster_all_ips = []
                    cluster_str = ''
                    for nic, nicInfo in nics.iteritems():
                        if nicInfo != 'Not-Configured': 
                            cluster_all_ips.extend(nicInfo[0].ipAddress)
                    for item in cluster_all_ips:
                        cluster_str += item + " "

                    options = cluster.configuration.dasConfig.option
                    if len(options) != 0:
                        has_isolationaddress1 = False
                        isolationaddress1 = None
                        for option in options:
                            if option.key == 'das.isolationaddress1':
                                has_isolationaddress1 = True
                                #print cluster_name, option.key, option.value
                                isolationaddress1 = option.value
                                passed = isolationaddress1 in cluster_all_ips
                                self.reporter.notify_progress(self.reporter.notify_checkLog,  datacenter +"@"+cluster_name+ "=" + str(isolationaddress1) + "(Expected: =Among:"+str(cluster_all_ips)+")", (passed and "PASS" or "FAIL"))
                                message += ", "+datacenter +"@"+cluster_name+"="+str(isolationaddress1)+" (Expected: =Among:["+cluster_str+"])#"+(passed and "PASS" or "FAIL")
                            if has_isolationaddress1 == True:
                                if option.key == 'das.isolationaddress2' or option.key == 'das.isolationaddress3':
                                    if isolationaddress1 == option.value:
                                        passed_all = False
                                        self.reporter.notify_progress(self.reporter.notify_checkLog, datacenter +"@"+cluster_name+ "=Advance setting has duplicated value with das.isolationaddress2 or das.isolationaddress3  (Expected: =Among:"+str(cluster_all_ips)+")", (False and "PASS" or "FAIL"))
                                        message += ", "+datacenter +"@"+cluster_name+"=Advance setting has duplicated value with das.isolationaddress2 or das.isolationaddress3 (Expected: =Among:["+cluster_str+"])#"+(False and "PASS" or "FAIL")

                        if has_isolationaddress1 == False:
                            passed_all = False
                            self.reporter.notify_progress(self.reporter.notify_checkLog, datacenter +"@"+cluster_name+ "=Not-Configured (Expected: =Among:"+str(cluster_all_ips)+")", (False and "PASS" or "FAIL"))
                            message += ", "+datacenter +"@"+cluster_name+"=Not-Configured (Expected: =Among:["+cluster_str+"])#"+(False and "PASS" or "FAIL")
                    else:
                        passed_all=False
                        self.reporter.notify_progress(self.reporter.notify_checkLog, datacenter +"@"+cluster_name+ "=Not-Configured (Expected: =Among:"+str(cluster_all_ips)+")", (False and "PASS" or "FAIL"))
                        message += ", "+datacenter +"@"+cluster_name+"=Not-Configured (Expected: =Among:["+cluster_str+"])#"+(False and "PASS" or "FAIL")

            except AttributeError:
                passed_all = False
                self.reporter.notify_progress(self.reporter.notify_checkLog, datacenter +"@"+ "=Not-Configured (Expected: =IP Address of any Nutanix CVM)", (False and "PASS" or "FAIL"))
                message += ", "+datacenter +"@"+"=Not-Configured (Expected: =IP Address of any Nutanix CVM)#"+(False and "PASS" or "FAIL")
            passed_all = passed_all and passed

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_cluster_das_isolationaddress1 - Exit")
        return passed_all, message, path

    @checkgroup("cluster_checks", "Cluster Advance Settings das.isolationaddress2", ["availability"], "IP Address of any Nutanix CVM")
    def check_cluster_das_isolationaddress2(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_cluster_das_isolationaddress2 - Enter")
        path='content.rootFolder.childEntity.hostFolder.childEntity'
        all_cluster = self.get_vc_property(path) or {}
        message = ""
        passed_all = True
        passed = False
        for datacenter, clusters in all_cluster.iteritems():
            try:
                if len(clusters)==0:
                    raise AttributeError
                for cluster in clusters:
                    passed = False
                    cluster_name=cluster.name

                    if self.authconfig['cluster']!='':
                        if cluster_name not in self.authconfig['cluster']:
                            #print "skipping "+cluster_name
                            continue

                    nics = self.get_vc_property('content.rootFolder.childEntity.hostFolder.childEntity[name='+cluster_name+'].configurationEx.dasVmConfig.key[name=NTNX*CVM].guest.net')
                    cluster_all_ips = []
                    cluster_str = ''
                    for nic, nicInfo in nics.iteritems():
                        if nicInfo != 'Not-Configured': 
                            cluster_all_ips.extend(nicInfo[0].ipAddress)
                    for item in cluster_all_ips:
                        cluster_str += item + " "

                    options=cluster.configuration.dasConfig.option
                    if len(options) != 0:
                        has_isolationaddress2 = False
                        isolationaddress2 = None
                        for option in options:
                            if option.key == 'das.isolationaddress2':
                                has_isolationaddress2 = True
                                #print cluster_name, option.key, option.value
                                isolationaddress2 = option.value
                                passed = isolationaddress2 in cluster_all_ips
                                self.reporter.notify_progress(self.reporter.notify_checkLog,  datacenter +"@"+cluster_name+ "=" + str(isolationaddress2) + "(Expected: =Among:"+str(cluster_all_ips)+")", (passed and "PASS" or "FAIL"))
                                message += ", "+datacenter +"@"+cluster_name+"="+str(isolationaddress2)+" (Expected: =Among:["+cluster_str+"])#"+(passed and "PASS" or "FAIL")

                            if has_isolationaddress2 == True:
                                if option.key == 'das.isolationaddress1' or option.key == 'das.isolationaddress3':
                                    if isolationaddress2 == option.value:
                                        passed_all = False
                                        self.reporter.notify_progress(self.reporter.notify_checkLog, datacenter +"@"+cluster_name+ "=Advance setting has duplicated value with das.isolationaddress1 or das.isolationaddress3  (Expected: =Among:"+str(cluster_all_ips)+")", (False and "PASS" or "FAIL"))
                                        message += ", "+datacenter +"@"+cluster_name+"=Advance setting has duplicated value with das.isolationaddress1 or das.isolationaddress3 (Expected: =Among:["+cluster_str+"])#"+(False and "PASS" or "FAIL")

                        if has_isolationaddress2 == False:
                            passed_all = False
                            self.reporter.notify_progress(self.reporter.notify_checkLog, datacenter +"@"+cluster_name+ "=Not-Configured (Expected: =Among:"+str(cluster_all_ips)+")", (False and "PASS" or "FAIL"))
                            message += ", "+datacenter +"@"+cluster_name+"=Not-Configured (Expected: =Among:["+cluster_str+"])#"+(False and "PASS" or "FAIL")
                    else:
                        self.reporter.notify_progress(self.reporter.notify_checkLog, datacenter +"@"+cluster_name+ "=Not-Configured (Expected: =Among:"+str(cluster_all_ips)+")", (False and "PASS" or "FAIL"))
                        message += ", "+datacenter +"@"+cluster_name+"=Not-Configured (Expected: =Among:["+cluster_str+"])#"+(False and "PASS" or "FAIL")

            except AttributeError:
                passed_all = False
                self.reporter.notify_progress(self.reporter.notify_checkLog, datacenter +"@"+ "=Not-Configured (Expected: =IP Address of any Nutanix CVM)", (False and "PASS" or "FAIL"))
                message += ", "+datacenter +"@"+"=Not-Configured (Expected: =IP Address of any Nutanix CVM)#"+(False and "PASS" or "FAIL")

            passed_all = passed_all and passed
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_cluster_das_isolationaddress2 - Exit")
        return passed_all , message,path

    @checkgroup("cluster_checks", "Cluster Advance Settings das.isolationaddress3",["availability"],"IP Address of any Nutanix CVM")
    def check_cluster_das_isolationaddress3(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_cluster_das_isolationaddress3 - Enter")
        path = 'content.rootFolder.childEntity.hostFolder.childEntity'
        all_cluster = self.get_vc_property(path) or {}
        message = ""
        passed_all = True
        passed = False
        for datacenter, clusters in all_cluster.iteritems():
            try:
                if len(clusters) == 0:
                    raise AttributeError
                for cluster in clusters:
                    passed = False
                    cluster_name=cluster.name

                    if self.authconfig['cluster']!='':
                        if cluster_name not in self.authconfig['cluster']:
                            #print "skipping "+cluster_name
                            continue

                    nics = self.get_vc_property('content.rootFolder.childEntity.hostFolder.childEntity[name='+cluster_name+'].configurationEx.dasVmConfig.key[name=NTNX*CVM].guest.net')
                    cluster_all_ips = []
                    cluster_str = ''
                    for nic, nicInfo in nics.iteritems():
                        if nicInfo != 'Not-Configured': 
                            cluster_all_ips.extend(nicInfo[0].ipAddress)
                    for item in cluster_all_ips:
                        cluster_str += item + " "

                    options = cluster.configuration.dasConfig.option
                    if len(options) != 0:
                        has_isolationaddress3 = False
                        isolationaddress3 = None
                        for option in options:
                            if option.key == 'das.isolationaddress3':
                                has_isolationaddress3 = True
                                #print cluster_name, option.key, option.value
                                isolationaddress3 = option.value
                                passed = isolationaddress3 in cluster_all_ips
                                self.reporter.notify_progress(self.reporter.notify_checkLog,  datacenter +"@"+cluster_name+ "=" + str(isolationaddress3) + "(Expected: =Among:"+str(cluster_all_ips)+")", (passed and "PASS" or "FAIL"))
                                message += ", "+datacenter +"@"+cluster_name+"="+str(isolationaddress3)+" (Expected: =Among:["+cluster_str+"])#"+(passed and "PASS" or "FAIL")

                            if has_isolationaddress3==True:
                                if option.key == 'das.isolationaddress1' or option.key == 'das.isolationaddress2':
                                    if isolationaddress3 == option.value:
                                        passed_all = False
                                        self.reporter.notify_progress(self.reporter.notify_checkLog, datacenter +"@"+cluster_name+ "=Advance setting has duplicated value with das.isolationaddress1 or das.isolationaddress3  (Expected: =Among:"+str(cluster_all_ips)+")", (False and "PASS" or "FAIL"))
                                        message += ", "+datacenter +"@"+cluster_name+"=Advance setting has duplicated value with das.isolationaddress1 or das.isolationaddress2 (Expected: =Among:["+cluster_str+"])#"+(False and "PASS" or "FAIL")

                        if has_isolationaddress3 == False:
                            passed_all = False
                            self.reporter.notify_progress(self.reporter.notify_checkLog, datacenter +"@"+cluster_name+ "=Not-Configured (Expected: =Among:"+str(cluster_all_ips)+")", (False and "PASS" or "FAIL"))
                            message += ", "+datacenter +"@"+cluster_name+"=Not-Configured (Expected: =Among:["+cluster_str+"])#"+(False and "PASS" or "FAIL")
                    else:
                        self.reporter.notify_progress(self.reporter.notify_checkLog, datacenter +"@"+cluster_name+ "=Not-Configured (Expected: =Among:"+str(cluster_all_ips)+")", (False and "PASS" or "FAIL"))
                        message += ", "+datacenter +"@"+cluster_name+"=Not-Configured (Expected: =Among:["+cluster_str+"])#"+(False and "PASS" or "FAIL")

            except AttributeError:
                passed_all = False
                self.reporter.notify_progress(self.reporter.notify_checkLog, datacenter +"@"+ "=Not-Configured (Expected: =IP Address of any Nutanix CVM)", (False and "PASS" or "FAIL"))
                message += ", "+datacenter +"@"+"=Not-Configured (Expected: =IP Address of any Nutanix CVM)#"+(False and "PASS" or "FAIL")

            passed_all = passed_all and passed
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_cluster_das_isolationaddress3 - Exit")
        return passed_all, message,path
 

    @checkgroup("cluster_checks", "Cluster Load Balanced", ["performance"], "Load Balanced")
    def check_cluster_load_balanced(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_cluster_load_balanced - Enter")
        path_curr = 'content.rootFolder.childEntity.hostFolder.childEntity.summary.currentBalance'
        current_balance = self.get_vc_property(path_curr)
        path_tar = 'content.rootFolder.childEntity.hostFolder.childEntity.summary.targetBalance'
        target_balance = self.get_vc_property(path_tar)
        message = ""
        passed_all = True

        for current_key in current_balance:
            passed = True
            if (current_balance[current_key]<=target_balance[current_key]) and (current_balance[current_key] != -1000) and (target_balance[current_key]!=-1000) and (current_balance[current_key] != "Not-Configured") and (target_balance[current_key]!="Not-Configured") :
                self.reporter.notify_progress(self.reporter.notify_checkLog,  current_key + "="+str(current_balance[current_key])+" (Expected: =Less than "+str(target_balance[current_key])+" )", ("PASS"))
                message += ", "+current_key + "="+str(current_balance[current_key])+" (Expected: =Less than "+str(target_balance[current_key])+")#PASS"
            else:
                cur_bal= "NA" if current_balance[current_key]== -1000 else current_balance[current_key]
                tar_bal= "NA"if (target_balance[current_key]==-1000 or target_balance[current_key]=="Not-Configured") else target_balance[current_key]  
                self.reporter.notify_progress(self.reporter.notify_checkLog, current_key + "="+str(cur_bal)+" (Expected: =Less than "+str(tar_bal)+" )", ("FAIL"))
                message += ", "+current_key + "="+str(cur_bal)+" (Expected: =Less than "+str(tar_bal)+")#FAIL"             
            passed_all = passed_all and passed

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_cluster_load_balanced - Exit")                                                                                                                                                      
        return passed_all , message,path_curr

    @checkgroup("cluster_checks", "Storage DRS", ["performance"], "False")
    def check_cluster_storgae_drs(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_cluster_storgae_drs - Enter")
        path_curr='content.rootFolder.childEntity.datastoreFolder.childEntity'
        storage_clusters_map = self.get_vc_property(path_curr)

        message = ""
        passed_all = True

        for datacenter, storage_clusters in storage_clusters_map.iteritems():
            passed = True
            if storage_clusters == "Not-Configured":
                continue
            storage_clusters_found = False
            ntnx_datastore_found = False
            storage_cluster_name = None
            for storage_cluster in storage_clusters:
                if not isinstance(storage_cluster, vim.StoragePod):
                    continue

                storage_clusters_found = True
                storage_cluster_name = storage_cluster.name
                for datastore in storage_cluster.childEntity:
                    datastore_name = datastore.name
                    if not fnmatch.fnmatch(datastore_name,"NTNX-local-ds*"):
                        #condition to check if NTNX-local name of Datastore found
                        #if not found skip check
                        continue
                    ntnx_datastore_found = True
                    mount_remote_host = datastore.info.nas.remoteHost

                    if mount_remote_host != "192.168.5.2":
                        # condition to check if NTNX-local datastore mounted to 192.168.5.2
                        # if not mounted then skip check
                        continue

                    storage_drs = storage_cluster.podStorageDrsEntry.storageDrsConfig.podConfig.enabled
                    self.reporter.notify_progress(self.reporter.notify_checkLog, datacenter +"@"+storage_cluster_name+"@"+datastore_name+"="+str(storage_drs)+" (Expected: =false)", ((not storage_drs) and "PASS" or "FAIL"))
                    message += ", "+datacenter +"@"+storage_cluster_name+"@"+datastore_name+ "="+str(storage_drs)+" (Expected: =false)#"+((not storage_drs) and "PASS" or "FAIL")            

            if storage_clusters_found == False:
                self.reporter.notify_progress(self.reporter.notify_checkLog, datacenter + "=Storage-Cluster-not-found (Expected: =false)", (False and "PASS" or "FAIL"))
                message += ", "+datacenter + "=No-Storage-Cluster-found (Expected: =false)#"+(False and "PASS" or "FAIL")
                passed = False
            elif ntnx_datastore_found == False:
                self.reporter.notify_progress(self.reporter.notify_checkLog, datacenter + "@"+storage_cluster_name+"=NTNX-Datastore-not-found (Expected: =false)", (True and "PASS" or "FAIL"))
                message += ", "+datacenter +"@"+storage_cluster_name+ "=NTNX-Datastore-not-found (Expected: =false)#"+(True and "PASS" or "FAIL")
                passed=False

            passed_all = passed_all and passed
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_cluster_storgae_drs - Exit")                                                                                                                                                      
        return passed_all , message,path_curr+".datastore"

    @checkgroup("cluster_checks", "Number of DRS Faults", ["performance"],"Number of DRS Faults")
    def check_cluster_drs_fault_count(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_cluster_drs_fault_count - Enter")
        path_curr = 'content.rootFolder.childEntity.hostFolder.childEntity.drsFault'
        clusters_map = self.get_vc_property(path_curr)
        message = ""
        passed_all = True

        for datacenter, clusters_drs_faults in clusters_map.iteritems():
            if clusters_drs_faults == "Not-Configured":
                continue
            count = len(clusters_drs_faults) if clusters_drs_faults !=None else 0
            self.reporter.notify_progress(self.reporter.notify_checkLog, datacenter + "="+str(count)+" (Expected: =0)", ((True if count ==0 else False) and "PASS" or "FAIL"))
            message += ", "+datacenter + "="+str(count)+" (Expected: =0)#"+((True if count ==0 else False) and "PASS" or "FAIL") 
            passed = (True if count ==0 else False)
            passed_all = passed_all and passed

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_cluster_drs_fault_count - Exit")
        return passed_all , message,path_curr

    @checkgroup("cluster_checks", "Number of Cluster Events", ["availability","manageability"], "Number of Cluster Events")
    def check_cluster_events_count(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_cluster_events_count - Enter")
        path_curr='content.rootFolder.childEntity.hostFolder.childEntity.configIssue'
        clusters_map = self.get_vc_property(path_curr)
        message = ""
        passed_all = True

        for datacenter, clusters_events in clusters_map.iteritems():
            if clusters_events == "Not-Configured":
                continue

            count = len(clusters_events) if clusters_events !=None else 0
            self.reporter.notify_progress(self.reporter.notify_checkLog, datacenter + "="+str(count)+" (Expected: =0)", ((True if count ==0 else False) and "PASS" or "FAIL"))
            message += ", "+datacenter + "="+str(count)+" (Expected: =0)#"+((True if count ==0 else False) and "PASS" or "FAIL") 
            passed = (True if count ==0 else False)
            passed_all = passed_all and passed

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_cluster_events_count - Exit")
        return passed_all , message,path_curr    

    @checkgroup("cluster_checks", "Cluster Memory Utilization %", ["performance"], "Memory Consumed %")
    def check_cluster_memory_utilization(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_cluster_memory_utilization - Enter")
        path = 'content.rootFolder.childEntity.hostFolder.childEntity.summary'
        clusters_summary = self.get_vc_property(path)
        message = ""
        passed_all = True

        for clusters_key, clusters_summ in clusters_summary.iteritems():
            if clusters_summ == "Not-Configured":
                continue
            passed = True
            effectiveMemory = clusters_summ.effectiveMemory
            totalMemory = clusters_summ.totalMemory

            if totalMemory > 0:
                effectiveMemory_to_bytes = effectiveMemory* 1000000 # converting to bytes
                cpu_utilization_percentage = round((effectiveMemory_to_bytes*100)/totalMemory, 2)
                self.reporter.notify_progress(self.reporter.notify_checkLog, clusters_key + "="+str(cpu_utilization_percentage)+"% (Expected: =memory-consumed-%)", (True and "PASS" or "FAIL"))
                message += ", "+clusters_key + "="+str(cpu_utilization_percentage)+"% (Expected: =memory-consumed-%)#"+(True and "PASS" or "FAIL")
            else:
                passed = False
                self.reporter.notify_progress(self.reporter.notify_checkLog, clusters_key + "=total_memory_is_zero (Expected: =memory-consumed-%)", (False and "PASS" or "FAIL"))
                message += ", "+clusters_key + "=total_memory_is_zero (Expected: =memory-consumed-%)#"+(False and "PASS" or "FAIL")

            passed_all = passed_all and passed
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_cluster_memory_utilization - Exit")
        return passed_all , message,path

    @checkgroup("cluster_checks", "Cluster Memory Overcommitment",["performance"],"Memory Oversubscrption %")
    def check_cluster_memory_overcommitment(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_cluster_memory_overcommitment - Enter")
        path = 'content.rootFolder.childEntity.hostFolder.childEntity'
        clusters_map = self.get_vc_property(path)
        message = ""
        passed_all = True

        for clusters_key, clusters in clusters_map.iteritems():
            passed = True
            for cluster in clusters:
                cluster_name= cluster.name
                if self.authconfig['cluster']!='':
                        if cluster_name not in self.authconfig['cluster']:
                            #print "skipping "+cluster_name
                            continue

                cluster_total_memory=cluster.summary.totalMemory
                vRam=0
                for host in cluster.host:
                    for vm in host.vm:
                        vRam+= 0  if vm.summary.config.memorySizeMB == None else vm.summary.config.memorySizeMB
                vRam=vRam*1000000
                if cluster_total_memory >0:
                    #cluster_total_memory=(cluster_total_memory/1024)/1024
                    memory_overcommitment = round((vRam/cluster_total_memory), 2) 
                    memory_overcommitment_percentage= (memory_overcommitment*100)%100
                    #print   cluster_name,   cluster_total_memory , vRam , memory_overcommitment, memory_overcommitment_percentage
                    self.reporter.notify_progress(self.reporter.notify_checkLog, clusters_key+"@" +cluster_name+ "="+str(memory_overcommitment_percentage)+"% (Expected: =memory-oversubscrption-%)", (True and "PASS" or "FAIL"))
                    message += ", "+clusters_key+"@" +cluster_name+ "="+str(memory_overcommitment_percentage)+"% (Expected: =memory-oversubscrption-%)#"+(True and "PASS" or "FAIL")
                else:
                    passed = False
                    self.reporter.notify_progress(self.reporter.notify_checkLog, clusters_key+"@" +cluster_name+ "=total_memory_is_zero (Expected: =memory-oversubscrption-%)", (False and "PASS" or "FAIL"))
                    message += ", "+clusters_key+"@" +cluster_name+ "=total_memory_is_zero (Expected: =memory-oversubscrption-%)#"+(False and "PASS" or "FAIL")
        passed_all = passed_all and passed
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_cluster_memory_overcommitment - Exit")
        return passed_all , message,path

    @checkgroup("cluster_checks", "Ratio pCPU/vCPU",["performance"],"pCPU/vCPU ratio")
    def check_cluster_ratio_pCPU_vCPU(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_cluster_ratio_pCPU_vCPU - Enter")
        path='content.rootFolder.childEntity.hostFolder.childEntity'
        clusters_map= self.get_vc_property(path)
        message = ""
        passed_all = True

        for clusters_key, clusters in clusters_map.iteritems():
            passed = True
            for cluster in clusters:
                cluster_name= cluster.name
                if self.authconfig['cluster']!='':
                        if cluster_name not in self.authconfig['cluster']:
                            #print "skipping "+cluster_name
                            continue

                numCpuCores=cluster.summary.numCpuCores
                pCPU=round(numCpuCores+numCpuCores*.3)
                vCPU=0
                for host in cluster.host:
                    for vm in host.vm:
                        vCPU+= 0 if vm.summary.config.numCpu == None else vm.summary.config.numCpu

                if pCPU > 0:
                    ratio= "1:"+str(int(round(vCPU/pCPU)))
                    self.reporter.notify_progress(self.reporter.notify_checkLog, clusters_key+"@" +cluster_name+ "="+str(ratio)+" (Expected: =pCPU/vCPU)", (True and "PASS" or "FAIL"))
                    message += ", "+clusters_key+"@" +cluster_name+ "="+str(ratio)+" (Expected: =pCPU/vCPU)#"+(True and "PASS" or "FAIL")
                else:
                    passed = False
                    self.reporter.notify_progress(self.reporter.notify_checkLog, clusters_key+"@" +cluster_name+ "=pCPU_is_zero (Expected: =pCPU/vCPU)", (False and "PASS" or "FAIL"))
                    message += ", "+clusters_key+"@" +cluster_name+ "=pCPU_is_zero (Expected: =pCPU/vCPU)#"+(False and "PASS" or "FAIL")
                passed_all = passed_all and passed

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_cluster_ratio_pCPU_vCPU - Exit")
        return passed_all, message, path

    @checkgroup("cluster_checks", "Admission Control Policy - Percentage Based on Nodes in the Cluster", ["performance","availability"],"True")
    def check_cluster_acpPercentage_basedOn_nodes(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_cluster_acpPercentage_basedOn_nodes - Enter")
        path = 'content.rootFolder.childEntity.hostFolder.childEntity'
        clusters_map = self.get_vc_property(path)
        message = ""
        passed_all = True

        for clusters_key, clusters in clusters_map.iteritems():
            passed = True
            if clusters == "Not-Configured":
                continue

            for cluster in clusters:
                if not isinstance(cluster, vim.ClusterComputeResource):
                    #condition to check if host directly attached to cluster
                    continue
                cluster_name= cluster.name
                if self.authconfig['cluster']!='':
                        if cluster_name not in self.authconfig['cluster']:
                            #print "skipping "+cluster_name
                            continue

                acp_enabled = cluster.configuration.dasConfig.admissionControlEnabled
                if not acp_enabled:
                    passed = False
                    self.reporter.notify_progress(self.reporter.notify_checkLog, clusters_key+"@" +cluster_name+ "=ACP is disabled (Expected: =true)", (False and "PASS" or "FAIL"))
                    message += ", "+clusters_key+"@" +cluster_name+ "=ACP is disabled (Expected: =true)#"+(False and "PASS" or "FAIL")
                    continue

                admissionControlPolicy = cluster.configuration.dasConfig.admissionControlPolicy
                if not isinstance(admissionControlPolicy, vim.cluster.FailoverResourcesAdmissionControlPolicy):
                    passed = False
                    self.reporter.notify_progress(self.reporter.notify_checkLog, clusters_key+"@" +cluster_name+ "=ACP is set to different policy than percentage based (Expected: =true)", (False and "PASS" or "FAIL"))
                    message += ", "+clusters_key+"@" +cluster_name+ "=ACP is set to different policy than percentage based (Expected: =true)#"+(False and "PASS" or "FAIL")
                    continue

                cpuFailoverResourcesPercent = cluster.configuration.dasConfig.admissionControlPolicy.cpuFailoverResourcesPercent
                memoryFailoverResourcesPercent = cluster.configuration.dasConfig.admissionControlPolicy.memoryFailoverResourcesPercent
                numberof_nodes = len(cluster.host)
                nplus = numberof_nodes + 1
                nplus_policy_based_percentage=round(100/nplus)

                if (nplus_policy_based_percentage != cpuFailoverResourcesPercent) and (memoryFailoverResourcesPercent !=nplus_policy_based_percentage):
                    passed = False
                    self.reporter.notify_progress(self.reporter.notify_checkLog, clusters_key+"@" +cluster_name+ "=ACP reservation policy does not meet N+1 failover requirements (Expected: =true)", (False and "PASS" or "FAIL"))
                    message += ", "+clusters_key+"@" +cluster_name+ "=ACP reservation policy does not meet N+1 failover requirements (Expected: =true)#"+(False and "PASS" or "FAIL")
                else:
                    self.reporter.notify_progress(self.reporter.notify_checkLog, clusters_key+"@" +cluster_name+ "=true (Expected: =true)", (True and "PASS" or "FAIL"))
                    message += ", "+clusters_key+"@" +cluster_name+ "=true (Expected: =true)#"+(True and "PASS" or "FAIL")

                passed_all = passed_all and passed
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_cluster_acpPercentage_basedOn_nodes - Exit")
        return passed_all , message,path

    @checkgroup("cluster_checks", "Verify reserved memory and cpu capacity versus Admission control policy set", ["performance"], "Cluster Failover Resources %")
    def check_cluster_validate_reserverdMemory_and_reservedCPU_vs_acp(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_cluster_validate_reserverdMemory_and_reservedCPU_vs_acp - Enter")
        path = 'content.rootFolder.childEntity.hostFolder.childEntity'
        clusters_map = self.get_vc_property(path)
        message = ""
        passed_all = True

        for clusters_key, clusters in clusters_map.iteritems():
            passed = True
            if clusters == "Not-Configured":
                continue

            for cluster in clusters:
                if not isinstance(cluster, vim.ClusterComputeResource):
                    #condition to check if host directly attached to cluster
                    continue
                cluster_name= cluster.name
                if self.authconfig['cluster']!='':
                        if cluster_name not in self.authconfig['cluster']:
                            #print "skipping "+cluster_name
                            continue

                acp_enabled = cluster.configuration.dasConfig.admissionControlEnabled
                if not acp_enabled:
                    passed = False
                    self.reporter.notify_progress(self.reporter.notify_checkLog, clusters_key+"@" +cluster_name+ "=ACP is disabled (Expected: =Cluster Failover Resources %)", (False and "PASS" or "FAIL"))
                    message += ", "+clusters_key+"@" +cluster_name+ "=ACP is disabled (Expected: =Cluster Failover Resources %)#"+(False and "PASS" or "FAIL")
                    continue
                admissionControlPolicy = cluster.configuration.dasConfig.admissionControlPolicy
                if not isinstance(admissionControlPolicy, vim.cluster.FailoverResourcesAdmissionControlPolicy):
                    passed = False
                    self.reporter.notify_progress(self.reporter.notify_checkLog, clusters_key+"@" +cluster_name+ "=ACP is set to different policy than percentage based (Expected: =Cluster Failover Resources %)", (False and "PASS" or "FAIL"))
                    message += ", "+clusters_key+"@" +cluster_name+ "=ACP is set to different policy than percentage based (Expected: =Cluster Failover Resources %)#"+(False and "PASS" or "FAIL")
                    continue

                cpuFailoverResourcesPercent = cluster.configuration.dasConfig.admissionControlPolicy.cpuFailoverResourcesPercent
                memoryFailoverResourcesPercent = cluster.configuration.dasConfig.admissionControlPolicy.memoryFailoverResourcesPercent
                currentCpuFailoverResourcesPercent = cluster.summary.admissionControlInfo.currentCpuFailoverResourcesPercent
                currentMemoryFailoverResourcesPercent = cluster.summary.admissionControlInfo.currentMemoryFailoverResourcesPercent
                cpu_diff = currentCpuFailoverResourcesPercent - cpuFailoverResourcesPercent
                memory_diff = currentMemoryFailoverResourcesPercent - memoryFailoverResourcesPercent

                if (cpu_diff > 25 ) and (memory_diff > 25):
                    passed = True
                else:
                    passed = False

                msg = "Reserved-Cpu:"+str(cpuFailoverResourcesPercent)+"; Current-Cpu:"+str(currentCpuFailoverResourcesPercent)+"; Reserved-Memory:"+str(memoryFailoverResourcesPercent)+"; Current-Memory:"+str(currentMemoryFailoverResourcesPercent)
                self.reporter.notify_progress(self.reporter.notify_checkLog, clusters_key+"@" +cluster_name+ "="+msg+" (Expected: =Cluster Failover Resources %)", (passed and "PASS" or "FAIL"))
                message += ", "+clusters_key+"@" +cluster_name+ "="+msg+" (Expected: =Cluster Failover Resources %)#"+(passed and "PASS" or "FAIL")

                passed_all = passed_all and passed
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_cluster_validate_reserverdMemory_and_reservedCPU_vs_acp - Exit")
        return passed_all , message,path

    @checkgroup("esxi_checks", "Validate the Directory Services Configuration is set to Active Directory", ["security"], "True")
    def check_directory_service_set_to_active_directory(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_directory_service_set_to_active_directory - Enter")
        path = 'content.rootFolder.childEntity.hostFolder.childEntity.host.config.authenticationManagerInfo.authConfig'
        authenticationStoreInfo = self.get_vc_property(path)
        message = ""
        passed = True
        for hostname, store in authenticationStoreInfo.iteritems():
            for item in store:
                if isinstance(item, vim.host.ActiveDirectoryInfo):
                    if hasattr(item, "enabled"):
                        is_active_dir_enabled = item.enabled
                        self.reporter.notify_progress(self.reporter.notify_checkLog, hostname+"="+str(is_active_dir_enabled) + " (Expected: =True) " , (is_active_dir_enabled and "PASS" or "FAIL"))
                        passed = passed and (is_active_dir_enabled and True or False)
                        message += ", " +hostname+"="+str(is_active_dir_enabled) + " (Expected: =True) "+"#"+((is_active_dir_enabled) and "PASS" or "FAIL") 

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_directory_service_set_to_active_directory - Exit")
        return passed, message,path

    @checkgroup("esxi_checks", "Validate NTP client is set to Enabled and is in the running state", ["reliability"], "NTP client is enabled and running.")
    def check_ntp_client_enable_running(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_ntp_client_enable_running - Enter")
        path = 'content.rootFolder.childEntity.hostFolder.childEntity.host'
        datacenter_hosts=self.get_vc_property(path)
        message = ""
        passed = False
        for datacenter in datacenter_hosts.keys():
            try:
                for host in datacenter_hosts[datacenter]:
                    try:
                        host_name = host.name
                        if self.authconfig['host'] != '':
                            if host_name not in self.authconfig['host']:
                                #print "skipping host "+host_name
                                continue
                        ruleset_enable =False
                        service_running = False
                        rulesets = host.configManager.firewallSystem.firewallInfo.ruleset
                        host_services = host.config.service.service
                        for ruleset in rulesets:
                            if ruleset.key == "ntpClient":
                                ruleset_enable = ruleset.enabled
                                for service in host_services:
                                    if service.key == "ntpd":
                                        service_running = service.running
                        self.reporter.notify_progress(self.reporter.notify_checkLog, datacenter+"."+host.name+" = NTP Client enable:"+str(ruleset_enable) + " and running:"+str(service_running)+" (Expected: ="+" NTP Client enable: True and running: True "+") " , ((ruleset_enable and service_running) and "PASS" or "FAIL"))
                        passed = passed and ((ruleset_enable and service_running) and "PASS" or "FAIL") 
                        message += ", " +datacenter+"@"+host.name+"= NTP Client enabled:"+str(ruleset_enable) + " and running:"+str(service_running)+" (Expected: = NTP Client enable: True and running: True)#"+ ((ruleset_enable and service_running) and "PASS" or "FAIL")
                    except AttributeError:
                        self.reporter.notify_progress(self.reporter.notify_checkLog, datacenter+"."+host.name+" = NTP Client not configured" , ((ruleset_enable and service_running) and "PASS" or "FAIL"))
                        passed = False
                        message += ", " +datacenter+"@"+host.name+" = NTP Client not configured (Expected: = NTP Client enable: True and running: True )#"+ ((ruleset_enable and service_running) and "PASS" or "FAIL")
            except AttributeError:
                    self.reporter.notify_progress(self.reporter.notify_checkLog, datacenter+" = NTP Client not configured (Expected: = NTP Client enable: True and running: True )" , (False and "PASS" or "FAIL"))
                    passed = False
                    message += ", " +datacenter+" = NTP Client not configured (Expected: = NTP Client enable: True and running: True )#"+ (False and "PASS" or "FAIL")

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_ntp_client_enable_running - Exit")
        return passed, message, path

    @checkgroup("esxi_checks", "NTP Servers Configured", ["availability"], "NTP Servers are configured")
    def check_ntp_servers_configured(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_ntp_servers_configured - Enter")
        path = 'content.rootFolder.childEntity.hostFolder.childEntity.host'
        all_hosts = self.get_vc_property(path)
        message = ""
        passed_all = True

        for cluster, hostObject in all_hosts.iteritems():
            try:
                if len(hostObject) == 0:
                    pass
                    #self.reporter.notify_progress(self.reporter.notify_checkLog, cluster+" = No Hosts are configured ( Expected: = At-least 2 NTP Servers are configured )","FAIL")
                    #passed = False
                    #message += ", " +cluster+"= No Hosts are configured (Expected:= At-least 2 NTP Servers are configured ) #FAIL"
                else:
                    for host in hostObject:
                        passed = True
                        host_name=host.name
                        if self.authconfig['host']!='':
                            if host_name not in self.authconfig['host']:
                                #print "skipping host "+host_name
                                continue
                        ntp_servers = host.config.dateTimeInfo.ntpConfig.server
                        ntp_servers_str = ' '.join(ntp_servers)
                        if len(ntp_servers) < 2:
                            passed = False
                            self.reporter.notify_progress(self.reporter.notify_checkLog, cluster+"."+host.name+" = NTP Servers configured ["+','.join(ntp_servers)+"]  (Expected: = at-least 2 NTP Servers are configured )","FAIL")
                            message += ", " +cluster+"@"+host.name+"="+','.join(ntp_servers)+" (Expected: =At-least 2 NTP Servers are configured ) #FAIL"
                        else:
                            self.reporter.notify_progress(self.reporter.notify_checkLog, cluster+"."+host.name+" = NTP Servers configured ["+','.join(ntp_servers)+"]  (Expected: = at-least 2 NTP Servers are configured )","PASS")
                            message += ", " +cluster+"@"+host.name+"="+','.join(ntp_servers)+" (Expected: =At-least 2 NTP Servers are configured ) #PASS"     
                               
                        passed_all = passed_all and passed
            except AttributeError:
                    self.reporter.notify_progress(self.reporter.notify_checkLog, cluster+"=Not-Configured (Expected: =At-least 2 NTP Servers are configured )","FAIL")
                    message += ", " +cluster+"=Not-Configured (Expected: =At-least 2 NTP Servers are configured ) #FAIL"     
                    passed = False

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_ntp_servers_configured - Exit")
        return passed_all, message, path

    @checkgroup("esxi_checks", "Management VMkernel adapter has only Management Traffic Enabled", ["performance"], "vMotionTraffic:Disabled<br/> ManagementTraffic:Enabled<br/> FTLogging:Disabled")
    def check_management_vmkernel_has_management_traffic(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_management_vmkernel_has_management_traffic - Enter")
        path = 'content.rootFolder.childEntity.hostFolder.childEntity.host.configManager.virtualNicManager.info.netConfig'
        virtual_nic_mgrs = self.get_vc_property(path)
        message = ""
        passed = True

        for host, netConfig_list in virtual_nic_mgrs.iteritems():
            #print host
            if netConfig_list == "Not-Configured":
                continue
            else:
                service_list = []
                vmkernal_nic_and_portgrp = {}
                nic_selected_service = {}

                for netConfig in netConfig_list:
                    service_list.append(netConfig.nicType)
                    candidateVnic_list = netConfig.candidateVnic
                    for candidateVnic in candidateVnic_list:
                        device = candidateVnic.device

                        if candidateVnic.key in netConfig.selectedVnic:
                            if device not in nic_selected_service.keys():
                                nic_selected_service[device] = list()
                            (nic_selected_service[device]).append(netConfig.nicType)
                        if device not in vmkernal_nic_and_portgrp.keys():
                            vmkernal_nic_and_portgrp[candidateVnic.portgroup.lower()] = device
                #print "\t\t",service_list, '\n\t\t',vmkernal_nic_and_portgrp,"\n\t\t",nic_selected_service
                vmkernal_adapter = vmkernal_nic_and_portgrp.get('management network')
                enabled_management_service = nic_selected_service.get(vmkernal_adapter)
                status = True
                excepted_result="vMotionTraffic:Disabled; ManagementTraffic:Enabled; FTLogging:Disabled"

                if enabled_management_service != None:
                    result = ''
                    if 'vmotion' in enabled_management_service:
                        status = False
                        result += "vMotionTraffic:Enabled;"
                    else:
                        result+="vMotionTraffic:Disabled;"

                    if 'management' in enabled_management_service:
                        result += " ManagementTraffic:Enabled;"
                    else:
                        result += " ManagementTraffic:Disabled;"

                    if 'faultToleranceLogging' in enabled_management_service:
                        status = False
                        result += " FTLogging:Enabled"
                    else:
                        result += " FTLogging:Disabled"

                    passed = passed and status
                    message += ", " +host+"@"+vmkernal_adapter+"="+result+" (Expected: ="+excepted_result+")"+"#"+(status and "PASS" or "FAIL")
                    self.reporter.notify_progress(self.reporter.notify_checkLog,host+"@"+vmkernal_adapter+"="+result+" (Expected: ="+excepted_result+")",(status and "PASS" or "FAIL"))
                else:
                    status = False
                    message += ", " +host+"=Management-Adapter-Not-Found (Expected: ="+excepted_result+")"+"#"+(status and "PASS" or "FAIL")
                    self.reporter.notify_progress(self.reporter.notify_checkLog,host+"=Management-Adapter-Not-Found (Expected: ="+excepted_result+")",(status and "PASS" or "FAIL"))
                passed = passed and status

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_management_vmkernel_has_management_traffic - Exit")                                                                                                                                                      
        return passed, message,path

    @checkgroup("esxi_checks", "vMotion VMkernel adapter has only vMotion Traffic Enabled", ["performance"], "vMotionTraffic:Enabled<br/> ManagementTraffic:Disabled<br/> FTLogging:Disabled")
    def check_vmotion_vmkernel_has_management_traffic(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_vmotion_vmkernel_has_management_traffic - Enter")
        path = 'content.rootFolder.childEntity.hostFolder.childEntity.host.configManager.virtualNicManager.info.netConfig'
        virtual_nic_mgrs = self.get_vc_property(path)
        message = ""
        passed = True

        for host, netConfig_list in virtual_nic_mgrs.iteritems():
            #print host
            if netConfig_list == "Not-Configured":
                continue
            else:
                service_list = []
                vmkernal_nic_and_portgrp = {}
                nic_selected_service = {}

                for netConfig in netConfig_list:
                    service_list.append(netConfig.nicType)

                    candidateVnic_list = netConfig.candidateVnic
                    for candidateVnic in candidateVnic_list:
                        device = candidateVnic.device

                        if candidateVnic.key in netConfig.selectedVnic:
                            if device not in nic_selected_service.keys():
                                nic_selected_service[device] = list()
                            (nic_selected_service[device]).append(netConfig.nicType)

                        if device not in vmkernal_nic_and_portgrp.keys():
                            vmkernal_nic_and_portgrp[candidateVnic.portgroup.lower()] = device

                vmkernal_adapter = vmkernal_nic_and_portgrp.get('vmotion')
                enabled_management_service = nic_selected_service.get(vmkernal_adapter)

                status = True
                excepted_result = "vMotionTraffic:Enabled; ManagementTraffic:Disabled; FTLogging:Disabled"
                if enabled_management_service != None :
                    result = ''
                    if 'vmotion' in enabled_management_service:
                        result += "vMotionTraffic:Enabled;"
                    else:
                        result += "vMotionTraffic:Disabled;"

                    if 'management' in enabled_management_service:
                        status = False
                        result += " ManagementTraffic:Enabled;"
                    else:
                        result += " ManagementTraffic:Disabled;"

                    if 'faultToleranceLogging' in enabled_management_service:
                        status = False
                        result +=" FTLogging:Enabled"
                    else:
                        result +=" FTLogging:Disabled"

                    message += ", " +host+"@"+vmkernal_adapter+"="+result+" (Expected: ="+excepted_result+")"+"#"+(status and "PASS" or "FAIL")
                    self.reporter.notify_progress(self.reporter.notify_checkLog,host+"@"+vmkernal_adapter+"="+result+" (Expected: ="+excepted_result+")",(status and "PASS" or "FAIL"))
                else:
                    status = False
                    message += ", " +host+"=vMotion-Adapter-Not-Found (Expected: ="+excepted_result+")"+"#"+(status and "PASS" or "FAIL")
                    self.reporter.notify_progress(self.reporter.notify_checkLog,host+"=vMotion-Adapter-Not-Found (Expected: ="+excepted_result+")",(status and "PASS" or "FAIL"))
                passed = passed and status

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_vmotion_vmkernel_has_management_traffic - Exit")
        return passed, message, path

    @checkgroup("esxi_checks", "FTLogging VMkernel adapter has only FTLogging Enabled", ["performance"], "vMotionTraffic:Disabled<br/> ManagementTraffic:Disabled<br/> FTLogging:Enabled")
    def check_ftlogging_vmkernel_has_management_traffic(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_ftlogging_vmkernel_has_management_traffic - Enter")
        path = 'content.rootFolder.childEntity.hostFolder.childEntity.host.configManager.virtualNicManager.info.netConfig'
        virtual_nic_mgrs = self.get_vc_property(path)

        message = ""
        passed = True
        for host, netConfig_list in virtual_nic_mgrs.iteritems():
            #print host
            if netConfig_list == "Not-Configured":
                continue
            else:
                service_list = []
                vmkernal_nic_and_portgrp = {}
                nic_selected_service = {}

                for netConfig in netConfig_list:
                    service_list.append(netConfig.nicType)
                    candidateVnic_list = netConfig.candidateVnic
                    for candidateVnic in candidateVnic_list:
                        device = candidateVnic.device

                        if candidateVnic.key in netConfig.selectedVnic:
                            if device not in nic_selected_service.keys():
                                nic_selected_service[device] = list()
                            (nic_selected_service[device]).append(netConfig.nicType)

                        if device not in vmkernal_nic_and_portgrp.keys():
                            vmkernal_nic_and_portgrp[candidateVnic.portgroup.lower()] = device
                #print "\t\t",service_list, '\n\t\t',vmkernal_nic_and_portgrp,"\n\t\t",nic_selected_service
                vmkernal_adapter = vmkernal_nic_and_portgrp.get('faulttolerancelogging')
                enabled_management_service = nic_selected_service.get(vmkernal_adapter)

                status = True
                excepted_result="vMotionTraffic:Disabled; ManagementTraffic:Disabled; FTLogging:Enabled"
                if enabled_management_service != None:
                    result=''
                    if 'vmotion' in enabled_management_service:
                        status = False
                        result +="vMotionTraffic:Enabled;"
                    else:
                        result += "vMotionTraffic:Disabled;"
                    if 'management' in enabled_management_service:
                        status = False
                        result +=" ManagementTraffic:Enabled;"
                    else:
                        result +=" ManagementTraffic:Disabled;"

                    if 'faultToleranceLogging' in enabled_management_service:
                        result +=" FTLogging:Enabled"
                    else:
                        result += " FTLogging:Disabled"

                    message += ", " +host+"@"+vmkernal_adapter+"="+result+" (Expected: ="+excepted_result+")"+"#"+(status and "PASS" or "FAIL")
                    self.reporter.notify_progress(self.reporter.notify_checkLog,host+"@"+vmkernal_adapter+"="+result+" (Expected: ="+excepted_result+")",(status and "PASS" or "FAIL"))
                else:
                    status = False
                    message += ", " +host+"=FTLogging-Adapter-Not-Found (Expected: ="+excepted_result+")"+"#"+(status and "PASS" or "FAIL")
                    self.reporter.notify_progress(self.reporter.notify_checkLog,host+"=FTLogging-Adapter-Not-Found (Expected: ="+excepted_result+")",(status and "PASS" or "FAIL"))
                passed = passed and status

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_ftlogging_vmkernel_has_management_traffic - Exit")
        return passed, message,path

    @checkgroup("esxi_checks", "Host Profiles are Configured and Compliant", ["configurability","manageability","security"], "True")
    def check_hostprofiles_configuration(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_hostprofiles_configuration - Enter")
        profile_list = self.get_vc_property('content.hostProfileManager.profile')
        host_profile_manager = self.get_vc_property('content.hostProfileManager')
        message = ""
        passed = True
        profiles_list = []
        host_profiles_list = []
        profile_entity_map = {}
        for key, profiles in profile_list.iteritems():
            if profiles == None or profiles == "Not-Configured":
                continue
            for profile in profiles:
                profiles_list.append(profile)
                profile_entity_map[profile] = profile.entity

        for key,profilemanager in host_profile_manager.iteritems():
            host_profile_manager = profilemanager 

        if len(profiles_list) > 0:
            path = 'content.rootFolder.childEntity.hostFolder.childEntity'
            cluster_map = self.get_vc_property(path)
            for clusters_key, clusters in cluster_map.iteritems():
                profile_flag = False
                if clusters!="Not-Configured":
                    for cluster in clusters:
                        cluster_name = cluster.name
                        if self.authconfig['cluster'] != '':
                            if cluster_name not in self.authconfig['cluster']:
                                #print "skipping "+cluster_name
                                continue
                        if not isinstance(cluster, vim.ClusterComputeResource):
                            #condition to check if any host attached to datacenter without adding to any cluster
                            continue
                        host_list = cluster.host
                        if len(host_list) > 0:
                            for host in host_list:
                                host_profile_list = host_profile_manager.FindAssociatedProfile(host)
                                for host_profile in host_profile_list:
                                    if host_profile in host_profiles_list:
                                        break
                                    elif len(host_profiles_list) == 0:
                                        host_profiles_list.append(host_profile)
                                    else:
                                        profile_flag = True    
                        if profile_flag == True:
                            passed = False
                            self.reporter.notify_progress(self.reporter.notify_checkLog,"Multiple Host Profiles configured on Hosts in cluster ["+cluster_name+"] =True (Expected: =False)" , (passed and "PASS" or "FAIL"))
                            message += ", "+"Multiple Host Profiles configured on Hosts in cluster ["+cluster_name+"] =True (Expected: =False)" +"#"+((passed) and "PASS" or "FAIL")
                        else:
                            for host in host_list:
                                host_name = host.name
                                if self.authconfig['host'] !='':
                                    if host_name not in self.authconfig['host']:
                                        #print "skipping host "+host_name
                                        continue

                                for profile in profiles_list:
                                    entity_host_list = profile_entity_map.get(profile)

                                    if host in entity_host_list:
                                        temp_host_list = [host]
                                        compliance_result = profile.CheckProfileCompliance_Task(temp_host_list)
                                        time.sleep(10)
                                        compliance_status_list = compliance_result.info.result
                                        host_name = host.name
                                        proFILE_NAME = profile.name
                                        if compliance_status_list is not None and len(compliance_status_list) > 0:
                                            for result in compliance_status_list:
                                                compliance_status = result.complianceStatus
                                                if compliance_status == "nonCompliant" or compliance_status == "unknown":
                                                    passed = False
                                                    self.reporter.notify_progress(self.reporter.notify_checkLog,"Host ["+host_name+"] on Cluster ["+cluster_name+"] Compliance with Host Profile ["+proFILE_NAME+"] =False (Expected: =True)" , (passed and "PASS" or "FAIL"))
                                                    message += ", "+"Host ["+host_name+"] on Cluster ["+cluster_name+"] Compliance with Host Profile ["+proFILE_NAME+"] =False (Expected: =True)" +"#"+((passed) and "PASS" or "FAIL")
                                        else:
                                            passed = True
                                            self.reporter.notify_progress(self.reporter.notify_checkLog,"Host ["+host_name+"] on Cluster ["+cluster_name+"] Compliance with Host Profile ["+proFILE_NAME+"] =Cannot Determine (Expected: =True)" , (passed and "PASS" or "FAIL"))
                                            message += ", "+"Host ["+host_name+"] on Cluster ["+cluster_name+"] Compliance with Host Profile ["+proFILE_NAME+"] =Cannot Determine (Expected: =True)" +"#"+((passed) and "PASS" or "FAIL")

        else:
            passed = True
            self.reporter.notify_progress(self.reporter.notify_checkLog,"No Host Profiles Configured =True (Expected: =True) " , (passed and "PASS" or "FAIL"))
            message += ", "+"No Host Profiles Configured =True (Expected: =True)" +"#"+((passed) and "PASS" or "FAIL")

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_hostprofiles_configuration - Exit")
        return passed,message,''   

    @checkgroup("esxi_checks", "Error Messages in ESXi Logs", ["configurability","manageability","availability","security"], "Error Count")
    def check_esxi_logs(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_esxi_logs - Enter")
        check_list = ["Failed Logins in auth.log", "Error Messages in hostd.log", "Error Messages in vmkernel.log", "Error Messages in lacp.log"]
        path_curr='content.rootFolder.childEntity.hostFolder.childEntity.host'
        clusters_map = self.get_vc_property(path_curr)
        message = ""
        passed_all = True
        for datacenter, host_list in clusters_map.iteritems():
            passed = True
            #print datacenter
            if host_list == "Not-Configured" :
                continue
            elif len(host_list)==0: 
                #condtion to Check if no host found
                continue
            for host in host_list:
                host_ip = host.name
                if self.authconfig['host'] != '':
                    if host_ip not in self.authconfig['host']:
                        #print "skipping host "+host_name
                        continue
                flag,esxi_ssh = self.get_esxi_ssh_connection(host_ip)
                if flag == "SSH Connection Failed" or flag == "Authentication Exception":
                    passed = False
                    message += ", " +"Error Messages in ESXi Logs on " + host_ip + " =SSH Connection Failed" + " (Expected: =Error Count)"+"#"+("FAIL")
                    self.reporter.notify_progress(self.reporter.notify_checkLog, "Error Messages in ESXi Logs on "+host_ip+" =SSH Connection Failed"+" (Expected: =Error Count)",("FAIL"))
                elif esxi_ssh is not None and esxi_ssh._transport is not None:
                    for check_name in check_list:
                        error_count = 0
                        time.sleep(1)
                        if check_name == "Failed Logins in auth.log":
                            log_FILE_NAME = "auth.log" 
                        elif check_name == "Error Messages in hostd.log":
                            log_FILE_NAME = "hostd.log"    
                        elif check_name == "Error Messages in vmkernel.log":
                            log_FILE_NAME = "vmkernel.log"    
                        elif check_name == "Error Messages in lacp.log":
                            log_FILE_NAME = "lacp.log"

                        cmd_error = "cat /var/log/"+log_FILE_NAME+" | grep \"Error\" | grep -v \"User \'root\' running command\""
                        stdin, stdout, stderr =  esxi_ssh.exec_command(cmd_error)
                        for line in stdout:
                            error_count+=1
                        if error_count > 50:
                            passed = False
                            message += ", " + check_name + " on " + host_ip + "=" + str(error_count) + " (Expected: =Less than 50)"+"#" + (passed and "PASS" or "FAIL")
                            self.reporter.notify_progress(self.reporter.notify_checkLog,check_name+" on "+host_ip+"="+str(error_count)+" (Expected: =Less than 50)",(passed and "PASS" or "FAIL"))
                        elif error_count <= 50:
                            passed = True
                            message += ", " +check_name+" on "+host_ip+"="+str(error_count)+" (Expected: =Less than 50)"+"#"+(passed and "PASS" or "FAIL")
                            self.reporter.notify_progress(self.reporter.notify_checkLog,check_name+" on "+host_ip+"="+str(error_count)+" (Expected: =Less than 50)",(passed and "PASS" or "FAIL"))
                else:
                    passed = False
                    message += ", " +"Error Messages in ESXi Logs on "+host_ip+" =Cannot Determine"+" (Expected: =Error Count)"+"#"+("FAIL")
                    self.reporter.notify_progress(self.reporter.notify_checkLog,"Error Messages in ESXi Logs on "+host_ip+" =Cannot Determine"+" (Expected: =Error Count)",("FAIL"))
                VCChecker.esxi_ssh = None
        passed_all = passed_all and passed

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_esxi_logs - Exit")
        return passed_all,message,path_curr

    def get_esxi_ssh_connection(self, host_ip):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: get_esxi_ssh_connection - Enter")
        if VCChecker.esxi_ssh is None:
                try:
                    VCChecker.esxi_ssh = paramiko.SSHClient()
                    VCChecker.esxi_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    VCChecker.esxi_ssh.connect(host_ip, username = "root", password = "nutanix/4u")
                except paramiko.AuthenticationException:
                    return "Authentication Exception",None
                except paramiko.SSHException, e:
                    return "SSH Connection Failed",None
                except socket.error, e:
                    return "SSH Connection Failed",None
        else:
            pass

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: get_esxi_ssh_connection - Exit")
        return  "Success",VCChecker.esxi_ssh

    def get_cvm_ssh_connection(self, cvm_ip):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: get_cvm_ssh_connection - Enter")
        if VCChecker.cvm_ssh is None:
                try:
                    VCChecker.cvm_ssh = paramiko.SSHClient()
                    VCChecker.cvm_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    VCChecker.cvm_ssh.connect(cvm_ip, username = "nutanix", password = "nutanix/4u")
                except paramiko.AuthenticationException:
                    return "Authentication Exception", None
                except paramiko.SSHException, e:
                    return "SSH Connection Failed", None
                except socket.error, e:
                    return "SSH Connection Failed", None
        else:
            pass

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: get_cvm_ssh_connection - Exit")
        return  "Success",VCChecker.cvm_ssh
 
    def get_ipmi_ssh_connection(self, ipmi_ip):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: get_ipmi_ssh_connection - Enter")
        if VCChecker.ipmi_ssh is None:
                try:
                    VCChecker.ipmi_ssh = paramiko.SSHClient()
                    VCChecker.ipmi_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    VCChecker.ipmi_ssh.connect(ipmi_ip, username = "ADMIN", password = "ADMIN")
                except paramiko.AuthenticationException:
                    return "Authentication Exception", None
                except paramiko.SSHException, e:
                    return "SSH Connection Failed", None
                except socket.error, e:
                    return "SSH Connection Failed", None
        else:
            pass

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: get_ipmi_ssh_connection - Exit")
        return  "Success",VCChecker.ipmi_ssh
  
    @checkgroup("esxi_checks", "Check if Default Password has Changed", ["security"], "Password changed Information")
    def check_default_password(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_default_password - Enter")
        #check esxi passwords
        path_curr='content.rootFolder.childEntity.hostFolder.childEntity.host'
        clusters_map = self.get_vc_property(path_curr)
        message = ""
        passed_all = True
        cvm_ip_list = []
        for datacenter, host_list in clusters_map.iteritems():
            passed = True
            #print datacenter
            if host_list == "Not-Configured" :
                continue
            elif len(host_list)==0: 
                #condtion to Check if no host found
                continue
            for host in host_list:
                host_ip = host.name
                if self.authconfig['host'] != '':
                    if host_ip not in self.authconfig['host']:
                        #print "skipping host "+host_name
                        continue

                flag, esxi_ssh = self.get_esxi_ssh_connection(host_ip)
                if flag == "Success":
                    passed = True
                    message += ", " +"Default Password of Host: "+host_ip+" =Not Changed"+" (Expected: =Not Changed)"+"#"+(passed and "PASS" or "FAIL")
                    self.reporter.notify_progress(self.reporter.notify_checkLog,"Default Password of Host: "+host_ip+" =Not Changed"+" (Expected: =Not Changed)",(passed and "PASS" or "FAIL"))
                elif flag == "Authentication Exception":
                    passed = False
                    message += ", " +"Default Password of Host: "+host_ip+" =Changed"+" (Expected: =Not Changed)"+"#"+(passed and "PASS" or "FAIL")
                    self.reporter.notify_progress(self.reporter.notify_checkLog,"Default Password of Host: "+host_ip+" =Changed"+" (Expected: =Not Changed)",(passed and "PASS" or "FAIL"))
                elif flag == "SSH Connection Failed":
                    passed = False
                    message += ", " +"Default Password of Host: "+host_ip+" =SSH Connection Failed"+" (Expected: =Not Changed)"+"#"+(passed and "PASS" or "FAIL")
                    self.reporter.notify_progress(self.reporter.notify_checkLog,"Default Password of Host: "+host_ip+" =SSH Connection Failed"+" (Expected: =Not Changed)",(passed and "PASS" or "FAIL"))
 
                VCChecker.esxi_ssh = None
        #check vcenter server password via SSH
#         flag,vcenter_server_ssh,vcenter_ip = self.get_vcenter_server_ssh_connection()
#  
#         if flag == "Success":
#             passed = True
#             message += ", " +"Default Password of vCenter Server: "+vcenter_ip+" =Not Changed"+" (Expected: =Not Changed)"+"#"+(passed and "PASS" or "FAIL")
#             self.reporter.notify_progress(self.reporter.notify_checkLog,"Default Password of vCenter Server: "+vcenter_ip+" =Not Changed"+" (Expected: =Not Changed)",(passed and "PASS" or "FAIL"))
#         elif flag == "Authentication Exception":
#             passed = False
#             message += ", " +"Default Password of vCenter Server: "+vcenter_ip+" =Changed"+" (Expected: =Not Changed)"+"#"+(passed and "PASS" or "FAIL")
#             self.reporter.notify_progress(self.reporter.notify_checkLog,"Default Password of vCenter Server: "+vcenter_ip+" =Changed"+" (Expected: =Not Changed)",(passed and "PASS" or "FAIL"))
#         elif flag == "SSH Connection Failed":
#             passed = False
#             message += ", " +"Default Password of vCenter Server: "+vcenter_ip+" =SSH Connection Failed"+" (Expected: =Not Changed)"+"#"+(passed and "PASS" or "FAIL")
#             self.reporter.notify_progress(self.reporter.notify_checkLog,"Default Password of vCenter Server: "+vcenter_ip+" =SSH Connection Failed"+" (Expected: =Not Changed)",(passed and "PASS" or "FAIL"))
 
        #check vcenter server password via HTTP
        vcenter_ip = self.get_vcenter_server_ip()
        vCenterServerURL = "https://"+vcenter_ip+":9443"
        try:
            vCenterServerResonse = requests.get(vCenterServerURL,auth=("root", "vmware"), verify=False)
            if vCenterServerResonse.status_code == 200:
                passed = True
                message += ", " +"Default Password of vCenter Server: "+vcenter_ip+" =Not Changed"+" (Expected: =Not Changed)"+"#"+(passed and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"Default Password of vCenter Server: "+vcenter_ip+" =Not Changed"+" (Expected: =Not Changed)",(passed and "PASS" or "FAIL"))
            elif vCenterServerResonse.status_code == 401:
                passed = False
                message += ", " +"Default Password of vCenter Server: "+vcenter_ip+" =Changed"+" (Expected: =Not Changed)"+"#"+(passed and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"Default Password of vCenter Server: "+vcenter_ip+" =Changed"+" (Expected: =Not Changed)",(passed and "PASS" or "FAIL"))
            else:
                passed = False
                message += ", " +"Default Password of vCenter Server: "+vcenter_ip+" =Connection Failed"+" (Expected: =Not Changed)"+"#"+(passed and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"Default Password of vCenter Server: "+vcenter_ip+" =Connection Failed"+" (Expected: =Not Changed)",(passed and "PASS" or "FAIL"))
        except:        
            passed = False
            message += ", " +"Default Password of vCenter Server: "+vcenter_ip+" =Connection Failed"+" (Expected: =Not Changed)"+"#"+(passed and "PASS" or "FAIL")
            self.reporter.notify_progress(self.reporter.notify_checkLog,"Default Password of vCenter Server: "+vcenter_ip+" =Connection Failed"+" (Expected: =Not Changed)",(passed and "PASS" or "FAIL"))

        #check cvms password
        path ='content.rootFolder.childEntity.hostFolder.childEntity.host.vm[name=NTNX*CVM].summary'
        vms_map= self.get_vc_property(path)
        for vms_key, vm in vms_map.iteritems():
            if vm == 'Not-Configured' :
                #condition to check if any clusters not found 
                continue
            passed = True
             
            vms_key = '@'.join(vms_key.split('@')[0:-1])
             
            cvm_ip = vm.guest.ipAddress
            cvm_ip_list.append(cvm_ip)
            flag,cvm_ssh = self.get_cvm_ssh_connection(cvm_ip) 

            if flag == "Success":
                passed = True
                message += ", " +"Default Password of CVM: "+cvm_ip+" =Not Changed"+" (Expected: =Not Changed)"+"#"+(passed and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"Default Password of CVM: "+cvm_ip+" =Not Changed"+" (Expected: =Not Changed)",(passed and "PASS" or "FAIL"))
            elif flag == "Authentication Exception":
                passed = False
                message += ", " +"Default Password of CVM: "+cvm_ip+" =Changed"+" (Expected: =Not Changed)"+"#"+(passed and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"Default Password of CVM: "+cvm_ip+" =Changed"+" (Expected: =Not Changed)",(passed and "PASS" or "FAIL"))
            elif flag == "SSH Connection Failed":
                passed = False
                message += ", " +"Default Password of CVM: "+cvm_ip+" =SSH Connection Failed"+" (Expected: =Not Changed)"+"#"+(passed and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"Default Password of CVM: "+cvm_ip+" =SSH Connection Failed"+" (Expected: =Not Changed)",(passed and "PASS" or "FAIL"))

            VCChecker.cvm_ssh = None
        #check prism passwords
        if len(cvm_ip_list) > 0:
            for cvm_ip in cvm_ip_list:
                prismURL = "https://"+cvm_ip+":9440"
                try:
                    prismResonse = requests.get(prismURL,auth=("admin", "admin"), verify=False)
                    if prismResonse.status_code == 200:
                        passed = True
                        message += ", " +"Default Password of Prism: "+cvm_ip+" =Not Changed"+" (Expected: =Not Changed)"+"#"+(passed and "PASS" or "FAIL")
                        self.reporter.notify_progress(self.reporter.notify_checkLog,"Default Password of Prism: "+cvm_ip+" =Not Changed"+" (Expected: =Not Changed)",(passed and "PASS" or "FAIL"))
                    elif prismResonse.status_code == 401:
                        passed = False
                        message += ", " +"Default Password of Prism: "+cvm_ip+" =Changed"+" (Expected: =Not Changed)"+"#"+(passed and "PASS" or "FAIL")
                        self.reporter.notify_progress(self.reporter.notify_checkLog,"Default Password of Prism: "+cvm_ip+" =Changed"+" (Expected: =Not Changed)",(passed and "PASS" or "FAIL"))
                    else:
                        passed = False
                        message += ", " +"Default Password of Prism: "+cvm_ip+" =Connection Failed"+" (Expected: =Not Changed)"+"#"+(passed and "PASS" or "FAIL")
                        self.reporter.notify_progress(self.reporter.notify_checkLog,"Default Password of Prism: "+cvm_ip+" =Connection Failed"+" (Expected: =Not Changed)",(passed and "PASS" or "FAIL"))
                except:        
                        passed = False
                        message += ", " +"Default Password of Prism: "+cvm_ip+" =Connection Failed"+" (Expected: =Not Changed)"+"#"+(passed and "PASS" or "FAIL")
                        self.reporter.notify_progress(self.reporter.notify_checkLog,"Default Password of Prism: "+cvm_ip+" =Connection Failed"+" (Expected: =Not Changed)",(passed and "PASS" or "FAIL"))

        #check IPMI passwords
        if len(cvm_ip_list) > 0:
            ipmi_ip_list = []
            ipmi_flag = False
            for cvm_ip in cvm_ip_list:
                if ipmi_flag == False:
                    prismURL = "https://"+cvm_ip+":9440/PrismGateway/services/rest/v1/hosts/"
                    headers = {'content-type': 'application/json'}
                    try: 
                        prismResonse = requests.get(prismURL,headers=headers,auth=("admin", "admin"), verify=False)
                        if prismResonse.status_code == 200:
                            responseHostsJson = json.loads(prismResonse.text)
                            host_entities = responseHostsJson["entities"]
                            for entity in host_entities:
                                ipmi_ip = entity["ipmiAddress"]
                                ipmi_ip_list.append(ipmi_ip)
                                ipmi_flag = True
                    except:
                            pass
            if len(ipmi_ip_list) > 0: 
                for ipmiip in ipmi_ip_list:
                    flag, ipmi_ssh = self.get_ipmi_ssh_connection(ipmiip)

                    if flag == "Success":
                        passed = True
                        message += ", " +"Default Password of IPMI: "+ipmiip+" =Not Changed"+" (Expected: =Not Changed)"+"#"+(passed and "PASS" or "FAIL")
                        self.reporter.notify_progress(self.reporter.notify_checkLog,"Default Password of IPMI: "+ipmiip+" =Not Changed"+" (Expected: =Not Changed)",(passed and "PASS" or "FAIL"))
                    elif flag == "Authentication Exception":
                        passed = False
                        message += ", " +"Default Password of IPMI: "+ipmiip+" =Changed"+" (Expected: =Not Changed)"+"#"+(passed and "PASS" or "FAIL")
                        self.reporter.notify_progress(self.reporter.notify_checkLog,"Default Password of IPMI: "+ipmiip+" =Changed"+" (Expected: =Not Changed)",(passed and "PASS" or "FAIL"))
                    elif flag == "SSH Connection Failed":
                        passed = False
                        message += ", " +"Default Password of IPMI: "+ipmiip+" =SSH Connection Failed"+" (Expected: =Not Changed)"+"#"+(passed and "PASS" or "FAIL")
                        self.reporter.notify_progress(self.reporter.notify_checkLog,"Default Password of IPMI: "+ipmiip+" =SSH Connection Failed"+" (Expected: =Not Changed)",(passed and "PASS" or "FAIL"))

                    VCChecker.ipmi_ssh = None

        passed_all = passed_all and passed 
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_default_password - Exit")
        return passed_all,message,path_curr

    @checkgroup("esxi_checks", "Check if only 10GBps VMNIC are Connected", ["performance"], "10GBps VMNIC Connected")
    def check_vmnic_10Gbps(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_vmnic_10Gbps - Enter")
        path='content.rootFolder.childEntity.hostFolder.childEntity.host.configManager.networkSystem.networkConfig.pnic'
        host_networks = self.get_vc_property(path)
        message = ""
        pass_all=True
        for key, network in host_networks.iteritems():
            passed = True
            if network == "Not-Configured":
                continue
            speed_flag = False
            duplex_flag = False

            for physical_nic in network:
                link_speed = physical_nic.spec.linkSpeed

                if link_speed is not None:
                    speed = link_speed.speedMb
                    duplexMode = link_speed.duplex

                    if speed == 'None' and duplexMode == 'None':
                        speed_flag = False
                    elif speed == 10000 and duplexMode != True:
                        speed_flag = True
                        duplex_flag = False
                    elif speed == 10000 and duplexMode == True:
                        speed_flag = True
                        duplex_flag = True
                        continue

            if speed_flag == True and duplex_flag == True:
                passed = True
                message += ", " +key+"=10GBps VMNIC Connected and in Full Duplex Mode (Expected: =10GBps VMNIC Connected and in Full Duplex Mode)"+"#"+(True and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,key+"=10GBPs VMNIC Connected and in Full Duplex Mode (Expected: =10GBps VMNIC Connected and in Full Duplex Mode)",(True and "PASS" or "FAIL"))
            elif speed_flag == True and duplex_flag == False:
                passed = False
                message += ", " +key+"=10GBps VMNIC Connected but Not in Full Duplex Mode (Expected: =10GBps VMNIC Connected and in Full Duplex Mode)"+"#"+(False and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,key+"=10GBps VMNIC Connected but Not in Full Duplex Mode (Expected: =10GBps VMNIC Connected and in Full Duplex Mode)",(False and "PASS" or "FAIL"))
            elif speed_flag == False:
                passed = False
                message += ", " +key+"=10GBps VMNIC Not Connected (Expected: =10GBps VMNIC Connected and in Full Duplex Mode)"+"#"+(False and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,key+"=10GBps VMNIC Not Connected (Expected: =10GBps VMNIC Connected and in Full Duplex Mode)",(False and "PASS" or "FAIL"))                        

            pass_all = pass_all and passed
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_vmnic_10Gbps - Exit")
        return pass_all, message, path

    @checkgroup("esxi_checks", "Both 10GBps & 1GBps VMNIC Connected to VDS or VSS",["configurability","manageability","availability"],"10GBps and 1GBps VMNIC are Not Connected to VDS or VSS")
    def check_vmnic_10Gbps_and_1GBps(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_vmnic_10Gbps_and_1GBps - Enter")
        path_curr='content.rootFolder.childEntity.hostFolder.childEntity.host'
        clusters_map = self.get_vc_property(path_curr)

        message = ""
        passed_all = True
        path = None
        for datacenter, host_list in clusters_map.iteritems():
            passed = True
            #print datacenter
            if host_list == "Not-Configured" :
                continue
            elif len(host_list)==0: 
                #condtion to Check if no host found
                continue
            for host in host_list:
                host_ip = host.name
                if self.authconfig['host'] != '':
                    if host_ip not in self.authconfig['host']:
                        #print "skipping host "+host_name
                        continue
                check_host_ip = str(host_ip).replace(".", "*")
                path = 'content.rootFolder.childEntity.hostFolder.childEntity.host[name='+check_host_ip+'].configManager.networkSystem.networkConfig.pnic'
                host_networks = self.get_vc_property(path)
                one_gbps_vmnic_map = []
                ten_gbps_vmnic_map = []
                for key, network in host_networks.iteritems():
                    passed = True
                    if network == "Not-Configured":
                        continue

                    for physical_nic in network:
                        link_speed = physical_nic.spec.linkSpeed
                        device_name = physical_nic.device

                        if link_speed is not None:
                            speed = link_speed.speedMb

                            if speed == 'None':
                                continue
                            elif speed == 10000:   
                                ten_gbps_vmnic_map.append(device_name)
                            elif speed == 1000:    
                                one_gbps_vmnic_map.append(device_name)

                if len(one_gbps_vmnic_map)==0:
                    passed = True
                    message += ", " +datacenter+"@"+host_ip+"=1GBps VMNIC Not Present (Expected: =Both 10GBps and 1GBps VMNIC are Not Connected to VDS or VSS)"+"#"+(passed and "PASS" or "FAIL")
                    self.reporter.notify_progress(self.reporter.notify_checkLog,datacenter+"."+host_ip+"=1GBps VMNIC Not Present (Expected: =Both 10GBps and 1GBps VMNIC are Not Connected to VDS or VSS)",(passed and "PASS" or "FAIL"))                
                elif len(one_gbps_vmnic_map) > 0 and len(ten_gbps_vmnic_map) > 0:
                    vswitch_path='content.rootFolder.childEntity.hostFolder.childEntity.host[name='+check_host_ip+'].configManager.networkSystem.networkConfig.vswitch.spec.policy.nicTeaming.nicOrder.activeNic'
                    vswitch_nic_map = self.get_vc_property(vswitch_path)
                    one_gbps_flag = False
                    ten_gbps_flag = False

                    for vswitch, vmnic_list in vswitch_nic_map.iteritems():
                        if vmnic_list == "Not-Configured" :
                            continue
                        else:
                            value_list = vmnic_list
                            for vnicname in value_list:
                                if vnicname in one_gbps_vmnic_map:
                                    one_gbps_flag = True
                                elif vnicname in ten_gbps_vmnic_map:   
                                    ten_gbps_flag = True

                        if one_gbps_flag and ten_gbps_flag:
                            passed = False
                            message += ", " +datacenter+"@"+host_ip+"=1GBps and 10 GBps VMNIC are Present Together (Expected: =Both 10GBps and 1GBps VMNIC are Not Connected to VDS or VSS)"+"#"+(passed and "PASS" or "FAIL")
                            self.reporter.notify_progress(self.reporter.notify_checkLog,datacenter+"@"+host_ip+"=1GBps and 10 GBps VMNIC are Present Together (Expected: =Both 10GBps and 1GBps VMNIC are Not Connected to VDS or VSS)",(passed and "PASS" or "FAIL"))                
                        else:
                            passed = True
                            message += ", " +datacenter+"@"+host_ip+"=1GBps and 10 GBps VMNIC Not Present Together (Expected: =Both 10GBps and 1GBps VMNIC are Not Connected to VDS or VSS)"+"#"+(passed and "PASS" or "FAIL")
                            self.reporter.notify_progress(self.reporter.notify_checkLog,datacenter+"@"+host_ip+"=1GBps and 10 GBps VMNIC Not Present Together (Expected: =Both 10GBps and 1GBps VMNIC are Not Connected to VDS or VSS)",(passed and "PASS" or "FAIL"))                

                passed_all = passed_all and passed  
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_vmnic_10Gbps_and_1GBps - Exit")
        return passed_all, message, path

    @checkgroup("vcenter_server_checks", "JVM Memory for vSphere Server", ["performance"], "Memory Configured")
    def check_jvm_memory(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_jvm_memory - Enter")
        check_list = ["JVM Memory for vSphere Web Client", "JVM Memory for Inventory Services", "JVM Memory for Storage Base Profiles"]
        message = ""
        passed_all = True
        passed = True
        memory = None

        flag,vcenter_server_ssh,vcenter_ip = self.get_vcenter_server_ssh_connection()
        if flag == "vCenter IP Not configured":
            passed = False
            message += ", " +"JVM Memory for vSphere Server =Cannot Determine vCenter Server IP"+" (Expected: =JVM Memory Information)"+"#"+("FAIL")
            self.reporter.notify_progress(self.reporter.notify_checkLog,"JVM Memory for vSphere Server =Cannot Determine vCenter Server IP"+" (Expected: =JVM Memory Information)",("FAIL"))
        elif flag == "SSH Connection Failed" or flag == "Authentication Exception":
            passed = False
            message += ", " +"JVM Memory for vSphere Server =SSH Connection Failed"+" (Expected: =JVM Memory Information)"+"#"+("FAIL")
            self.reporter.notify_progress(self.reporter.notify_checkLog,"JVM Memory for vSphere Server =SSH Connection Failed"+" (Expected: =JVM Memory Information)",("FAIL"))
        elif vcenter_server_ssh is not None and vcenter_server_ssh._transport is not None:
            server_version , inventory_size = self.get_inventory_info()
            
            for check_name in check_list:
                time.sleep(1)
                if check_name == "JVM Memory for vSphere Web Client":
                    cmd_memory = "cat /usr/lib/vmware-vsphere-client/server/wrapper/conf/wrapper.conf | grep \"wrapper.java.maxmemory\"" 
                    expected_result = self.get_vcenterserver_default_memory(server_version, inventory_size, "vsphere_web_client_memory")
                elif check_name == "JVM Memory for Inventory Services":
                    cmd_memory = "cat /usr/lib/vmware-vpx/inventoryservice/wrapper/conf/wrapper.conf | grep \"wrapper.java.maxmemory\""    
                    expected_result = self.get_vcenterserver_default_memory(server_version, inventory_size, "inventory_service_memory")
                elif check_name == "JVM Memory for Storage Base Profiles":
                    cmd_memory = "cat /usr/lib/vmware-vpx/sps/wrapper/conf/wrapper.conf | grep \"wrapper.java.maxmemory\""    
                    expected_result = self.get_vcenterserver_default_memory(server_version, inventory_size, "storage_management_memory")

                stdin, stdout, stderr =  vcenter_server_ssh.exec_command(cmd_memory) 
                for line in stdout:
                    if line.startswith('wrapper.java.maxmemory'):
                        memory = line.split("=")[1]

                passed,message = self.jvm_memory_helper(check_name,memory,expected_result,message)
        else:
            passed = False
            message += ", " +"JVM Memory for vSphere Server =Cannot Determine"+" (Expected: =JVM Memory Information)"+"#"+("FAIL")
            self.reporter.notify_progress(self.reporter.notify_checkLog,"JVM Memory for vSphere Server =Cannot Determine"+" (Expected: =JVM Memory Information)",("FAIL"))

        passed_all = passed_all and passed

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_jvm_memory - Exit")
        return passed_all,message,''

    def jvm_memory_helper(self,check_name, memory, expected_result, message):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: jvm_memory_helper - Enter")
        passed = True
        if memory is not None and int(memory.strip()) == expected_result:
            message += ", " +check_name+" = "+memory.strip()+" (Expected: = "+str(expected_result)+")"+"#"+(passed and "PASS" or "FAIL")
            self.reporter.notify_progress(self.reporter.notify_checkLog,check_name+" = "+memory.strip()+" (Expected: = "+str(expected_result)+")",(passed and "PASS" or "FAIL"))              
        elif memory is not None:
            passed = False
            message += ", " +check_name+" = "+memory.strip()+" (Expected: = "+str(expected_result)+")"+"#"+(passed and "PASS" or "FAIL")
            self.reporter.notify_progress(self.reporter.notify_checkLog,check_name+" = "+memory.strip()+" (Expected: = "+str(expected_result)+")",(passed and "PASS" or "FAIL"))              
        else:
            passed = False
            message += ", " +check_name+" = None (Expected: = "+str(expected_result)+")"+"#"+(passed and "PASS" or "FAIL")
            self.reporter.notify_progress(self.reporter.notify_checkLog,check_name+" = None (Expected: = "+str(expected_result)+")",(passed and "PASS" or "FAIL"))

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: jvm_memory_helper - Exit")
        return passed, message


    def get_inventory_info(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: get_inventory_info - Enter")
        host_count = 0
        vm_count = 0
        vcenter_guest_info = self.get_vc_property('content.about')
        for key, guest in vcenter_guest_info.iteritems():
            vcenter_version = guest.version
            vcenter_OS = guest.osType
        if vcenter_version == "5.5.0" and "linux" in vcenter_OS:
            server_version = "vcenter_server_appliance_5.5.x"
        elif vcenter_version == "5.1.0" and "linux" in vcenter_OS:
            server_version = "vcenter_server_appliance_5.1.x"
        elif  vcenter_version == "5.1.0" or vcenter_version == "5.1.0" and "windows" in vcenter_OS:
            server_version = "vcenter_server_5.x"

        hosts = self.get_vc_property('content.rootFolder.childEntity.hostFolder.childEntity.host.vm')
        for host in hosts.keys():
            host_configured=hosts[host]
            if host_configured == "Not-Configured":
                continue
            else:
                host_count += 1 
                for vm_configured in host_configured:
                    guest_info = vm_configured.guest
                    if guest_info is not None:
                        vm_count += 1

        if host_count <= 100 or vm_count <= 1000:
            inventory_size = "small_inventory"
        elif host_count > 100 and host_count <= 400 or vm_count > 1000 and vm_count <= 4000:
            inventory_size = "medium_inventory"
        elif host_count > 400 or vm_count > 4000:
            inventory_size = "large_inventory"
        else:
            inventory_size = "small_inventory"
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: get_inventory_info - Exit")
        return server_version, inventory_size

    def get_vcenterserver_vm(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: get_vcenterserver_vm - Enter")
        vcenter_ip = self.get_vcenter_server_ip()
        hosts = self.get_vc_property('content.rootFolder.childEntity.hostFolder.childEntity.host.vm')

        for host in hosts.keys():
            host_vm_list = hosts[host]
            if host_vm_list == "Not-Configured":
                continue
            for vm in host_vm_list:
                guest_info = vm.guest
                if guest_info is not None and guest_info.ipAddress == vcenter_ip:
                    return vm

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: get_vcenterserver_vm - Exit")
        return None

    def get_vcenterserver_default_memory(self, server_version, inventory_size, property):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: get_vcenterserver_default_memory - Enter")
        if len(VCChecker.vcenter_stats_config) == 0:
            vcenter_stats_path=os.path.abspath(os.path.dirname(__file__)) + os.path.sep + ".." + os.path.sep +"conf" + os.path.sep + "vcenter_stats.json"
            fp = open(vcenter_stats_path, 'r')
            VCChecker.vcenter_stats_config = json.load(fp)
            fp.close()
        else:
            pass

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: get_vcenterserver_default_memory - Exit")
        return VCChecker.vcenter_stats_config[server_version][inventory_size][property]

    @checkgroup("vcenter_server_checks", "Memory Utilization of vCenter Server",["performance"],"Memory Utilization")
    def check_memory_utilization(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_memory_utilization - Enter")
        message = ""
        passed = True
        vm = self.get_vcenterserver_vm()
        if vm is not None:
            memory_utilization = vm.summary.quickStats.guestMemoryUsage
            if memory_utilization is not None:
                message += ", " +"Memory Utilization of vCenter Server = "+str(memory_utilization)+" (Expected: =Memory Utilization)"+"#"+(passed and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"Memory Utilization of vCenter Server = "+str(memory_utilization)+" (Expected: =Memory Utilization)",(passed and "PASS" or "FAIL"))
            else:
                passed = False
                message += ", " +"Memory Utilization of vCenter Server =None (Expected: =Memory Utilization)"+"#"+(passed and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"Memory Utilization of vCenter Server =None (Expected: =Memory Utilization)",(passed and "PASS" or "FAIL"))                    
        else:
            passed = False
            message += ", " +"Memory Utilization of vCenter Server =Cannot Determine (Expected: =Memory Utilization)"+"#"+(passed and "PASS" or "FAIL")
            self.reporter.notify_progress(self.reporter.notify_checkLog,"Memory Utilization of vCenter Server =Cannot Determine (Expected: =Memory Utilization)",(passed and "PASS" or "FAIL"))                                                                                                                                              

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_memory_utilization - Exit")
        return passed, message,''

    @checkgroup("vcenter_server_checks", "Memory Assigned to vCenter Server",["performance"],"Memory Assigned")
    def check_memory_assigned(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_memory_assigned - Enter")
        message = ""     
        passed = True
        vm = self.get_vcenterserver_vm()
        server_version , inventory_size = self.get_inventory_info()
        expected_result = self.get_vcenterserver_default_memory(server_version, inventory_size, "vcenter_server_memory")
        if vm is not None:
            memory_assigned = vm.config.hardware.memoryMB
            if memory_assigned is not None and memory_assigned == expected_result:
                message += ", " +"Memory Assigned to vCenter Server = "+str(memory_assigned)+" (Expected: = "+str(expected_result)+")"+"#"+(passed and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"Memory Assigned to vCenter Server = "+str(memory_assigned)+" (Expected: = "+str(expected_result)+")",(passed and "PASS" or "FAIL"))
            else:
                passed = False
                message += ", " +"Memory Assigned to vCenter Server = "+str(memory_assigned)+" (Expected: = "+str(expected_result)+")"+"#"+(passed and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"Memory Assigned to vCenter Server = "+str(memory_assigned)+" (Expected: = "+str(expected_result)+")",(passed and "PASS" or "FAIL"))                    
        else:
            passed = False
            message += ", " +"Memory Assigned to vCenter Server =Cannot Determine (Expected: = "+str(expected_result)+")"+"#"+(passed and "PASS" or "FAIL")
            self.reporter.notify_progress(self.reporter.notify_checkLog,"Memory Assigned to vCenter Server =Cannot Determine (Expected: = "+str(expected_result)+")",(passed and "PASS" or "FAIL"))

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_memory_assigned - Exit")
        return passed, message,''
 
    @checkgroup("vcenter_server_checks", "CPU Utilization of vCenter Server", ["performance"], "CPU Utilization")
    def check_CPU_utilization(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_CPU_utilization - Enter")
        message = ""
        passed = True
        vm = self.get_vcenterserver_vm()
        if vm is not None:
            cpu_utilization = vm.summary.quickStats.overallCpuUsage
            if cpu_utilization is not None:
                message += ", " +"CPU Utilization of vCenter Server = "+str(cpu_utilization)+" (Expected: =CPU Utilization)"+"#"+(passed and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"CPU Utilization of vCenter Server = "+str(cpu_utilization)+" (Expected: =CPU Utilization)",(passed and "PASS" or "FAIL"))
            else:
                passed = False
                message += ", " +"CPU Utilization of vCenter Server =None (Expected: =CPU Utilization)"+"#"+(passed and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"Memory Utilization of vCenter Server =None (Expected: =CPU Utilization)",(passed and "PASS" or "FAIL"))                    
        else:
            passed = False
            message += ", " +"CPU Utilization of vCenter Server =Cannot Determine (Expected: =CPU Utilization)"+"#"+(passed and "PASS" or "FAIL")
            self.reporter.notify_progress(self.reporter.notify_checkLog,"CPU Utilization of vCenter Server =Cannot Determine (Expected: =CPU Utilization)",(passed and "PASS" or "FAIL"))

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_CPU_utilization - Exit")
        return passed, message,''
 
    @checkgroup("vcenter_server_checks", "CPUs Assigned to vCenter Server", ["performance"], "Number of CPU Assigned")
    def check_CPU_assigned(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_CPU_assigned - Enter")
        message = ""
        passed = True
        vm = self.get_vcenterserver_vm()
        server_version, inventory_size = self.get_inventory_info()
        expected_result = self.get_vcenterserver_default_memory(server_version, inventory_size, "number_of_cpu")
        if vm is not None:
            cpu_assigned = vm.config.hardware.numCPU
            if cpu_assigned is not None and cpu_assigned == expected_result:
                message += ", " +"CPUs Assigned to vCenter Server = "+str(cpu_assigned)+" (Expected: = "+str(expected_result)+")"+"#"+(passed and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"CPUs Assigned to vCenter Server = "+str(cpu_assigned)+" (Expected: = "+str(expected_result)+")",(passed and "PASS" or "FAIL"))
            else:
                passed = False
                message += ", " +"CPUs Assigned to vCenter Server = "+str(cpu_assigned)+" (Expected: = "+str(expected_result)+")"+"#"+(passed and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"CPUs Assigned to vCenter Server = "+str(cpu_assigned)+" (Expected: = "+str(expected_result)+")",(passed and "PASS" or "FAIL"))                    
        else:
            passed = False
            message += ", " +"CPUs Assigned to vCenter Server =Cannot Determine (Expected: = "+str(expected_result)+")"+"#"+(passed and "PASS" or "FAIL")
            self.reporter.notify_progress(self.reporter.notify_checkLog,"CPUs Assigned to vCenter Server =Cannot Determine (Expected: = "+str(expected_result)+")",(passed and "PASS" or "FAIL"))

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_CPU_assigned - Exit")                                                                                                                                                                   
        return passed ,message,''  

    @checkgroup("vcenter_server_checks", "Validate vCenter Server has VMware Tools installed and is up to date", ["performance"], "Tools Ok")
    def check_vcenter_server_tool_status(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_vcenter_server_tool_status - Enter")
        message = ""
        passed = True
        vm = self.get_vcenterserver_vm()
        if vm is not None:
            guest_info = vm.guest
            toolsStatus=guest_info.toolsStatus
            toolsStatus_expected="toolsOk"
            if toolsStatus == toolsStatus_expected :
                self.reporter.notify_progress(self.reporter.notify_checkLog, "vCenter Server VMware Tools installed Status="+toolsStatus  + " (Expected: ="+toolsStatus_expected+") " , (True and "PASS" or "FAIL"))
            else:
                passed = False
                self.reporter.notify_progress(self.reporter.notify_checkLog, "vCenter Server VMware Tools installed Status="+toolsStatus  + " (Expected: ="+toolsStatus_expected+") " , (False and "PASS" or "FAIL"))
            message += ", "+"vCenter Server VMware Tools installed Status="+toolsStatus  + " (Expected: ="+toolsStatus_expected+") " +"#"+((toolsStatus == toolsStatus_expected) and "PASS" or "FAIL")
        else:
            passed = False
            self.reporter.notify_progress(self.reporter.notify_checkLog, "vCenter Server VMware Tools installed Status =Cannot Determine (Expected: =toolsOk)" , (passed and "PASS" or "FAIL"))
            message += ", "+"vCenter Server VMware Tools installed Status =Cannot Determine (Expected: =toolsOk)" +"#"+(passed and "PASS" or "FAIL")

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_vcenter_server_tool_status - Exit")
        return passed,message,''

    @checkgroup("vcenter_server_checks", "Error Messages in vpxd.log", ["configurability","manageability","availability","security"], "Error Count")
    def check_vpxd_logs(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_vpxd_logs - Enter")
        message = ""
        passed_all = True
        passed = True
        error_count = 0
        flag,vcenter_server_ssh,vcenter_ip = self.get_vcenter_server_ssh_connection()

        if flag == "vCenter IP Not configured":
            passed = False
            message += ", " +"Error Messages in vpxd.log =Cannot Determine vCenter Server IP"+" (Expected: =Error Count)"+"#"+("FAIL")
            self.reporter.notify_progress(self.reporter.notify_checkLog,"Error Messages in vpxd.log =Cannot Determine vCenter Server IP"+" (Expected: =Error Count)",("FAIL"))
        elif flag == "SSH Connection Failed" or flag == "Authentication Exception":
            passed = False
            message += ", " +"Error Messages in vpxd.log =SSH Connection Failed"+" (Expected: =Error Count)"+"#"+("FAIL")
            self.reporter.notify_progress(self.reporter.notify_checkLog,"Error Messages in vpxd.log =SSH Connection Failed"+" (Expected: =Error Count)",("FAIL"))
        elif vcenter_server_ssh is not None and vcenter_server_ssh._transport is not None:
            cmd_error = "cat /var/log/vmware/vpx/vpxd.log | grep \"Error\" | grep -v \"User \'root\' running command\""    
            stdin, stdout, stderr =  vcenter_server_ssh.exec_command(cmd_error)     

            for line in stdout:
                error_count+=1
            if error_count > 50:
                message += ", " +"Error Messages in vpxd.log = "+str(error_count)+" (Expected: =Less than 50)"+"#"+(False and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"Error Messages in vpxd.log = "+str(error_count)+" (Expected: =Less than 50)",(False and "PASS" or "FAIL"))
                passed = False
            elif error_count <= 50:
                message += ", "+"Error Messages in vpxd.log = "+str(error_count)+" (Expected: =Less than 50)"+"#"+(True and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"Error Messages in vpxd.log = "+str(error_count)+" (Expected: =Less than 50)",(True and "PASS" or "FAIL"))
        else:
            passed = False
            message += ", " +"Error Messages in vpxd.log =Cannot Determine"+" (Expected: =Error Count)"+"#"+("FAIL")
            self.reporter.notify_progress(self.reporter.notify_checkLog,"Error Messages in vpxd.log =Cannot Determine"+" (Expected: =Error Count)",("FAIL"))
                                   
        passed_all = passed_all and passed
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_vpxd_logs - Exit")
        return passed_all ,message,''

    def get_vcenter_server_ip(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: get_vcenter_server_ip - Enter")
        vcenter_ip = None
        path_curr='content.setting.setting[key=VirtualCenter*AutoManagedIPV4].value'
        vcenter_ipv4 = self.get_vc_property(path_curr)
        for key, ip in vcenter_ipv4.iteritems():
            vcenter_ip=ip

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: get_vcenter_server_ip - Exit")
        return vcenter_ip  

    def get_vcenter_server_ssh_connection(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: get_vcenter_server_ssh_connection - Enter")
        vcenter_ip = self.get_vcenter_server_ip()
        if vcenter_ip == None :
            return "vCenter IP Not configured",None,None
        if VCChecker.vcenter_server_ssh is None:
                try:
                    VCChecker.vcenter_server_ssh = paramiko.SSHClient()
                    VCChecker.vcenter_server_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    VCChecker.vcenter_server_ssh.connect(vcenter_ip, username="root", password="vmware")
                except paramiko.AuthenticationException:
                    return "Authentication Exception",None,vcenter_ip
                except paramiko.SSHException, e:
                    return "SSH Connection Failed",None,vcenter_ip
                except socket.error, e:
                    return "SSH Connection Failed",None,vcenter_ip
        else:
            pass

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: get_vcenter_server_ssh_connection - Exit")
        return  "Success",VCChecker.vcenter_server_ssh,vcenter_ip

    @checkgroup("vcenter_server_checks", "vCenter Server Disk Utilization", ["performance","manageability"], "Disk Utilization Information")
    def check_disk_utilization(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_disk_utilization - Enter")
        line_map = {}
        line_count = 0
        message = ""
        passed_all = True
        passed = True
        flag, vcenter_server_ssh, vcenter_ip = self.get_vcenter_server_ssh_connection()

        if flag == "vCenter IP Not configured":
            passed = False
            message += ", " +"vCenter Server Disk Utilization =Cannot Determine vCenter Server IP"+" (Expected: =Disk Utilization Information)"+"#"+("FAIL")
            self.reporter.notify_progress(self.reporter.notify_checkLog,"vCenter Server Disk Utilization =Cannot Determine vCenter Server IP"+" (Expected: =Disk Utilization Information)",("FAIL"))
        elif flag == "SSH Connection Failed" or flag == "Authentication Exception":
            passed = False
            message += ", " +"vCenter Server Disk Utilization =SSH Connection Failed"+" (Expected: =Disk Utilization Information)"+"#"+("FAIL")
            self.reporter.notify_progress(self.reporter.notify_checkLog,"vCenter Server Disk Utilization =SSH Connection Failed"+" (Expected: =Disk Utilization Information)",("FAIL"))              
        elif vcenter_server_ssh is not None and vcenter_server_ssh._transport is not None:
            cmd_disk = "df -h"    
            stdin, stdout, stderr =  vcenter_server_ssh.exec_command(cmd_disk)

            for line in stdout:
                line_count+=1
                line_map[line_count] = line

            if line_count > 0:
                passed = True
                message += ", " +"vCenter Server Disk Utilization of "+vcenter_ip+"="+'\n'.join(line_map.values())+" (Expected: =Disk Utilization Information)"+"#"+(passed and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"vCenter Server Disk Utilization of "+vcenter_ip+"="+"                                                                         \n"+'\n'.join(line_map.values())+" (Expected: =Disk Utilization Information)",(passed and "PASS" or "FAIL"))
            elif line_count == 0:
                passed = False
                message += ", "+"vCenter Server Disk Utilization of "+vcenter_ip+"="+"No values fetched from SSH"+" (Expected: =Disk Utilization Information)"+"#"+(passed and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"vCenter Server Disk Utilization of "+vcenter_ip+"=No values fetched from SSH (Expected: =Disk Utilization Information)",(passed and "PASS" or "FAIL"))
        else:
            passed = False
            message += ", " +"vCenter Server Disk Utilization =Cannot Determine"+" (Expected: =Disk Utilization Information)"+"#"+("FAIL")
            self.reporter.notify_progress(self.reporter.notify_checkLog,"vCenter Server Disk Utilization =Cannot Determine"+" (Expected: =Disk Utilization Information)",("FAIL"))

        passed_all = passed_all and passed

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_disk_utilization - Exit")
        return passed_all ,message,''

    @checkgroup("vcenter_server_checks", "Validate vCenter Server License Expiration Date", ["availability"], "No expiration date or expiration date less than 60 days")
    def check_vcenter_server_license_expiry(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_vcenter_server_license_expiry - Enter")
        expirationDate = self.get_vc_property('content.licenseManager.evaluation.properties[key=expirationDate].value')
        message = ""
        passed = False
        for item, expiry_date in expirationDate.iteritems():
            #Currently timezone is not considered for the date difference / Need to add
            xexpiry = datetime.datetime(expiry_date.year,expiry_date.month, expiry_date.day)
            valid_60_days = (xexpiry - (datetime.datetime.today() + datetime.timedelta(60))).days > 60 or (xexpiry - (datetime.datetime.today() + datetime.timedelta(60))).days < 0
            self.reporter.notify_progress(self.reporter.notify_checkLog,"License Expiration Validation date:: " + str(expiry_date) + " (Expected: =Not within next 60 days or always valid)" , (valid_60_days and "PASS" or "FAIL"))
            passed = passed and valid_60_days
            message += ", "+"License Expiration Validation = " + str(expiry_date) + " (Expected: =Not within next 60 days or always valid) "+"#"+((valid_60_days) and "PASS" or "FAIL")

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_vcenter_server_license_expiry - Exit")
        return passed, message,''

    @checkgroup("vcenter_server_checks", "vCenter Server Plugins", ["performance"], "List of plugins")
    def check_vcenter_server_plugins(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_vcenter_server_plugins - Enter")
        vcenter_plugins_map = self.get_vc_property('content.extensionManager.extensionList')
        message = ""
        passed = True
        plug_list=[]
        for key, plugins in vcenter_plugins_map.iteritems():
            if plugins ==None:
                continue
            for plugin in plugins:
                plug_list.append(plugin.description.label)

        if len(plug_list) > 0:
            self.reporter.notify_progress(self.reporter.notify_checkLog,"vCenter Plugins= [" + ','.join(set(plug_list)) + "] (Expected: =Plugin List)" , (True and "PASS" or "FAIL"))
            message += ", "+"vCenter Plugins = " + ','.join(set(plug_list)) + " (Expected: =Plugin List) "+"#"+((True) and "PASS" or "FAIL")
        else:
            passed = False
            self.reporter.notify_progress(self.reporter.notify_checkLog,"vCenter Plugins= Plugins-Not-Found (Expected: =Plugin List)" , (False and "PASS" or "FAIL"))
            message += ", "+"vCenter Plugins = Plugins-Not-Found (Expected: =Plugin List) "+"#"+((False) and "PASS" or "FAIL")

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_vcenter_server_plugins - Exit")
        return passed, message, ''

    @checkgroup("vcenter_server_checks", "vCenter Server Role Based Access", ["performance"], "Role Based Access is Implemented")
    def check_vcenter_role_based_access(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_vcenter_role_based_access - Enter")
        vcenter_roleList = self.get_vc_property('content.authorizationManager.roleList')
        message = ""
        passed = True
        role_list=[]
        for key, roles in vcenter_roleList.iteritems():
            if roles ==None:
                continue
            for role in roles:
                role_list.append(role.name)

        if len(role_list) > 0:
            self.reporter.notify_progress(self.reporter.notify_checkLog,"vCenter Server Role Based Access= True (Expected: =True) " , (True and "PASS" or "FAIL"))
            message += ", "+"vCenter Server Role Based Access= True (Expected: =True) " +"#"+((True) and "PASS" or "FAIL")
        else:
            passed = False
            self.reporter.notify_progress(self.reporter.notify_checkLog,"vCenter Server Role Based Access= False (Expected: =True) " , (False and "PASS" or "FAIL"))
            message += ", "+"vCenter Server Role Based Access= False (Expected: =True) "+"#"+((False) and "PASS" or "FAIL")

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_vcenter_role_based_access - Exit")
        return passed,message, ''

    def get_network_resource_pool_settings(self,resource_pool_property):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: get_network_resource_pool_settings - Enter")
        if len(VCChecker.resource_pool_config) == 0:
            resource_pool_path=os.path.abspath(os.path.dirname(__file__)) + os.path.sep + ".." + os.path.sep +"conf" + os.path.sep + "resource_pool.json"
            fp = open(resource_pool_path, 'r')
            VCChecker.resource_pool_config = json.load(fp)
            fp.close()
        else:
            pass 

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: get_network_resource_pool_settings - Exit")
        return VCChecker.resource_pool_config[resource_pool_property]

    @checkgroup("network_and_switch_checks", "Network Resource Pool Settings", ["performance"], "Configured Values")
    def check_network_resource_pool_settings(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_network_resource_pool_settings - Enter")
        path='content.rootFolder.childEntity.networkFolder.childEntity'
        datacenter_networks = self.get_vc_property(path)
        message = ""
        passed = True
        for datacenter in datacenter_networks.keys():
            network_list = datacenter_networks.get(datacenter)
            dvs_found = False
            for network in network_list:
                if isinstance(network,vim.dvs.VmwareDistributedVirtualSwitch):
                    dvs_found = True
                    resource_pool_list = network.networkResourcePool
                    for properties in resource_pool_list:
                        property_key = properties.key
                        limit = properties.allocationInfo.limit
                        if limit == -1:
                            limit = "unlimited"
                        else:
                            limit = "other"
                        level = properties.allocationInfo.shares.level
                        shares = properties.allocationInfo.shares.shares
                        default_settings = self.get_network_resource_pool_settings(property_key)

                        if limit == default_settings["limit"] and shares == default_settings["shares"] and level == default_settings["priority"]:
                            passed = True
                            self.reporter.notify_progress(self.reporter.notify_checkLog, datacenter+"."+network.name+"["+properties.name+"] = [Limit:"+limit+" Shares:"+str(shares)+" Level:"+level+"] (Expected: =[Limit:"+default_settings["limit"]+" Shares:"+str(default_settings["shares"])+" Level:"+default_settings["priority"]+"])" , (passed and "PASS" or "FAIL"))
                            message += ", " +datacenter+"@"+network.name+"@"+"["+properties.name+"] = [Limit:"+limit+" Shares:"+str(shares)+" Level:"+level+"] (Expected: =[Limit:"+default_settings["limit"]+" Shares:"+str(default_settings["shares"])+" Level:"+default_settings["priority"]+"])"+"#"+(passed and "PASS" or "FAIL")
                        else:
                            passed = False
                            self.reporter.notify_progress(self.reporter.notify_checkLog, datacenter+"."+network.name+"["+properties.name+"] = [Limit:"+limit+" Shares:"+str(shares)+" Level:"+level+"] (Expected: =[Limit:"+default_settings["limit"]+" Shares:"+str(default_settings["shares"])+" Level:"+default_settings["priority"]+"])" , (passed and "PASS" or "FAIL"))
                            message += ", " +datacenter+"@"+network.name+"@"+"["+properties.name+"] = [Limit:"+limit+" Shares:"+str(shares)+" Level:"+level+"] (Expected: =[Limit:"+default_settings["limit"]+" Shares:"+str(default_settings["shares"])+" Level:"+default_settings["priority"]+"])"+"#"+(passed and "PASS" or "FAIL")                                

            if dvs_found == False and len(network_list) > 0:
                passed = False
                self.reporter.notify_progress(self.reporter.notify_checkLog, datacenter+"."+network.name+"=False (Expected: =True) " , (passed and "PASS" or "FAIL"))
                message += ", " +datacenter+"@"+network.name+"=False (Expected: =True) "+"#"+(passed and "PASS" or "FAIL")

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_network_resource_pool_settings - Exit")
        return passed, message, path

    @checkgroup("network_and_switch_checks", "Port Group and VLAN Consistency across vSphere Clusters", ["manageability","availability"], "Port Group and VLAN Consistency within cluster")
    def check_portgroup_consistency(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_portgroup_consistency - Enter")
        path = 'content.rootFolder.childEntity.hostFolder.childEntity'
        cluster_map = self.get_vc_property(path)
        passed = True
        passed_all = True
        message = ""
        message_all = ""
        for clusters_key, clusters in cluster_map.iteritems():
            if clusters!="Not-Configured":
                for cluster in clusters:
                    cluster_name = cluster.name
                    if self.authconfig['cluster'] != '':
                        if cluster_name not in self.authconfig['cluster']:
                            #print "skipping "+cluster_name
                            continue
                    postgroup_passed = True
                    vlanid_passed = True
                    port_group_list = []
                    vlan_map = {}
                    hosts = cluster.host
                    for xhost in hosts: 
                        portgroup_list = xhost.configManager.networkSystem.networkConfig.portgroup
                        for port_group in portgroup_list:
                            portgroup_name = port_group.spec.name
                            vlan_id = port_group.spec.vlanId
                            if portgroup_name not in port_group_list:
                                port_group_list.append(portgroup_name)
                                vlan_map[portgroup_name] = str(vlan_id)

                    for xhost in hosts:
                        host_name = xhost.name
                        if self.authconfig['host'] != '':
                            if host_name not in self.authconfig['host']:
                                #print "skipping host "+host_name
                                continue     

                        absent_port_group_list = []
                        individual_port_group_list = []
                        absent_vlanId_map = {}

                        portgroup_list = xhost.configManager.networkSystem.networkConfig.portgroup
                        for port_group in portgroup_list:
                            portgroup_name = port_group.spec.name
                            vlan_id = port_group.spec.vlanId
                            individual_port_group_list.append(portgroup_name)
                            if vlan_id is None:
                                absent_vlanId_map[portgroup_name] = vlan_map[portgroup_name]
                                vlanid_passed = False

                        for port_group in port_group_list:
                            if port_group not in individual_port_group_list:
                                absent_port_group_list.append(port_group)
                                postgroup_passed = False

                        if postgroup_passed and vlanid_passed:
                            self.reporter.notify_progress(self.reporter.notify_checkLog,clusters_key+"."+cluster_name+"."+xhost.name+" =True (Expected: =True)" , (True and "PASS" or "FAIL"))
                            message += ", "+clusters_key+"@"+cluster_name+"@"+xhost.name+" =True (Expected: =True)" +"#"+(True and "PASS" or "FAIL")
                        elif postgroup_passed == False and vlanid_passed == True:
                            passed = False
                            self.reporter.notify_progress(self.reporter.notify_checkLog,clusters_key+"."+cluster_name+"."+xhost.name+" =Missing Port Groups::[" + ','.join(set(absent_port_group_list)) + "] (Expected: =All Port Groups must be Present)" , (postgroup_passed and "PASS" or "FAIL"))
                            message += ", "+clusters_key+"@"+cluster_name+"@"+xhost.name+" =Missing Port Groups::[" + ','.join(set(absent_port_group_list)) + "]::"+xhost.name+" (Expected: =All Port Groups must be Present)"+"#"+(postgroup_passed and "PASS" or "FAIL")
                        elif postgroup_passed == True and vlanid_passed == False:
                            passed = False
                            self.reporter.notify_progress(self.reporter.notify_checkLog,clusters_key+"."+cluster_name+"."+xhost.name+" =Missing VLAN IDs::[" + ','.join(set(absent_vlanId_map.values())) + "] (Expected: =All VLAN IDs must be Present)" , (vlanid_passed and "PASS" or "FAIL"))
                            message += ", "+clusters_key+"@"+cluster_name+"@"+xhost.name+" =Missing VLAN IDs::[" +','.join(set(absent_vlanId_map.values())) + "]::"+xhost.name+" (Expected: =All VLAN IDs must be Present)"+"#"+(vlanid_passed and "PASS" or "FAIL")
            passed_all = passed_all and passed

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_portgroup_consistency - Exit")
        return passed_all, message, path

    @checkgroup("network_and_switch_checks", "Virtual Distributed Switch - Network IO Control", ["performance"], "Enabled")
    def check_virtual_distributed_switch_networ_io_control(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_virtual_distributed_switch_networ_io_control - Enter")
        path = 'content.rootFolder.childEntity.networkFolder.childEntity'
        datacenter_networks = self.get_vc_property(path)
        message = ""
        passed = True
        for datacenter in datacenter_networks.keys():
            network_list = datacenter_networks.get(datacenter)
            dvs_found = False
            for network in network_list:
                if isinstance(network,vim.dvs.VmwareDistributedVirtualSwitch):
                    dvs_found = True
                    nioc_enabled = network.config.networkResourceManagementEnabled
                    self.reporter.notify_progress(self.reporter.notify_checkLog, datacenter+"."+network.name+"="+str(nioc_enabled) + " (Expected: =True) " , (nioc_enabled and "PASS" or "FAIL"))
                    message += ", " +datacenter+"@"+network.name+"="+str(nioc_enabled) + " (Expected: =True) "+"#"+((nioc_enabled) and "PASS" or "FAIL")
                    passed = passed and nioc_enabled

            if dvs_found == False:
                passed =False
                self.reporter.notify_progress(self.reporter.notify_checkLog, datacenter+"@=Not-Configured (Expected: =True) " , (False and "PASS" or "FAIL"))
                message += ", " +datacenter+"=Not-Configured (Expected: =True) "+"#"+((False) and "PASS" or "FAIL")

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_virtual_distributed_switch_networ_io_control - Exit")
        return passed, message, path

    @checkgroup("network_and_switch_checks", "Virtual Distributed Switch - MTU",["performance"],"1500")
    def check_virtual_distributed_switch_mtu(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_virtual_distributed_switch_mtu - Enter")
        path = 'content.rootFolder.childEntity.networkFolder.childEntity'
        datacenter_networks = self.get_vc_property(path)

        message = ""
        pass_all = True
        for datacenter in datacenter_networks.keys():
            network_list = datacenter_networks.get(datacenter)
            dvs_found = False
            maxMtu_expected = 1500
            for network in network_list:
                if isinstance(network,vim.dvs.VmwareDistributedVirtualSwitch):
                    dvs_found = True
                    maxMtu = network.config.maxMtu
                    # default value for maxMtu is 1500. Sometime MOB returns None value. So setting maxMtu value to 1500 as default
                    if maxMtu is None: 
                        maxMtu = 1500

                    if maxMtu == maxMtu_expected:
                        message += ", " +datacenter+"@"+network.name+"@="+str(maxMtu) + " (Expected: ="+str(maxMtu_expected)+")"+"#"+(True and "PASS" or "FAIL")
                        self.reporter.notify_progress(self.reporter.notify_checkLog, datacenter+"."+network.name+"="+str(maxMtu) + " (Expected: ="+str(maxMtu_expected)+") " , ( True and "PASS" or "FAIL"))
                    else:
                        pass_all = False
                        self.reporter.notify_progress(self.reporter.notify_checkLog, datacenter+"."+network.name+"="+str(maxMtu) + " (Expected: ="+str(maxMtu_expected)+") " , ( False and "PASS" or "FAIL"))
                        message += ", " +datacenter+"@"+network.name+"@="+str(maxMtu) + " (Expected: ="+str(maxMtu_expected)+")"+"#"+(False and "PASS" or "FAIL")

            if dvs_found == False:
                pass_all = False
                self.reporter.notify_progress(self.reporter.notify_checkLog, datacenter+"=Not-Configured (Expected: ="+str(maxMtu_expected)+") " , ( False and "PASS" or "FAIL"))
                message += ", " +datacenter+"@=Not-Configured (Expected: ="+str(maxMtu_expected)+")"+"#"+(False and "PASS" or "FAIL")

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_virtual_distributed_switch_mtu - Exit")
        return pass_all, message, path

    @checkgroup("network_and_switch_checks", "Check if vSwitchNutanix has no physical adapters", ["security","performance"], "None")
    def check_vswitch_no_physical_nic(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_vswitch_no_physical_nic - Enter")
        path = 'content.rootFolder.childEntity.hostFolder.childEntity.host.configManager.networkSystem.networkInfo'
        host_networks = self.get_vc_property(path)

        message = ""
        pass_all=True

        for key, network in host_networks.iteritems():
            passed = True
            if network == "Not-Configured":
                continue

            vswitchs=network.vswitch
            if vswitchs is None:
                continue
            vSwitchNutanix_found=False
            for vswitch in vswitchs:
                if vswitch.name == "vSwitchNutanix":
                    vSwitchNutanix_found=True
                    if len(vswitch.pnic)==0:
                        #print vswitch.name+" as no pnic"
                        message += ", " +key+"@"+vswitch.name+"=None (Expected: =None)"+"#"+(True and "PASS" or "FAIL")
                        self.reporter.notify_progress(self.reporter.notify_checkLog,key+"@"+vswitch.name+"=None (Expected: =None)",(True and "PASS" or "FAIL"))
                    else:
                        passed = False
                        pnic_dict={}
                        for nic in network.pnic:
                            pnic_dict[nic.key] = nic.device
                        nic_names = []
                        for pnic in vswitch.pnic:
                            nic_names.append(pnic_dict[pnic])
                        #print vswitch.name+"="+(','.join(nic_names))
                        message += ", " +key+"@"+vswitch.name+"="+(','.join(nic_names))+" (Expected: =None)"+"#"+(False and "PASS" or "FAIL")
                        self.reporter.notify_progress(self.reporter.notify_checkLog,key+"@"+vswitch.name+"="+(','.join(nic_names))+" (Expected: =None)",(False and "PASS" or "FAIL"))
            if vSwitchNutanix_found==False:
                passed = False
                message += ", " +key+"=vSwitchNutanix-Not-Found (Expected: =None)"+"#"+(False and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,key+"=vSwitchNutanix-Not-Found (Expected: =None)",(False and "PASS" or "FAIL"))
            pass_all = passed and pass_all

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_vswitch_no_physical_nic - Exit")
        return pass_all, message, path

    @checkgroup("network_and_switch_checks", "vSwitchNutanix Connected to CVM only", ["manageability","availability","performance"], "CVM")
    def check_vswitchnutanix_connected_to_only_CVM(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_vswitchnutanix_connected_to_only_CVM - Enter")
        path = 'content.rootFolder.childEntity.hostFolder.childEntity.host.configManager.networkSystem.networkInfo'
        host_networks = self.get_vc_property(path)

        message = ""
        pass_all = True
        portgrp = set()
        for key, network in host_networks.iteritems():
            passed = True
            if network == "Not-Configured":
                continue

            vswitchs = network.vswitch
            if vswitchs is None:
                continue
            vSwitchNutanix_found = False

            vSwitchNutanix_key = None
            for vswitch in vswitchs:
                if vswitch.name == "vSwitchNutanix":
                    vSwitchNutanix_found = True
                    vSwitchNutanix_key = vswitch.key
                    break

            if vSwitchNutanix_found == False:
                passed = False
                message += ", " +key+"=vSwitchNutanix-Not-Found (Expected: =None)"+"#"+(False and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,key+"=vSwitchNutanix-Not-Found (Expected: =None)",(False and "PASS" or "FAIL"))
            else:
                for portgroup in network.portgroup:
                    if portgroup.vswitch == vSwitchNutanix_key:
                        portgrp.add(portgroup.spec.name)

        passed = True
        for port_grp_name in portgrp:
            vm_names = self.get_vc_property("content.rootFolder.childEntity.hostFolder.childEntity.network[name="+port_grp_name+"].vm.name")
            for vmkey, name in vm_names.iteritems():
                if name == "Not-Configured":
                    continue
                else:
                    vmkey = vmkey.replace(name,"")
                    if fnmatch.fnmatch(name,"NTNX*CVM"):
                        passed = True
                        message += ", " +vmkey+"="+name+" (Expected: =CVM)"+"#"+(True and "PASS" or "FAIL")
                        self.reporter.notify_progress(self.reporter.notify_checkLog,vmkey+"="+name+" (Expected: =CVM)",(True and "PASS" or "FAIL"))
                    else:
                        passed = False
                        message += ", " +vmkey+"="+name+" (Expected: =CVM)"+"#"+(False and "PASS" or "FAIL")
                        self.reporter.notify_progress(self.reporter.notify_checkLog,vmkey+"="+name+" (Expected: =CVM)",(False and "PASS" or "FAIL"))
                    pass_all = passed and pass_all 

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_vswitchnutanix_connected_to_only_CVM - Exit")
        return pass_all, message, "content.rootFolder.childEntity.hostFolder.childEntity.network.vm"

    @checkgroup("storage_and_vm_checks", "Hardware Acceleration of Datastores", ["performance"], "Supported")
    def check_vStorageSupport(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_vStorageSupport - Enter")
        path = 'content.rootFolder.childEntity.hostFolder.childEntity'
        clusters_object= self.get_vc_property(path)
        message = ""
        pass_all = True

        for dcs_key, clusters in clusters_object.iteritems():
            if clusters == 'Not-Configured' :
                #condition to check if any clusters not found 
                continue

            for cluster in clusters:
                cluster_name=cluster.name

                if self.authconfig['cluster']!='':
                    if cluster_name not in self.authconfig['cluster']:
                        #print "skipping "+cluster_name
                        continue

                if not isinstance(cluster, vim.ClusterComputeResource):
                    #condition to check if host directly attached to cluster
                    continue

                cluster_name = cluster.name
                #Start of Datastore VStorageSupport
                if cluster.environmentBrowser ==None:
                    continue 
                datastore_dict = {}
                datastores = cluster.environmentBrowser.QueryConfigTarget().datastore
                for datastore in datastores:
                    datastore_dict[datastore.name] = datastore.vStorageSupport
                # End of Datastore VStorageSupport

                # Start of datastore mount to host
                if cluster.datastore ==None:
                    #condition to check if any host exist in cluster
                    continue

                for cluster_ds in cluster.datastore:
                    cluster_ds_name=cluster_ds.name
                    if fnmatch.fnmatch(cluster_ds_name,"NTNX-local-ds*"):
                        continue
                    host_mounted_map = {} 
                    for cluster_ds_host_mount in cluster_ds.host:
                        hostname = cluster_ds_host_mount.key.name
                        #host_name=host.name
                        if self.authconfig['host'] != '':
                            if hostname not in self.authconfig['host']:
                                #print "skipping host "+hostname
                                continue
                        if cluster_ds_host_mount.mountInfo.accessible== True:
                            #print cluster_name, hostname , cluster_ds_name ,cluster_ds_host_mount.mountInfo.accessible ,datastore_dict[cluster_ds_name]
                            expected_vStorageSupported="vStorageSupported"
                            actual_vStorageSupported=datastore_dict[cluster_ds_name]

                            message += ", " +dcs_key+"@"+cluster_name+"@"+hostname+"@"+cluster_ds_name+"="+actual_vStorageSupported+ " (Expected: ="+expected_vStorageSupported+")"+"#"+((expected_vStorageSupported == actual_vStorageSupported) and "PASS" or "FAIL")
                            self.reporter.notify_progress(self.reporter.notify_checkLog,dcs_key+"@"+cluster_name+"@"+hostname+"@"+cluster_ds_name+"="+actual_vStorageSupported+ " (Expected: ="+expected_vStorageSupported+")" , ( (expected_vStorageSupported == actual_vStorageSupported) and "PASS" or "FAIL"))
                # End of datastore mount to host            
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_vStorageSupport - Exit")
        return pass_all, message, path + '.host.datastore'

    @checkgroup("storage_and_vm_checks", "USB Device Connected to VM", ["manageability","reliability"], "False")
    def check_usb_disabled(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_usb_disabled - Enter")
        path = 'content.rootFolder.childEntity.hostFolder.childEntity.host.vm.config.hardware.device'
        vms_virtual_hardware = self.get_vc_property(path)
        message = ""
        pass_all=True

        for vms_key, vms_vDevice in vms_virtual_hardware.iteritems():
            passed = True
            if vms_vDevice == 'Not-Configured' :
                #condition to check if any clusters not found 
                continue
            usb_found = False
            for device in vms_vDevice:
                if isinstance(device, vim.vm.device.VirtualUSB):
                    usb_found = True
                    usb_connected=device.connectable.connected
                    passed = not usb_connected
                    message += ", " +vms_key+"="+str(usb_connected) + " (Expected: =False)"+"#"+(not usb_connected and "PASS" or "FAIL")
                    self.reporter.notify_progress(self.reporter.notify_checkLog, vms_key+"="+str(usb_connected) + " (Expected: =False)", (not usb_connected and "PASS" or "FAIL"))
                    break
            if usb_found == False:
                message += ", " +vms_key+"=Not-Attached (Expected: =False)"+"#"+(True and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog, vms_key+"=Not-Attached (Expected: =False)", (True and "PASS" or "FAIL"))
            pass_all = pass_all and passed  

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_usb_disabled - Exit")
        return pass_all, message,path

    @checkgroup("storage_and_vm_checks", "RS-232 Serial Port Connected to VM", ["manageability","reliability"], "False")
    def check_rs232_serial_port_disabled(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_rs232_serial_port_disabled - Enter")
        path = 'content.rootFolder.childEntity.hostFolder.childEntity.host.vm.config.hardware.device'
        vms_virtual_hardware = self.get_vc_property(path)
        message = ""
        pass_all = True

        for vms_key, vms_vDevice in vms_virtual_hardware.iteritems():
            if vms_vDevice == 'Not-Configured' :
                #condition to check if any clusters not found 
                continue
            serial_found = False
            passed = True
            for device in vms_vDevice:
                if isinstance(device, vim.vm.device.VirtualSerialPort):
                    serial_found = True
                    serial_connected = device.connectable.connected
                    passed = not serial_connected
                    message += ", " +vms_key+"="+str(serial_connected) + " (Expected: =False)"+"#"+(( not serial_connected) and "PASS" or "FAIL")
                    self.reporter.notify_progress(self.reporter.notify_checkLog, vms_key+"="+str(serial_connected) + " (Expected: =False)", ((not serial_connected) and "PASS" or "FAIL"))
                    break 
            if serial_found == False:
                message += ", " +vms_key+"=Not-Attached (Expected: =False)"+"#"+(True and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog, vms_key+"=Not-Attached (Expected: =False)", (True and "PASS" or "FAIL"))                   
            pass_all = pass_all and passed

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_rs232_serial_port_disabled - Exit")
        return pass_all, message,path

    @checkgroup("storage_and_vm_checks", "CD-ROM Connected to VM", ["manageability","reliability"], "False")
    def check_cdrom_disabled(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_cdrom_disabled - Enter")
        path = 'content.rootFolder.childEntity.hostFolder.childEntity.host.vm.config.hardware.device'
        vms_virtual_hardware = self.get_vc_property(path)
        message = ""
        pass_all = True

        for vms_key, vms_vDevice in vms_virtual_hardware.iteritems():
            if vms_vDevice == 'Not-Configured' :
                #condition to check if any clusters not found 
                continue
            cdrom_found = False
            passed = True
            for device in vms_vDevice:
                if isinstance(device, vim.vm.device.VirtualCdrom):
                    cdrom_found = True
                    cdrom_connected = device.connectable.connected
                    passed = not cdrom_connected
                    message += ", " +vms_key+"="+str(cdrom_connected) + " (Expected: =False)"+"#"+(( not cdrom_connected) and "PASS" or "FAIL")
                    self.reporter.notify_progress(self.reporter.notify_checkLog, vms_key+"="+str(cdrom_connected) + " (Expected: =False)", ((not cdrom_connected) and "PASS" or "FAIL"))
                    break
            if cdrom_found == False:
                message += ", " +vms_key+"=Not-Attached (Expected: =False)"+"#"+(True and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog, vms_key+"=Not-Attached (Expected: =False)", (True and "PASS" or "FAIL"))
            pass_all = pass_all and passed

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_cdrom_disabled - Exit")                                                                                                                                              
        return pass_all, message, path

    @checkgroup("storage_and_vm_checks", "VM OS Version same as Guest OS Version", ["performance","manageability","configurability"], "OS Versions Should Match")
    def check_VM_OS_Versions(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_VM_OS_Versions - Enter")
        path = 'content.rootFolder.childEntity.hostFolder.childEntity.host.vm.summary'
        vm_list = self.get_vc_property(path)
        message = ""
        passed_all = True

        for vms_key, vm in vm_list.iteritems():
            if vm == 'Not-Configured' :
                #condition to check if any clusters not found 
                continue
            passed=True

            vm_OS_version = vm.config.guestFullName
            guest_OS_version= vm.guest.guestFullName

            if str(vm_OS_version) == str(guest_OS_version):
                self.reporter.notify_progress(self.reporter.notify_checkLog,  vms_key + "="+str(guest_OS_version)+" (Expected: ="+str(vm_OS_version)+" )", ("PASS"))
                message += ", "+vms_key + "="+str(guest_OS_version)+" (Expected: = "+str(vm_OS_version)+")#PASS"
            else:
                self.reporter.notify_progress(self.reporter.notify_checkLog, vms_key + "="+str(guest_OS_version)+" (Expected: ="+str(vm_OS_version)+" )", ("FAIL"))
                message += ", "+vms_key+ "="+str(guest_OS_version)+" (Expected: ="+str(vm_OS_version)+")#FAIL"             

            passed_all = passed_all and passed

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_VM_OS_Versions - Exit")
        return passed_all, message,path


    @checkgroup("cvm_checks", "Memory Reservation Per CVM(MB)", ["performance"], "Equal to size of VM memory")
    def check_memory_reservation_of_cvm(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_memory_reservation_of_cvm - Enter")
        path = 'content.rootFolder.childEntity.hostFolder.childEntity.host.vm[name=NTNX*CVM].summary'
        vms_map = self.get_vc_property(path)
        message = ""
        pass_all = True

        for vms_key, vm in vms_map.iteritems():
            if vm == 'Not-Configured' :
                #condition to check if any clusters not found 
                continue
            passed=True

            vms_key = '@'.join(vms_key.split('@')[0:-1])
            memory_reservation = vm.config.memoryReservation
            vm_memory = vm.config.memorySizeMB

            if memory_reservation == vm_memory:
                message += ", " +vms_key+"="+ str(memory_reservation) + " (Expected: ="+str(vm_memory)+")"+"#"+(True and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog, vms_key+"="+ str(memory_reservation) + " (Expected: ="+str(vm_memory)+")", (True and "PASS" or "FAIL"))
            else:
                passed = False
                message += ", " +vms_key+"=" + str(memory_reservation) + " (Expected: ="+str(vm_memory)+")"+"#"+(True and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog, vms_key+"="+ str(memory_reservation) +" (Expected: ="+str(vm_memory)+")", (True and "PASS" or "FAIL"))
            pass_all = pass_all and passed

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_memory_reservation_of_cvm - Exit")
        return pass_all, message, path

    @checkgroup("storage_and_vm_checks", "VM using the VMXNET3 virtual network device",["performance"], "Vmxnet3")
    def check_vm_using_vmxnet3(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_vm_using_vmxnet3 - Enter")
        path = 'content.rootFolder.childEntity.hostFolder.childEntity.host.vm.config'
        vms = self.get_vc_property(path)
        message = ""
        pass_all = True

        for vm_key, vm in vms.iteritems():
            if vm == 'Not-Configured' :
                #condition to check if any clusters not found 
                continue

            #vm version
            version=vm.version
            #Version Number from version string 
            version_no=int(version.replace("vmx-",""))
            if version_no < 7 :
                #print vm_key , version_no ,"Skipping check"
                #skip check if version is less then 7 as need to check version above 7
                continue

            passed =True
            adapter=set()
            #Device used by VM 
            #print vm_key , version_no
            for device in vm.hardware.device:
                if isinstance(device, vim.vm.device.VirtualEthernetCard):
                    #print "\t",type(device).__class__
                    adapter.add(((type(device).__name__).split('.')[-1]).replace("Virtual",""))
            #print "\t\t", ','.join(adapter)
            if 'Vmxnet3' in adapter:
                passed = True
            else : 
                passed= False

            message += ", " +vm_key+"="+(','.join(adapter))+" (Expected: =Vmxnet3)"+"#"+(passed and "PASS" or "FAIL")
            self.reporter.notify_progress(self.reporter.notify_checkLog,vm_key+"="+(','.join(adapter))+" (Expected: =Vmxnet3)", (passed and "PASS" or "FAIL"))     
            pass_all = pass_all and passed

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_vm_using_vmxnet3 - Exit")
        return pass_all, message,path

    @checkgroup("storage_and_vm_checks", "VM hardware version is the most up to date with the ESXI version",["performance"], "VM hardware version should be in the latest version supported by ESXi in the cluster")
    def check_vm_hardware_version_ailing_with_esxi_version(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_vm_hardware_version_ailing_with_esxi_version - Enter")
        path = 'content.rootFolder.childEntity.hostFolder.childEntity' #.host.vm.config
        clusters_map = self.get_vc_property(path)
        message = ""
        pass_all = True
        for cluster_key, clusters in clusters_map.iteritems():
            if clusters == 'Not-Configured' :
                #condition to check if any clusters not found 
                continue
            for cluster in clusters:
                cluster_name=cluster.name

                if self.authconfig['cluster']!='':
                    if cluster_name not in self.authconfig['cluster']:
                        #print "skipping "+cluster_name
                        continue

                host_version=[]
                for host in cluster.host:
                    if host.config.product.version not in host_version:
                        host_version.append(host.config.product.version)

                if len(host_version) == 0:
                    continue
                elif len(host_version)>1:
                    continue
                else:
                    allhost_version = '.'.join((host_version[0]).split('.')[0:-1])

                    allvm_version = None
                    if allhost_version == "5.1":
                        allvm_version = 10
                    elif allhost_version == "5.5":
                        allvm_version = 9
                    else:
                        continue

                    for host in cluster.host:
                        passed = True
                        host_name = host.name
                        if self.authconfig['host'] != '':
                            if host_name not in self.authconfig['host']:
                                #print "skipping host "+host_name
                                continue

                        for vm in host.vm:
                            vm_name = vm.name
                            version = vm.config.version
                            #Version Number from version string 
                            version_no = int(version.replace("vmx-",""))
                            #if allvm_version > version_no:
                            if version_no >= allvm_version:
                                #print cluster_name, host_name, vm_name, version
                                message += ", " +cluster_key+"@"+cluster_name+"@"+host_name+"@"+vm_name+"="+ version+" (Expected: =Greater than vmx-"+str(allvm_version)+")"+"#"+(True and "PASS" or "FAIL")
                                self.reporter.notify_progress(self.reporter.notify_checkLog,cluster_key+"@"+cluster_name+"@"+host_name+"@"+vm_name+"="+ version+" (Expected: =Greater than vmx-"+str(allvm_version)+")", (True and "PASS" or "FAIL"))
                            else:
                                passed = False
                                message += ", " +cluster_key+"@"+cluster_name+"@"+host_name+"@"+vm_name+"="+ version+" (Expected: =Greater than vmx-"+str(allvm_version)+")"+"#"+(False and "PASS" or "FAIL")
                                self.reporter.notify_progress(self.reporter.notify_checkLog,cluster_key+"@"+cluster_name+"@"+host_name+"@"+vm_name+"="+ version+" (Expected: =Greater than vmx-"+str(allvm_version)+")", (False and "PASS" or "FAIL"))

                            pass_all= pass_all and passed
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_vm_hardware_version_ailing_with_esxi_version - Exit")
        return pass_all, message,path+".host.vm"

    def get_nutanix_cluster_info(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: get_nutanix_cluster_info - Enter")
        if len(VCChecker.responseHostsJson) == 0 or len(VCChecker.responseClusterJson) == 0:
            ncc_auth_conf_path = os.path.abspath(os.path.dirname(__file__)) + os.path.sep + ".." + os.path.sep +"conf" + os.path.sep + "auth.conf"
            fp = open(ncc_auth_conf_path, 'r')
            ncc_auth_config = json.load(fp)
            fp.close()

            ncc_config = ncc_auth_config["ncc"]
            current_cvm_ip = ncc_config["cvm_ip"]

            restURLHosts = "https://"+current_cvm_ip+":9440/PrismGateway/services/rest/v1/hosts/"
            restURLCluster = "https://"+current_cvm_ip+":9440/PrismGateway/services/rest/v1/cluster/"

            headers = {'content-type': 'application/json'}
            try:
                response_hosts = requests.get(restURLHosts, headers=headers,auth=("admin", "admin"), verify=False)
                responseCluster = requests.get(restURLCluster, headers=headers,auth=("admin", "admin"), verify=False)

                if (response_hosts.status_code != 200) and (responseCluster.status_code != 200):
                    return None

                VCChecker.responseHostsJson = json.loads(response_hosts.text)
                VCChecker.responseClusterJson = json.loads(responseCluster.text)

            except requests.ConnectionError:
                return '' , '' , False
            except:
                return '' , '' , False 
        else:
            pass

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: get_nutanix_cluster_info - Exit")
        return VCChecker.responseHostsJson["entities"] , VCChecker.responseClusterJson["name"] , True    

    @checkgroup("hardware_and_bios_checks", "XD-Execute Disabled",["performance"],"True")
    def check_XD_enabled(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_XD_enabled - Enter")
        path_curr = 'content.rootFolder.childEntity.hostFolder.childEntity.host.hardware.cpuFeature'
        host_map = self.get_vc_property(path_curr)

        message = ""
        passed_all = True

        for key, host_cpuFeatures in host_map.iteritems():
            passed = True

            if host_cpuFeatures == "Not-Configured":
                continue

            for cpuFeature in host_cpuFeatures:
                if cpuFeature.level == -2147483647 :
                    edx = cpuFeature.edx
                    xd_enabled=False
                    # Bit operation
                    # if  edx=0010:1100:0001:0000:0000:1000:0000:0000, to check XD 20th bit should set to 1
                    if list(edx.split(':')[2])[-1] == '1':
                        xd_enabled=True

                    message += ", " +key+"="+str(xd_enabled)+" (Expected: =True)"+"#"+(xd_enabled and "PASS" or "FAIL")
                    self.reporter.notify_progress(self.reporter.notify_checkLog,key+"="+str(xd_enabled)+" (Expected: =True)",(xd_enabled and "PASS" or "FAIL"))
                    passed=xd_enabled
                    continue
            passed_all = passed_all and passed

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_XD_enabled - Exit")
        return passed_all , message, path_curr

    @checkgroup("hardware_and_bios_checks", "VT-Extensions", ["performance"], "3")
    def check_VT_extensions(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_VT_extensions - Enter")
        path_curr = 'content.rootFolder.childEntity.hostFolder.childEntity.host'
        clusters_map = self.get_vc_property(path_curr)

        message = ""
        passed_all = True
        VT_extension_level = False
        for datacenter, host_list in clusters_map.iteritems():
            passed = True
            #print datacenter

            if host_list == "Not-Configured" :
                continue
            elif len(host_list)==0: 
                #condtion to Check if no host found
                continue

            for host in host_list:
                host_ip=host.name
                if self.authconfig['host']!='':
                    if host_ip not in self.authconfig['host']:
                        #print "skipping host "+host_name
                        continue
                flag,esxi_ssh = self.get_esxi_ssh_connection(host_ip)
                if flag == "SSH Connection Failed" or flag == "Authentication Exception":
                    passed = False
                    message += ", " +datacenter+"@"+host_ip+"="+"SSH Connection Failed"+" (Expected: =3)"+"#"+("FAIL")
                    self.reporter.notify_progress(self.reporter.notify_checkLog,datacenter+"."+host_ip+"="+"SSH Connection Failed"+" (Expected: =3)",("FAIL"))
                elif esxi_ssh is not None and esxi_ssh._transport is not None:
                    cmd = "esxcfg-info|grep \"HV Support\""
                    stdin, stdout, stderr =  esxi_ssh.exec_command(cmd)

                    for line in stdout:
                        line = ''.join(e for e in line if e.isalnum())

                        if line.startswith('HVSupport'):
                            level = line[-1:]

                            if level is not None and level == "3":
                                VT_extension_level = True
                                message += ", " +datacenter+"@"+host_ip+"="+level+" (Expected: =3)"+"#"+(VT_extension_level and "PASS" or "FAIL")
                                self.reporter.notify_progress(self.reporter.notify_checkLog,datacenter+"."+host_ip+"="+level+" (Expected: =3)",(VT_extension_level and "PASS" or "FAIL"))
                                passed=VT_extension_level

                            elif level is not None and level != "3":  
                                message += ", " +datacenter+"@"+host_ip+"="+level+" (Expected: =3)"+"#"+(VT_extension_level and "PASS" or "FAIL")
                                self.reporter.notify_progress(self.reporter.notify_checkLog,datacenter+"."+host_ip+"="+level+" (Expected: =3)",(VT_extension_level and "PASS" or "FAIL"))
                                passed=VT_extension_level
                else:
                    passed = False
                    message += ", " +datacenter+"@"+host_ip+" =Cannot Determine"+" (Expected: =3)"+"#"+("FAIL")
                    self.reporter.notify_progress(self.reporter.notify_checkLog,datacenter+"@"+host_ip+" =Cannot Determine"+" (Expected: =3)",("FAIL"))

                VCChecker.esxi_ssh = None
        passed_all = passed_all and passed
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_VT_extensions - Exit")
        return passed_all,message,path_curr

    @checkgroup("hardware_and_bios_checks", "NX-1020 Maximum Cluster Size", ["configurability","supportability"], "Less than 8")
    def check_NX1020_Cluster_Size(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_NX1020_Cluster_Size - Enter")
        entities, cluster, status = self.get_nutanix_cluster_info()
        model_map = {}
        model_count = 0;
        message = ""
        passed_all = True
        if status ==True:
            for entity in entities:
                if entity["blockModel"] == "NX1020":
                    model_map[model_count] = entity["blockModel"]
                    model_count += 1

            if len(model_map) > 8:
                passed = False
                message += ", " +"Nutanix Cluster["+cluster+"] has Cluster_Size ="+str(len(model_map))+" (Expected: =Cluster size less than 8)"+"#"+(passed and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"Nutanix Cluster["+cluster+"] has Cluster_Size ="+str(len(model_map))+" (Expected: =Cluster size less than 8)",(passed and "PASS" or "FAIL"))

            elif len(model_map) == 0:
                passed = True
                message += ", " +"Nutanix Cluster["+cluster+"] has Cluster_Size ="+str(len(model_map))+" (Expected: =Cluster size less than 8)"+"#"+(passed and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"Nutanix Cluster["+cluster+"] has Cluster_Size ="+str(len(model_map))+" (Expected: =Cluster size less than 8)",(passed and "PASS" or "FAIL"))

            else :
                passed=True
                message += ", " +"Nutanix Cluster["+cluster+"] has Cluster_Size ="+str(len(model_map))+" (Expected: =Cluster size less than 8)"+"#"+(passed and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"Nutanix Cluster["+cluster+"] has Cluster_Size ="+str(len(model_map))+" (Expected: =Cluster size less than 8)",(passed and "PASS" or "FAIL"))

        elif status == False:
            passed = False
            message += ", " +"Check Status"+"="+"SSH Connection Failed"+" (Expected: =Cluster size less than 8)"+"#"+("FAIL")
            self.reporter.notify_progress(self.reporter.notify_checkLog,"Check Status"+"="+"SSH Connection Failed"+" (Expected: =Cluster size less than 8)",("FAIL"))

        passed_all = passed_all and passed
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_NX1020_Cluster_Size - Exit")
        return passed_all,message,''    
 
    @checkgroup("hardware_and_bios_checks", "NX-1020 Nodes mixed with Other Nodes", ["configurability","performance","supportability"], "Mixed Nodes Not Present")
    def check_NX1020_Mixed_Nodes_Not_Present(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_NX1020_Mixed_Nodes_Not_Present - Enter")
        entities, cluster, status = self.get_nutanix_cluster_info()
        model_map = {}
        nx1020_model_count = 0;
        other_model_count = 0;
        message = ""
        passed_all = True

        if status == True:
            for entity in entities:
                if entity["blockModel"] == "NX1020":
                    model_map[nx1020_model_count] = entity["blockModel"]
                    nx1020_model_count += 1
                else:
                    other_model_count += 1

            if other_model_count > 0 and nx1020_model_count > 0:
                passed = False
                message += ", " +"On Nutanix Cluster["+cluster+"] Non NX-1020 Node Count ="+str(other_model_count)+" (Expected: =Non NX-1020 Node Count 0)"+"#"+(passed and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"On Nutanix Cluster["+cluster+"] Non NX-1020 Node Count ="+str(other_model_count)+" (Expected: =Non NX-1020 Node Count 0)",(passed and "PASS" or "FAIL"))

            elif other_model_count == 0 and nx1020_model_count > 0:
                passed = True
                message += ", " +"On Nutanix Cluster["+cluster+"] Non NX-1020 Node Count ="+str(other_model_count)+" (Expected: =Non NX-1020 Node Count 0)"+"#"+(passed and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"On Nutanix Cluster["+cluster+"] Non NX-1020 Node Count ="+str(other_model_count)+" (Expected: =Non NX-1020 Node Count 0)",(passed and "PASS" or "FAIL"))

            elif other_model_count > 0 and nx1020_model_count == 0:
                passed = True
                message += ", " +"On Nutanix Cluster["+cluster+"] NX-1020 Node Count ="+str(nx1020_model_count)+" (Expected: =NX-1020 Node Count 0)"+"#"+(passed and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"On Nutanix Cluster["+cluster+"] NX-1020 Node Count ="+str(nx1020_model_count)+" (Expected: =NX-1020 Node Count 0)",(passed and "PASS" or "FAIL"))

        elif status == False:
            passed = False
            message += ", " +"Check Status"+"="+"SSH Connection Failed"+" (Expected: =NX-1020 Node Count 0)"+"#"+("FAIL")
            self.reporter.notify_progress(self.reporter.notify_checkLog,"Check Status"+"="+"SSH Connection Failed"+" (Expected: =NX-1020 Node Count 0)",("FAIL"))

        passed_all = passed_all and passed

        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_NX1020_Mixed_Nodes_Not_Present - Exit")
        return passed_all,message,''    
 
    @checkgroup("hardware_and_bios_checks", "NX-6000 Nodes mixed with NX-2000 Nodes", ["configurability","supportability"], "Mixed Nodes Not Present")
    def check_NX6000_mixed_with_NX2000(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_NX6000_mixed_with_NX2000 - Enter")
        entities, cluster, status = self.get_nutanix_cluster_info()
        model_map = {}
        nx6000_model_count = 0;
        nx2000_model_count = 0;
        message = ""
        passed_all = True

        if status ==True:
            for entity in entities:
                if entity["blockModel"] == "NX6000":
                    model_map[nx6000_model_count] = entity["blockModel"]
                    nx6000_model_count+=1
                elif entity["blockModel"] == "NX2000":
                    model_map[nx2000_model_count] = entity["blockModel"]
                    nx2000_model_count+=1    

            if nx6000_model_count > 0 and nx2000_model_count > 0:
                passed = False
                message += ", " +"Nutanix Cluster["+cluster+"] has Non NX-6000 Node Count ="+str(nx2000_model_count)+" (Expected: =Non NX-6000 Node Count 0)"+"#"+(passed and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"Nutanix Cluster["+cluster+"] has Non NX-6000 Node Count ="+str(nx2000_model_count)+" (Expected: =Non NX-6000 Node Count 0)",(passed and "PASS" or "FAIL"))

            elif nx6000_model_count > 0 and nx2000_model_count == 0:    
                passed = True
                message += ", " +"Nutanix Cluster["+cluster+"] has NX-6000 Node Count ="+str(nx6000_model_count)+" (Expected: =NX-6000 Node Count > 0)"+"#"+(passed and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"Nutanix Cluster["+cluster+"] has Non NX-6000 Node Count ="+str(nx6000_model_count)+" (Expected: =Non NX-6000 Node Count > 0)",(passed and "PASS" or "FAIL"))

            elif nx6000_model_count == 0 and nx2000_model_count == 0:
                passed = True
                message += ", " +"Nutanix Cluster["+cluster+"] has NX-6000,NX-2000 Node Count =0 (Expected: =NX-6000,NX-2000 Node Count 0)"+"#"+(passed and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"Nutanix Cluster["+cluster+"] has NX-6000,NX-2000 Node Count =0 (Expected: =NX-6000,NX-2000 Node Count 0)",(passed and "PASS" or "FAIL"))

        elif status == False:
            passed = False
            message += ", " +"Check Status"+"="+"SSH Connection Failed"+" (Expected: =NX-6000,NX-2000 Node Count 0)"+"#"+("FAIL")
            self.reporter.notify_progress(self.reporter.notify_checkLog,"Check Status"+"="+"SSH Connection Failed"+" (Expected: =NX-6000,NX-2000 Node Count 0)",("FAIL"))

        passed_all = passed_all and passed
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_NX6000_mixed_with_NX2000 - Exit")
        return passed_all,message,''   

    @checkgroup("hardware_and_bios_checks", "NX-1050 Maximum Cluster Size", ["configurability","supportability","performance"], "Less than 8")
    def check_NX1050_Cluster_Size(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_NX1050_Cluster_Size - Enter")
        entities,cluster,status = self.get_nutanix_cluster_info()
        model_map = {}
        model_count = 0
        message = ""
        passed_all = True
        speed_flag_map = {}

        if status ==True:
            for entity in entities:
                if entity["blockModel"] == "NX1050":
                    model_map[model_count] = entity["blockModel"]
                    model_count += 1
                    host_ip = entity["hypervisorAddress"]
                    check_host_ip = str(host_ip).replace(".", "*")
                    speed_flag = self.check_vmnic_connection(check_host_ip)
                speed_flag_map[model_count] = speed_flag

            if len(model_map) <= 5:
                passed = True
                message += ", " +"Nutanix Cluster["+cluster+"] has Cluster_Size ="+str(len(model_map))+" (Expected: =Cluster size less than 8)"+"#"+(passed and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"Nutanix Cluster["+cluster+"] has Cluster_Size ="+str(len(model_map))+" (Expected: =Cluster size less than 8)",(passed and "PASS" or "FAIL"))

            elif len(model_map) > 5 and True in speed_flag_map.values():
                passed=False
                message += ", " +"Nutanix Cluster["+cluster+"] has Cluster_Size ="+str(len(model_map))+" (Expected: =Cluster size less than 8)"+"#"+(passed and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"Nutanix Cluster["+cluster+"] has Cluster_Size ="+str(len(model_map))+" (Expected: =Cluster size less than 8)",(passed and "PASS" or "FAIL"))

            else :
                passed=True
                message += ", " +"Nutanix Cluster["+cluster+"] has Cluster_Size ="+str(len(model_map))+" (Expected: =Cluster size less than 8)"+"#"+(passed and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"Nutanix Cluster["+cluster+"] has Cluster_Size ="+str(len(model_map))+" (Expected: =Cluster size less than 8)",(passed and "PASS" or "FAIL"))

        elif status == False:
            passed = False
            message += ", " +"Check Status"+"="+"SSH Connection Failed"+" (Expected: =Cluster size less than 8)"+"#"+("FAIL")
            self.reporter.notify_progress(self.reporter.notify_checkLog,"Check Status"+"="+"SSH Connection Failed"+" (Expected: =Cluster size less than 8)",("FAIL"))

        passed_all = passed_all and passed 
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_NX1050_Cluster_Size - Exit")
        return passed_all,message,''   

    @checkgroup("hardware_and_bios_checks", "NX-1050 Nodes mixed with Other Nodes", ["configurability","supportability"], "Mixed Nodes Not Present")
    def check_NX1050_mixed_with_other_nodes(self):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_NX1050_mixed_with_other_nodes - Enter")
        entities, cluster, status = self.get_nutanix_cluster_info()
        model_map = {}
        nx1050_model_count = 0;
        other_model_count = 0;
        message = ""
        passed_all = True
        speed_flag_map = {}

        if status ==True:
            for entity in entities:
                if entity["blockModel"] == "NX1050":
                    model_map[nx1050_model_count] = entity["blockModel"]
                    nx1050_model_count += 1
                else: 
                    other_model_count += 1
                host_ip = entity["hypervisorAddress"]
                check_host_ip = str(host_ip).replace(".", "*")
                speed_flag = self.check_vmnic_connection(check_host_ip)
            speed_flag_map[nx1050_model_count] = speed_flag

            if nx1050_model_count > 0 and other_model_count > 0 and True in speed_flag_map.values():
                passed=False
                message += ", " +"Nutanix Cluster["+cluster+"] has Non NX-1050 Node Count ="+str(other_model_count)+" (Expected: =Non NX-1050 Node Count 0)"+"#"+(passed and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"Nutanix Cluster["+cluster+"] has Non NX-1050 Node Count ="+str(other_model_count)+" (Expected: =Non NX-1050 Node Count 0)",(passed and "PASS" or "FAIL"))

            elif nx1050_model_count > 0 and other_model_count == 0:
                passed=True
                message += ", " +"Nutanix Cluster["+cluster+"] has Non NX-1050 Node Count ="+str(other_model_count)+" (Expected: =Non NX-1050 Node Count 0)"+"#"+(passed and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"Nutanix Cluster["+cluster+"] has Non NX-1050 Node Count ="+str(other_model_count)+" (Expected: =Non NX-1050 Node Count 0)",(passed and "PASS" or "FAIL"))

            elif nx1050_model_count == 0 and other_model_count == 0:
                passed=False
                message += ", " +"Nutanix Cluster["+cluster+"] has NX-1050 Node Count =0 (Expected: =NX-1050 Node Count > 0)"+"#"+(passed and "PASS" or "FAIL")
                self.reporter.notify_progress(self.reporter.notify_checkLog,"Nutanix Cluster["+cluster+"] has NX-1050 Node Count =0 (Expected: =NX-1050 Node Count > 0)",(passed and "PASS" or "FAIL"))

        elif status == False:
            passed = False
            message += ", " +"Check Status"+"="+"SSH Connection Failed"+" (Expected: =Non NX-1050 Node Count 0)"+"#"+("FAIL")
            self.reporter.notify_progress(self.reporter.notify_checkLog,"Check Status"+"="+"SSH Connection Failed"+" (Expected: =Non NX-1050 Node Count 0)",("FAIL"))

        passed_all = passed_all and passed 
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_NX1050_mixed_with_other_nodes - Exit")
        return passed_all,message,''

    def check_vmnic_connection(self,check_host_ip):
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_vmnic_connection - Enter")
        path='content.rootFolder.childEntity.hostFolder.childEntity.host[name='+check_host_ip+'].configManager.networkSystem.networkConfig.pnic'
        host_networks = self.get_vc_property(path)


        for key, network in host_networks.iteritems():
            speed_flag = False
            if network == "Not-Configured":
                continue

            for physical_nic in network:
                link_speed = physical_nic.spec.linkSpeed

                if link_speed is not None:
                    speed = link_speed.speedMb

                    if speed == 'None':
                        speed_flag = False
                    elif speed == 10000:   
                        speed_flag = False
                    elif speed == 1000:    
                        speed_flag = True
                        continue
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: check_vmnic_connection - Exit")                                                                                                                                              
        return speed_flag