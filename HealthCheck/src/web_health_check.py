import sys
if (len(sys.argv) > 2):
    cur_dir=" ".join(sys.argv[2:])
else:
    cur_dir = None

from utility import Logger
loggerObj = Logger(cur_dir)

import web
import requests
from web import form
from checkers.ncc_checker import NCCChecker
from checkers.vc_checker import VCChecker
from checkers.view_checker import HorizonViewChecker
from checkers.base_checker import CheckerBase
from reporters import DefaultConsoleReporter
from report_generator import PDFReportGenerator,CSVReportGenerator
from prettytable import PrettyTable
import json
from operator import itemgetter
import csv, time
import os
import httplib
import paramiko
import socket
from utility import Security
import warnings
from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect
from requests.exceptions import ConnectionError
import reportGenerator
import utility 
from deployer_web import initiate_deployment
import api

file_name = os.path.basename(__file__)
    
urls = (

    '/v1/deployer/customers/$','api.customers' ,       
    '/v1/deployer/customers/(\d+)/$','api.customers',   
    '/v1/deployer/customers/(\d+)/tasks/$','api.customertasks',
    '/v1/deployer/customers/(\d+)/tasks/(\d+)/$','api.customertasks',   
    '/v1/deployer/utils/nodedetails/$','api.nodedetails',
    '/v1/deployer/utils/foundationprogress/$','api.foundationprogress',
    '/v1/deployer/action/$','api.customeraction',
    '/v1/deployer/customers/(\d+)/tasks/(\d+)/status/$','api.deploymentstatus',
    '/config', 'config',
    '/connect', 'connect',
    '/run', 'runChecks',
    '/refresh', 'refresh',
    '/stopExecute', 'stopExecute',
    '/reports/(\d+)/','api.customerReports',
    '/download/','api.downloadReports',
    '/', 'index',
    '/GeneratePdf/','reportGenerator.GeneratePdf',
    '/home/', 'home',
    '/isoImages/', 'api.isoImages',
    '/prevTask/','api.customerPrevTask'
    )

app = web.application(urls, globals())
#web.header('Content-Type', 'applicaton/json')
#render = web.template.render('templates/')
render = web.template.render('templates/')

class home:
    def __init__(self):
        self.checkers = {}
        self.callback_name = ''
        for checker_class in CheckerBase.__subclasses__():
            checker = checker_class()
            self.checkers[checker.get_name()] = checker
        
        loggerObj.LogMessage("info","Available Checkers :"+str(self.checkers.keys()))
        for checker in self.checkers.keys():
            conf_path = os.path.abspath(os.path.dirname(__file__))+os.path.sep\
             +"conf"
            loggerObj.LogMessage("info",file_name + " :: Checker configration path - " + conf_path)
             
            checker_conf_file = conf_path + os.path.sep + checker + ".conf" 
            file_ptr = open(checker_conf_file, 'r')
            checker_config = json.load(file_ptr)
            file_ptr.close()

            knowledge_file = conf_path + os.path.sep + "knowledge_base.json" 
            file_ptr = open(knowledge_file, 'r')
            knowledge_config = json.load(file_ptr)
            file_ptr.close()

            checker_module = self.checkers[checker]
            self.reporter = DefaultConsoleReporter(checker)
            checker_module.configure(checker_config, knowledge_config, self.reporter)
            loggerObj.LogMessage("info",file_name + " :: Configured checker "+checker)

    def GET(self):
        return render.home(self.checkers)
    
    
class index:
    def __init__(self):
        self.checkers = {}
        self.callback_name = ''
        for checker_class in CheckerBase.__subclasses__():
            checker = checker_class()
            self.checkers[checker.get_name()] = checker
        
        for checker in self.checkers.keys():
            conf_path = os.path.abspath(os.path.dirname(__file__))+os.path.sep\
             +"conf"
            loggerObj.LogMessage("info",file_name + " :: Checker configration path - " + conf_path)
             
            checker_conf_file = conf_path + os.path.sep + checker + ".conf" 
            file_ptr = open(checker_conf_file, 'r')
            checker_config = json.load(file_ptr)
            file_ptr.close()

            knowledge_file = conf_path + os.path.sep + "knowledge_base.json" 
            file_ptr = open(knowledge_file, 'r')
            knowledge_config = json.load(file_ptr)
            file_ptr.close()

            checker_module = self.checkers[checker]
            self.reporter = DefaultConsoleReporter(checker)
            checker_module.configure(checker_config, knowledge_config, self.reporter)
            loggerObj.LogMessage("info",file_name + " :: Configured checker "+checker)

    def GET(self):
        return render.index(self.checkers)
    
