__author__ = 'subashatreya'

import abc
import json
import os
from reporters import CheckerResult,ViewCheckerResult
from utility import Logger

loggerObj = Logger()

file_name = os.path.basename(__file__)

def check(func):
    def wrapper(*args, **kwargs):
        args[0].reporter.notify_progress("Running " + func.__name__)
        result = func(*args, **kwargs)

        checker_result = CheckerResult(func.__name__, result[0], result[1])
        args[0].reporter.notify_progress("Completed " + func.__name__ + " ....... " + str(result[0]))
        args[0].result.add_check_result(checker_result)
    return wrapper

class CheckerBase:

    __metaclass__ = abc.ABCMeta

    def __init__(self, name):
        self.config = {}
        self.authconfig={}
        self.authconfig = self.get_auth_config(name)
        self.reporter = None
        self.checks=[]
        self.result = CheckerResult(name)
        loggerObj.LogMessage("info",file_name + " :: Initialized Checker "+name)
        self.realtime_results = {}

    @abc.abstractmethod
    def get_name(self):
        return

    @abc.abstractmethod
    def get_desc(self):
        return

    @abc.abstractmethod
    def configure(self, config, knowledge_pool, reporter):
        return

    @abc.abstractmethod
    def execute(self, args):
        return
    
    @abc.abstractmethod
    def usage(self):
        return
       
    @abc.abstractmethod
    def setup(self):
        return

    @staticmethod
    def validate_config(config, prop):
        if not prop in config:
            raise RuntimeError(prop + " not in config")
    
    
    def get_auth_config(self,checker):
        auth={}
        try:           
            auth_path=os.path.join(os.path.abspath(os.path.dirname(__file__))+os.path.sep+".."+os.path.sep+"conf"+os.path.sep+"auth.conf")
            fp = open(auth_path,"r")
            authconfig = json.load(fp)
            fp.close()
            auth=authconfig[checker]
            loggerObj.LogMessage("info",file_name + " :: Successfully initialized auth.conf")
        except ValueError as e:
            print checker+ " not configured"
            loggerObj.LogMessage("error",file_name + " :: Failed to initialize auth.conf," + e.message)
            self.setup()
        except Exception as e:
            print checker+ " not configured"
            loggerObj.LogMessage("error",file_name + " :: Failed to initialize auth.conf," + e.message)
            self.setup()
        return auth
 
    @staticmethod
    def save_auth_into_auth_config(checker_name, data):
        authconfig={}
        try:
            auth_path=os.path.join(os.path.abspath(os.path.dirname(__file__))+os.path.sep+".."+os.path.sep+"conf"+os.path.sep+"auth.conf")
            fp = open(auth_path,"r")
            authconfig = json.load(fp)
            fp.close()
            
        except ValueError as e:
            loggerObj.LogMessage("error",file_name + " :: Failed to update auth.conf," + e)
            
        authconfig[checker_name]=data
        auth_path=os.path.join(os.path.abspath(os.path.dirname(__file__))+os.path.sep+".."+os.path.sep+"conf"+os.path.sep+"auth.conf")
        fp = open(auth_path,"w")
        json.dump(authconfig, fp, indent=2)
        fp.close()
        loggerObj.LogMessage("info",file_name + " :: Successfully updated auth.conf")