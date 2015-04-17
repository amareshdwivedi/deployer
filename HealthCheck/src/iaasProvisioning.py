'''
Created on Nov 29, 2014

@author: GaneshM
'''
import json
import os
import sys
import time
from foundation.nutanixFoundation import FoundationProvision
from foundation.prismProvision import PrismActions
from serverConfiguration.vCenterServer import VCenterServerConf
from prettytable import PrettyTable

def usage():
    x = PrettyTable(["Option", "Description"])
    x.align["Option"] = "l"
    x.align["Description"] = "l"
    x.padding_width = 1 
    x.add_row(["foundation", "Perform foundation based on the input parameters"])
    x.add_row(["cluster_config", "Create Storage pool and Container for the cluster"])
    x.add_row(["vcenter_server_config", "Peform Server Configuration"])
    x.add_row(["run_all", "Runs all health checks"])
    print str(x)
    sys.exit(1)

def console_msg(message=None):
       print "\n"+message+"\n"+"+"+"-"*100+"+"

def main():   
    options = sys.argv[1:]
    #print "Options :",options
    if len(options) == 0:
        usage()
   
    
    availOptions = ['foundation','cluster_config','vcenter_server_config','run_all']
    '''
    for item in options:
        if item not in availOptions:
            usage()
    '''
    if (options[0] not in availOptions) and (options[0] != "foundationProgress"):
        usage()

    if options[0] == "run_all":
        options = availOptions
    
    if len(options) > 2:
        usage()
    elif len(options) == 2:
        try :
            #print "Arguement Json is :",options[1]
            inputData = json.loads(options[1])
        except:
            print "Invalid Input"
            sys.exit(1)
    else:
        confFile = os.path.abspath(os.path.dirname(__file__))+os.path.sep +"conf" + os.path.sep + "input.json"
        fp = open(confFile,"r")
        inputData = json.load(fp)
        
        print "Configuration File:",confFile
        print "Did you configured all the necessary Parameters; If not exit (n), update input file & then continue(y)."
        choice = raw_input('Do You want to Continue(y/n) ?')
        if choice[0].lower() == 'n':
            sys.exit(0)
        if choice[0].lower() != 'y':
            print " Invalid Choice"
            sys.exit(0)

    if 'foundation' in options:
        #Foundation Process
        fProcess = FoundationProvision(inputData['foundation'])
        fProcess.init_foundation()
        console_msg("Foundation is successfully initialised.")
        print "-- Please be patient.  This could take 30-60 minutes --"

        if len(options) != 2:
            while True:
                progPercent = fProcess.get_progress()
                num = int(progPercent)

                if num == -1:
                    console_msg("Error Occurred !")
                    sys.exit(1)

                sys.stdout.write('\r')
                sys.stdout.write("[ "+"#"*num+"."*(100-num)+" ] %s%%"%(num))
                time.sleep(1)
                
                if num == 100:
                    break
            time.sleep(20)
            print "\n"
            console_msg("Fondation Process Complete.")
            
    if "foundationProgress" in options:
        fProcess = FoundationProvision(inputData['foundation'])
        progPercent = fProcess.get_progress()
        print progPercent

    if "cluster_config"    in options:
        #Prism Configuration
        console_msg("Cluster configuration started using Prism API..")
        prismObj = PrismActions(inputData['prismDetails'])
        status = prismObj.create_storage_pool()
        console_msg(status)

        status = prismObj.create_container()
        console_msg(status)
        
    if "vcenter_server_config" in options:
        #vCenterServer Configuration
        print "inside vceserv config"
        console_msg('VCenter Server Configuration started ..')
        vServer = VCenterServerConf(inputData['vCenterConf'])
        vServer.do_configuration()
        console_msg("vCenter Server configuration Successfully Done.")
        
    sys.exit(0)
    
if __name__ == "__main__":
    main()
    
