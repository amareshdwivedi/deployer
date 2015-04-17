'''
Created on Dec 18, 2014

@author: GaneshM
Description : The script performs the DPaaS operations.
              This script sends the REST reqeust to server & gets the response. 
              for input request Json is required as input which comprises of fields namely restURL, Authentication & Value (Post request data).
'''
import os, sys, time
import json, warnings, requests

def main():  
    
    options = sys.argv[1:]
    
    if len(options) == 1:
        try :
            
            inputData = json.loads(options[0])
        except:
            print "Invalid Json Syntax."
            sys.exit(1)
    else:
        print "Invalid number of input arguments."
        sys.exit(1)
    
    warnings.simplefilter('ignore')
    headers = {'content-type': 'application/json'}
    
    try:
    	restURL,userName,passwd,jsonStr = inputData['restURL'], inputData['authentication']['username'], inputData['authentication']['password'], inputData['value']
    except KeyError:
    	print 'Key not found in input JSON.' 
    	sys.exit(1)
    except:
    	print "Unknown Error."
    	sys.exit(1)	   	
       
    try:
        if jsonStr != '':
            response = requests.post(restURL, headers=headers, auth=(userName, passwd), data=json.dumps(jsonStr), verify=False)
        else:
            response = requests.get(restURL, headers=headers, auth=(userName, passwd), verify=False)
            
        if response.status_code == 200:
            print response.text
            
            
        elif(response_code == 401):
            print "Incorrect Credentials"
        
        elif(response_code == 400):
            print "Unauthorized user"
        
        elif(response_code == 404):
            print "Page Not Found"
        
        else:
            print "Unknown Error"
        
    except requests.ConnectionError, e:
        print 'A connection attempt failed because the Prism API Server did not properly responded' 
    except :
        print "Unexpected error:", sys.exc_info()[0]

    sys.exit(1)
    
if __name__ == "__main__":
    main()
    