class config:
    def __init__(self):
        pass

    def POST(self):
        data = web.input()
        if data['checker'] == "vc":
            conf_data = { "vc_port": data['vCenter Server Port'], 
                          "vc_user": data['vCenter Server Username'], 
                          "vc_ip": data['vCenter Server IP'], 
                          "cluster": data['Clusters(Comma Seperated List)'], 
                          "host": data['Hosts(Comma Seperated List)'],  
                          "vc_pwd": Security.encrypt(data['vCenter Server Password'])
                        }
            CheckerBase.save_auth_into_auth_config("vc",conf_data)
            loggerObj.LogMessage("info",file_name + " :: Configured auth.conf for vc")
            status = {"Configuration": "Success"}
            return json.dumps(status)

        if data['checker'] == "ncc":
            conf_data = { "cvm_ip": data['CVM IP'], 
                          "cvm_pwd": Security.encrypt(data['CVM SSH Host Password']), 
                          "cvm_user": data['CVM SSH Host Username']
                          }

            CheckerBase.save_auth_into_auth_config("ncc",conf_data)
            loggerObj.LogMessage("info",file_name + " :: Configured auth.conf for ncc")            
            status = {"Configuration": "Success"}        
            return json.dumps(status)
        
        if data['checker'] == "view":
            conf_data = { "view_ip": data['Server'], 
                          "view_pwd": Security.encrypt(data['Password']), 
                          "view_user": data['User'],
                          "view_vc_ip": data['VC Server'],
                          "view_vc_user": data['VC User'],
                          "view_vc_pwd": Security.encrypt(data['VC Password']),
                          "view_vc_port": data['VC Port'],
                          }

            CheckerBase.save_auth_into_auth_config("view",conf_data)
            loggerObj.LogMessage("info",file_name + " :: Configured auth.conf for view")            
            status = {"Configuration": "Success"}        
            return json.dumps(status)           

class connect:
    def __init__(self):
        self.checkers = {}
        self.callback_name = ''
        for checker_class in CheckerBase.__subclasses__():
            checker = checker_class()
            self.checkers[checker.get_name()] = checker

    def POST(self):
        data = web.input()
        
        status = {}
        if data['checker'] == "vc":
            ret , msg = self.checkers['vc'].check_connectivity(data['vCenter Server IP'],data['vCenter Server Username'],Security.encrypt(data['vCenter Server Password']),data['vCenter Server Port'],"web")
            if ret:
                loggerObj.LogMessage("info",file_name + " :: vc connection successfull")                            
                status['Connection'] = "Connection Success"
            else:
                status['Connection'] = msg
            return json.dumps(status)
    
        if data['checker'] == "ncc":
            ret , msg = self.checkers['ncc'].check_connectivity(data['CVM IP'],data['CVM SSH Host Username'],Security.encrypt(data['CVM SSH Host Password']),"web")
            if ret:
                loggerObj.LogMessage("info",file_name + " :: ncc connection successfull")                            
                status['Connection'] = "Connection Success"
            else:
                status['Connection'] = msg
            return json.dumps(status)
         
        if data['checker'] == "view":
            ret , msg = self.checkers['view'].check_connectivity(data['Server'],data['User'],Security.encrypt(data['Password']))
            vc_ret , vc_msg = self.checkers['view'].check_view_vc_connectivity(data['VC Server'],data['VC User'],Security.encrypt(data['VC Password']),data['VC Port'],"web")
            if ret and vc_ret:
                loggerObj.LogMessage("info",file_name + " :: view connection successfull")                            
                status['Connection'] = "Connection Success"
            else:
                if not ret:
                    status['Connection'] = msg
                else:
                    status['Connection'] = vc_msg

            return json.dumps(status)        
        
    
