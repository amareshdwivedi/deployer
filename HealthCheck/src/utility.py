import re
import logging
import binascii
from Crypto.Cipher import ARC4
import json
import os

glob_stopExecution = False
class Validate:
    
    @staticmethod
    def valid_ip(address):
        ip_pattern = "^([01]?\\d\\d?|2[0-4]\\d|25[0-5])\\.([01]?\\d\\d?|2[0-4]\\d|25[0-5])\\.([01]?\\d\\d?|2[0-4]\\d|25[0-5])\\.([01]?\\d\\d?|2[0-4]\\d|25[0-5])$"
        pat=re.compile(ip_pattern)
        is_valid_ip = pat.match(str(address))
        if is_valid_ip : 
            return True
        return False

class Security :
    @staticmethod
    def encrypt(data):
        arc=ARC4.new('01234567')
        cipher_text=binascii.hexlify(arc.encrypt(data))
        return cipher_text
    
    @staticmethod
    def decrypt(cipher_text):
        arc = ARC4.new('01234567')
        data=arc.decrypt(binascii.unhexlify(cipher_text))
        return data

class Logger:
    def __init__(self,cur_dir=None):
        #import traceback
        #traceback.print_stack()
        self.logger = logging.getLogger('hcd')
        if not self.logger.handlers:
            LogConfigFile = os.path.abspath(os.path.dirname(__file__))+os.path.sep +"conf" + os.path.sep + "log.conf"
            fp = open(LogConfigFile, 'r')
            logConfigParams = json.load(fp)
            fp.close()

            if cur_dir is None:
                self.hdlr = logging.FileHandler(os.getcwd() + os.path.sep + str(logConfigParams['file']))
            else:
                self.hdlr = logging.FileHandler(cur_dir + os.path.sep + str(logConfigParams['file']))
            
            self.formatter = logging.Formatter(str(logConfigParams['formatter']))
            self.hdlr.setFormatter(self.formatter)
            self.logger.addHandler(self.hdlr) 
            if logConfigParams['level'] == "INFO":
                self.logger.setLevel(logging.INFO)
            elif logConfigParams['level'] == "WARNING":
                self.logger.setLevel(logging.WARNING)
            elif logConfigParams['level'] == "ERROR":
                self.logger.setLevel(logging.ERROR)
            elif logConfigParams['level'] == "CRITICAL":
                self.logger.setLevel(logging.CRITICAL)
            elif logConfigParams['level'] == "DEBUG":
                self.logger.setLevel(logging.DEBUG)
            else:
                self.logger.setLevel(logging.NOTSET)
            
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Singleton, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def LogMessage(self,msgType, msgText):
        if msgType.lower() == "info":
        	self.logger.info(msgText)

        elif msgType.lower() == "warning":
        	self.logger.warning(msgText)

        elif msgType.lower() == "error":
        	self.logger.error(msgText)

        elif msgType.lower() == "critical":
        	self.logger.critical(msgText)

        else:
        	self.logger.log(msgText)

