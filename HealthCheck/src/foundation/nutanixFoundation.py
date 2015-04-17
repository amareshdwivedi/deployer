'''
Created on Nov 25, 2014

@author: GaneshM
'''
import requests
import json,os,sys
from lepl.apps.rfc3696 import HttpUrl
from utility import Logger

loggerObj = Logger()

class FoundationProvision:
    def __init__(self,foundationDetails):
        self.restInput = foundationDetails['restInput']
        self.provision_url = "http://"+foundationDetails['server']+":8000/foundation/image_nodes"
        self.progress_url  = "http://"+foundationDetails['server']+":8000/foundation/progress"        
        self.validate_urls()
        

    def validate_urls(self):
        validator = HttpUrl()
        if not validator(self.provision_url):
            print "Not a valid URL -",self.provision_url
            sys.exit(1)
        if not validator(self.progress_url):
            print "Not a valid URL -",self.progress_url
            sys.exit(1)
        #loggerObj.LogMessage("info","Foundation urls successfully validated.")

    def init_foundation(self):
        headers = {'content-type': 'application/json'}
        response = requests.post(self.provision_url, data=json.dumps(self.restInput), headers=headers, verify=False)
        
        response_code = response.status_code
        if(response_code == 200):
            loggerObj.LogMessage("info","Foundation is successfully Initialized.")
            return None
        elif(response_code == 404):
            print "Foundation Server not reachable."
            loggerObj.LogMessage("error","Foundation Server not reachable.")
            sys.exit(1)
        else:
            print "Error occurred."
            loggerObj.LogMessage("error","Failed to initialize foundation.")
            sys.exit(1)

    def get_progress(self):
    	headers = {'content-type': 'application/json'}
        response = requests.get(self.progress_url, headers=headers, verify=False)

        if response.status_code == 200:
           	response_text = json.loads(response.text)
        	return response_text["aggregate_percent_complete"]
        else:
        	return "-1"
        '''
        t = response.text
        print "status :",t.split(',')[len(t.split(','))-1]
        '''
