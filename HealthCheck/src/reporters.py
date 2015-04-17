from exceptions import AttributeError
__author__ = 'subashatreya'
from prettytable import PrettyTable
from colorama import Fore, Back, Style
from colorama import init
init()

MSG_WIDTH = 121
class CheckerResult:
    def __init__(self, name, authconfig=None, passed=None, message=None, category=None, path=None, expected_result=None, help_content=None):
        self.name = name
        self.passed = passed
        if str(self.passed) in ("True","False"):
            self.passed = passed and "PASS" or "FAIL"
        self.message = message
        self.category = category
        if authconfig is not None:
            if self.name == "vc":
                self.ip = authconfig['vc_ip']
                self.user = authconfig['vc_user']
            elif self.name == "ncc":
                self.ip = authconfig['cvm_ip']
                self.user = authconfig['cvm_user']
            elif self.name == "view":
                self.ip = authconfig['view_ip']
                self.user = authconfig['view_user']    
                
        self.steps = []
        self.path = path
        self.expected_result = expected_result
        self.help_content = help_content

    def add_check_result(self, step):
        self.steps.append(step)

    def set_status(self, status):
        self.status = status
    
    def set_message(self, message):
        self.message = message
        
    def set_severity(self, severity):
        self.severity = severity
        
    def prop_dict(self):
        props  = []
        all_prop = [ x for x in self.message.split(', ') if x != '']
        for xprop in all_prop:
            xprop,xstatus = xprop.split("#")
            firstChildEntity = True
            datacenter = cluster = entity = host = ''           
            
            is_hosname_added=False
            for xzip in zip(self.path.split('.'),xprop.split('=')[0].split('@')[1:]):
                if xzip[0] == "childEntity":
                    if firstChildEntity:
                        datacenter = xzip[1]
                        firstChildEntity = False
                    else:
                        cluster = xzip[1]
                if xzip[1] != "NoName":
                    entity = xzip[1].split('[')[0]

                if xzip[0] == "host":
                    if is_hosname_added == False: #check if host Name is added
                        is_hosname_added=True
                        host = xzip[1]
                        
            xprop = xprop.replace('NoName.','').replace('NoName','')    
            props.append({"Message":xprop,"Status":xstatus,"Datacenter":datacenter,"Cluster":cluster,"Host":host, "Entity":entity})
        return props

    def to_dict(self):
        if self.message is None:
            dict_obj = {"Name": self.name, "Status": self.passed, "ip":self.ip, "user":self.user, "Category": self.category, "Help_content":self.help_content} 
        elif ',' in self.message:
            self.props = self.prop_dict()
            dict_obj = {"Name": self.name, "Status": self.passed, "Properties": self.props, "Category": self.category, "Expected_Result": self.expected_result, "Help_content":self.help_content}
        else:
            try:
                dict_obj = {"Name": self.name, "Status": self.passed, "Properties": self.message, "ip":self.ip, "user":self.user, "Category": self.category, "Help_content":self.help_content}
            except AttributeError:
                dict_obj = {"Name": self.name, "Status": self.passed, "Properties": self.message,"Category": self.category, "Help_content":self.help_content}

        if len(self.steps) > 0:
            steps_dict = []
            for step in self.steps:
                steps_dict.append(step.to_dict())
            dict_obj["checks"] = steps_dict

        return dict_obj

class ViewCheckerResult(CheckerResult):      
    def prop_dict(self):
        #print "view prop_dict"
        props  = []
        all_prop = [ x for x in self.message.split(', ') if x != '']
        for xprop in all_prop:
            #print "xprop : "+ xprop
            xprop,xstatus = xprop.split("#")
            props.append({"Message":xprop,"Status":xstatus})
        
        return props
         
    def to_dict(self):
        #print "view to_dict"
        if self.message is None:
            dict_obj = {"Name": self.name, "Status": self.passed, "ip":self.ip, "user":self.user, "Category": self.category,  "Help_content":self.help_content}
        elif ',' in self.message:
            self.props = self.prop_dict()
            dict_obj = {"Name": self.name, "Status": self.passed, "Properties": self.props, "Category": self.category, "Expected_Result": self.expected_result, "Help_content":self.help_content}
        else:
            try:
                dict_obj = {"Name": self.name, "Status": self.passed, "Message": self.message, "ip":self.ip, "user":self.user, "Category": self.category, "Help_content":self.help_content}
            except AttributeError:
                dict_obj = {"Name": self.name, "Status": self.passed, "Message": self.message,"Category": self.category, "Help_content":self.help_content}
                
                
            
        if len(self.steps) > 0:
            steps_dict = []
            for step in self.steps:
                steps_dict.append(step.to_dict())
            dict_obj["checks"] = steps_dict

        return dict_obj


class DefaultConsoleReporter:

    def __init__(self, name):
        self.name = name
        self.row_count = 0
        self.x = PrettyTable(["message", "Status"])
    def notify_progress(self, fname,*args):
        fname(*args)
        
        
    def notify_info(self, message):
        print self.name + " : " + "+++ "+message+" +++"
    
    def notify_checkGroup(self,message):
        print self.name + " : " + "\n++++ Running check group - "+message+" ++++"
        self.row_count = 0
        
    def notify_checkName(self,message):
        if self.row_count > 0:
            print str(self.x)
            
        if message == "":
            return
        
        self.x = PrettyTable([message, "Status"])
        self.x.align[message] = "l"
        self.x.align["Status"] = "l"
        self.x.padding_width = 1
        self.row_count = 0
        
        
    def notify_checkLog(self,message, status):
        if status == "FAIL":
            status = Fore.RED+status+Fore.RESET
        else:
            status = Fore.GREEN+status+Fore.RESET
        
        self.x.add_row(['\n'.join([message.replace('NoName@','').replace("NoName",'').replace('@','.')[x:x+MSG_WIDTH] for x in range(0,len(message.replace('NoName.','').replace('NoName','')),MSG_WIDTH)]).ljust(MSG_WIDTH),status])
        self.row_count += 1
    
    def notify_one_line(self,message, status):
        print "+"+"-"*MSG_WIDTH+"-"*10+"+"
        if status == "FAIL" or status == "Fail":
            status = Fore.RED+"[ "+status+" ]"+Fore.RESET
        elif status == "Err":
            status = Fore.YELLOW+"[ "+status+" ]"+Fore.RESET
        elif status == "Warn":
            status = Fore.MAGENTA+"[ "+status+" ]"+Fore.RESET
        else:
            status = Fore.GREEN+"[ "+status+" ]"+Fore.RESET
        print '\n'.join([message[x:x+MSG_WIDTH] for x in range(0,len(message),MSG_WIDTH)]).ljust(MSG_WIDTH),status
        self.row_count += 1
        

