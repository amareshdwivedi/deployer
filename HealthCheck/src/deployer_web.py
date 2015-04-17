'''
Created on Dec 29, 2014

@author: RohitD
'''
import json
import os
import sys
import time
from foundation.nutanixFoundation import FoundationProvision
from foundation.prismProvision import PrismActions
from serverConfiguration.vCenterServer import VCenterServerConf
from utility import Logger

loggerObj = Logger()
class initiate_deployment:
        """
            This class would be providing an interface 
            where user can initiate foundation ,prism and vcenter
            .We can also monitor the foundation progress by using this
            class api.
        
        """

        def __init__(self,json_input):

            #self.deployment_type = deployment_type
            self.inputData = json_input
            self.progressStatus = None
            self.fProcess = FoundationProvision(self.inputData['foundation'])
            


        def initiate_foundation(self):
            """ This function would be initiating foundation installation process"""

            #fProcess = FoundationProvision(self.inputData['foundation'])
            self.fProcess.init_foundation()
            print "Foundation is successfully initialised."
            return True

        def initiate_cluster_config(self):

            prismObj = PrismActions(self.inputData['prismDetails'])
            status = prismObj.create_storage_pool()
            print status
            status = prismObj.create_container()
            print status
            
            return status 

        def initiate_vcenter_server_config(self):
            
            vServer = VCenterServerConf(self.inputData['vCenterConf'])
            vServer.do_configuration()
            print "vCenter Server configuration Successfully Done."
            return True

        def check_foundation_progress(self):
            progPercent = self.fProcess.get_progress()
            progressStatus = progPercent
            return  progressStatus