class runChecks:
    def __init__(self):
        self.checkers = {}
        self.callback_name = ''
        for checker_class in CheckerBase.__subclasses__():
            checker = checker_class()
            self.checkers[checker.get_name()] = checker
        
        for checker in self.checkers.keys():
            conf_path = os.path.abspath(os.path.dirname(__file__))+os.path.sep\
             +"conf"
            loggerObj.LogMessage("info",file_name + " :: Checker configration path - " + conf_path)

            checker_conf_file = conf_path + os.path.sep + checker + ".conf" 
            file_ptr = open(checker_conf_file, 'r')
            checker_config = json.load(file_ptr)
            file_ptr.close()

            knowledge_file = conf_path + os.path.sep + "knowledge_base.json" 
            file_ptr = open(knowledge_file, 'r')
            knowledge_config = json.load(file_ptr)
            file_ptr.close()

            checker_module = self.checkers[checker]
            self.reporter = DefaultConsoleReporter(checker)
            checker_module.configure(checker_config, knowledge_config, self.reporter)
            loggerObj.LogMessage("info",file_name + " :: Configured checker "+checker)


    def POST(self):
        data = web.input()
        results = {}
        run_logs = {}
        
        checkers_list, group = [], []
        if data['category'] == "Run All":
            checkers_list = self.checkers.keys()
            for item in checkers_list:
                run_logs[item] = {'checks': []}

        if data['category'] == "ncc":
            checkers_list = ['ncc']
            run_logs['ncc'] = {'checks': []}
            if data['group'] == "Run All":
                group.append("run_all")
            else:
                group.append(data['group'] + " " + "run_all")
                
        if data['category'] == "vc":
            checkers_list = ['vc']
            run_logs['vc'] = {'checks': []}
            if data['group'] == "Run All":
                group.append("run_all")
            else:
                group.append(data['group'])
                
        if data['category'] == "view":
            checkers_list = ['view']
            run_logs['view'] = {'checks': []}
            if data['group'] == "Run All":
                group.append("run_all")
            else:
                group.append(data['group'])          
        
        with open("display_json.json", "w") as myfile:
            json.dump(run_logs, myfile)
        taskId = None
        try:
            customerId = data['customerId']
            taskId = api.model.add_task(customerId,None,"HealthCheck")
        except:
            pass
        
        for checker in checkers_list:
            checker_module = self.checkers[checker]
            if checker == "vc":
                loggerObj.LogMessage("info",file_name + " :: Executing vc checks")
                result, status = checker_module.execute(group,"web")
            elif checker == 'ncc':
                loggerObj.LogMessage("info",file_name + " :: Executing ncc checks")
                result, status = checker_module.execute(group,"web")
            elif checker == 'view':
                loggerObj.LogMessage("info",file_name + " :: Executing view checks")
                result, status = checker_module.execute(group,"web")    
            else: 
                loggerObj.LogMessage("info",file_name + " :: Executing run_all")       
                result, status = checker_module.execute(["run_all"],"web")
            
            results[checker] = result.to_dict()
        
        utility.glob_stopExecution = False
        
        if status in ['Stopped','Complete']:
            #Generate Json Reports 
            outfile = open(os.getcwd() + os.path.sep +"reports"+os.path.sep+"results.json", 'w')
            json.dump(results, outfile, indent=2)
            outfile.close()
            loggerObj.LogMessage("info",file_name + " :: Results JSON generated successfully")
                        
            #Generate CSV Reports
            CSVReportGenerator(results,cur_dir)
            loggerObj.LogMessage("info",file_name + " :: CSV report generated successfully")
            
            
            #Generate PDF Report based on results. 
            reportFileName = PDFReportGenerator(results,cur_dir)
            loggerObj.LogMessage("info",file_name + " :: PDF report generated successfully")
        else:
            loggerObj.LogMessage("error", "Exception Caused:: "+status)
            return status

        if taskId is not None:
            taskId = api.model.update_task(int(taskId), "Completed",reportFileName)
        
        return "Execution "+status
        
class refresh:
    def __init__(self):
        pass

    def GET(self):
        try:
            f = open("display_json.json", 'r')
            
            allJson = json.load(f)
            chTotal = chPass = chFail = 0

            if "vc" in allJson:
                checkJson = allJson["vc"]
            if "ncc" in allJson:
                checkJson = allJson["ncc"]
            if "view" in allJson:
                checkJson = allJson["view"]

            for item in checkJson["checks"]:
                chTotal += 1
                if item["Status"].upper() == "PASS":
                    chPass += 1
                else:
                    chFail +=1
            
            allJson["Total"] = chTotal
            allJson["PASS"] = chPass
            allJson["FAIL"] = chFail
            allJson["Percent"] = round(chPass*1.0/chTotal * 100,2)
            return json.dumps(allJson)

        except:
            return True
        
class stopExecute:
    def __init__(self):
        pass

    def GET(self):
        utility.glob_stopExecution = True


if __name__ == "__main__":
    web.internalerror = web.debugerror
    app.run()
