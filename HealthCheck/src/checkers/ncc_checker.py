'''
    This module is to run health check against the CVM.
    i.e. controller vm where ncc utility is installed.
'''

__author__ = 'subashatreya'


import paramiko
from base_checker import *
from prettytable import PrettyTable
import sys
import ast
import getpass
import utility
from utility import Validate, Security, Logger
import socket
from colorama import Fore
from web import form
import time

MSG_WIDTH = 120
LOGGER_OBJ = Logger()
FILE_NAME = os.path.basename(__file__)

def exit_with_message(message):
    print message
    sys.exit(1)


class NCCChecker(CheckerBase):
    _NAME_ = "ncc"

    def __init__(self):
        super(NCCChecker, self).__init__(NCCChecker._NAME_)

        pwd = Security.decrypt(self.authconfig['cvm_pwd'])
        self.config_form = form.Form(form.Textbox('CVM IP', value=self.authconfig['cvm_ip']),\
                         form.Textbox('CVM SSH Host Username', value=self.authconfig['cvm_user']),\
                         form.Password('CVM SSH Host Password', value=pwd))() 

    def get_name(self):
        return NCCChecker._NAME_

    def get_desc(self):
        return "Performs Nutanix cluster health checks"

    def configure(self, config, knowledge_pool, reporter):
        self.config = config
        self.knowledge_pool = knowledge_pool[self.get_name()]
        self.reporter = reporter
        self.authconfig = self.get_auth_config(self.get_name())
        CheckerBase.validate_config(self.authconfig, "cvm_ip")
        CheckerBase.validate_config(self.authconfig, "cvm_user")
        CheckerBase.validate_config(self.authconfig, "cvm_pwd")
        CheckerBase.validate_config(self.config, "ncc_path")

    def usage(self, message=None):
        x_table = PrettyTable(["Name", "Short help"])
        x_table.align["Name"] = "l"
        x_table.align["Short help"] = "l"  # Left align city names
        x_table.padding_width = 1  # One space between column edges and contents (default)
        x_table.add_row(["ncc", "Run NCC checks."])
        x_table.add_row(["ncc setup", "Set Nutanix Cluster Check Configuration"])
        message = message is None and str(x_table) or "\nERROR : " + message + "\n\n" + str(x_table)
        exit_with_message(message)

    def execute(self, args, req_type="cmd"):

        if len(args) != 0:
            if args[0] == 'setup':
                self.setup()
                exit_with_message("Nutanix Cluster is configured.")

        ssh = None
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.authconfig['cvm_ip'], username=self.authconfig['cvm_user'], \
                        password=Security.decrypt(self.authconfig['cvm_pwd']))
        except paramiko.AuthenticationException:
            LOGGER_OBJ.LogMessage("error", FILE_NAME + \
                                  " :: NCC Authentication failed - Invalid username or password")
            if req_type == "cmd":
                exit_with_message("Error : " + \
                "Authentication failed - Invalid username or password \n\nPlease run \"ncc setup\" command to configure ncc.")
            else:
                return (self.result, "Error : Authentication failed - Invalid username or password")
        except paramiko.SSHException, exception_obj:
            LOGGER_OBJ.LogMessage("error", FILE_NAME + " :: NCC SSH Exception" + exception_obj.message)
            if req_type == "cmd":
                exit_with_message("Error : " + str(exception_obj) + "\n\nPlease run \"ncc setup\" command to configure ncc.")
            else:
                return (self.result, "Error :  NCC SSH Exception")
        except socket.error, exception_obj:
            LOGGER_OBJ.LogMessage("error", FILE_NAME + " :: NCC Socket Error" + exception_obj.message)
            if req_type == "cmd":
                exit_with_message(str(exception_obj) + "\n\nPlease run \"ncc setup\" command to configure ncc.")
            else:
                return (self.result, "Error : NCC Socket Error")
        except:
            LOGGER_OBJ.LogMessage("error", FILE_NAME + " :: " + sys.exc_info()[0])
            if req_type == "cmd":
                exit_with_message("Unexpected Error :" + sys.exc_info()[0])
            else:
                return (self.result, "Error : " + sys.exc_info()[0])

        self.result = CheckerResult("ncc", self.authconfig)

        ntnx_env = "source /etc/profile.d/zookeeper_env.sh && source /usr/local/nutanix/profile.d/nutanix_env.sh && "
        # check if ncc is installed on the CVM
        stdin, stdout, stderr = ssh.exec_command(ntnx_env + "ncc --ncc_version")
        for line in stderr:
            if ("ncc: not found" in line) or ("ncc: command not found" in line) or \
            ("can\'t open \'/etc/profile.d/zookeeper_env.sh\'" in line) or \
            ("can\'t open \'/usr/local/nutanix/profile.d/nutanix_env.sh'" in line):
                if req_type == "cmd":
                    exit_with_message("NCC is not installed on this CVM\nPlease login to CVM,install NCC and then run Healthcheck again.")
                else:
                    return (self.result, "Error : NCC is not installed on this CVM")
        LOGGER_OBJ.LogMessage("info", "NCC Version Running on CVM :: " + stdout.readline().strip())

        # new command that run only health_checks for ncc
        cmd = len(args) > 0 and self.config['ncc_path'] + " --ncc_interactive=false health_checks " + " ".join(args) or self.config['ncc_path'] + " health_checks "
        # JIRA GSO-535
        # Exporting sbin path as As to run network_checks and data_protection_checks of NCC.
        # sbin is required in PATH as NCC execute /sbin/ route & /sbin/ifconfig command \
        # while executing network_checks and data_protection_checks respectively
        export_env = "export PATH=$PATH:/usr/local/sbin:/usr/sbin:/sbin && "

        # old command
        # cmd = len(args) > 0 and self.config['ncc_path'] + " --ncc_interactive=false " + " ".join(args) or self.config['ncc_path']
        cmd = ntnx_env + export_env + cmd
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: NCC Command to execute -  " + str(cmd))
        status_text = {0 : "Done", 1 : "Done", 3 : "Pass", 4: "Pass", 5: "Warn", 6: "Fail", 7: "Err"}
        time.sleep(1)
        try:
            stdin, stdout, stderr = ssh.exec_command(cmd)
        except paramiko.ChannelException, exception_obj:
            LOGGER_OBJ.LogMessage("error", FILE_NAME + " :: NCC SSH execution failed:: " + exception_obj.message)
            if req_type == "cmd":
                exit_with_message(str(exception_obj) + "\n\nUnable to get NCC results through SSH")
            else:
                return (self.result, "Error : Unable to get NCC results through SSH")
        except:
            LOGGER_OBJ.LogMessage("error", FILE_NAME + " :: " + sys.exc_info()[0])
            if req_type == "cmd":
                exit_with_message("Unexpected Error :" + sys.exc_info()[0])
            else:
                return (self.result, "Error : " + sys.exc_info()[0])

        passed_all = True
        # self.realtime_results['ncc'] = []
        first_json = 0
        for current_line in stdout:
            if "Another execution of NCC is in progress" in current_line:
                LOGGER_OBJ.LogMessage("error", FILE_NAME + " :: Another execution of NCC is in progress")
                if req_type == "cmd":
                    exit_with_message("Error : Another execution of NCC is in progress.\nPlease run NCC Healthcheck after some time.")
                else:
                    return (self.result, "Error : Another execution of NCC is in progress")

            if utility.glob_stopExecution:
                return (self.result, "Stopped")
            try:
                json_equiv = ast.literal_eval(current_line.strip('\n').replace("null", "'null'").replace("true", "'true'").replace("false", "'false'"))
                first_json += 1
            except:
                print current_line
                continue

            if first_json == 1:
                self.reporter.notify_progress(self.reporter.notify_info, "Starting NCC Checks")

            check_name = json_equiv["output holder list"][0]["message"]
            status = json_equiv["status"]

            LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: NCC Check Name - " + check_name + ", Check Status - " + str(status))

            try:
                self.realtime_results = json.load(open("display_json.json", "r"))
                self.realtime_results['ncc']['checks'].append({'Name':check_name, 'Status':status_text[status],  "knowledge":self.knowledge_pool.get(check_name, None)})
                with open("display_json.json", "w") as myfile:
                    json.dump(self.realtime_results, myfile)
                LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: NCC Check dumped to JSON file")
            except:
                pass
            message = ""
            if status in [7]:
                message = json_equiv["detail canvas"]["output holder list"][0]["message list"][0]

            if status < 6:
                self.result.add_check_result(CheckerResult(check_name, None, status_text[status], message))
            else:
                self.result.add_check_result(CheckerResult(check_name, None, status_text[status], message, None, None, None, self.knowledge_pool.get(check_name, None)))

            self.reporter.notify_one_line(check_name, status_text[status])
            if status not in [0, 1, 3, 4]:
                passed_all = False
        self.result.passed = (passed_all and "PASS" or "FAIL")
        if first_json:
            print "+" + "-"*MSG_WIDTH + "-"*10 + "+"
            self.reporter.notify_progress(self.reporter.notify_info, "NCC Checks complete")
        ssh.close()
        return (self.result, "Complete")


    def setup(self):
        print "\nConfiguring NCC :\n"
        current_cvm_ip = self.authconfig['cvm_ip'] if ('cvm_ip' in self.authconfig.keys()) else "Not Set"
        cvm_ip = raw_input("Enter CVM IP [default: " + current_cvm_ip + "]: ")
        cvm_ip = cvm_ip.strip()
        if cvm_ip == "":
            if current_cvm_ip == "Not Set":
                LOGGER_OBJ.LogMessage("error", FILE_NAME + " :: Error: Set CVM IP.")
                exit_with_message("Error: Set CVM IP.")
            cvm_ip = current_cvm_ip

        if Validate.valid_ip(cvm_ip) == False:
            LOGGER_OBJ.LogMessage("error", FILE_NAME + " :: Error: Invalid CVM IP address.")
            exit_with_message("\nError: Invalid CVM IP address.")

        # cvm_ip=raw_input("Enter CVM IP : ")
        current_cvm_user = self.authconfig['cvm_user'] if ('cvm_user' in self.authconfig.keys()) else "Not Set"
        cvm_user = raw_input("Enter CVM SSH Host Username [default: " + current_cvm_user + "]: ")
        cvm_user = cvm_user.strip()
        if cvm_user == "":
            if current_cvm_user == "Not Set":
                LOGGER_OBJ.LogMessage("error", FILE_NAME + " :: Error: Set CVM SSH Host Username.")
                current_cvm_user("Error: Set CVM SSH Host Username.")
            cvm_user = current_cvm_user
        # cvm_user=raw_input("Enter CVM User Name : ")

        current_pass = self.authconfig['cvm_pwd'] if ('cvm_pwd' in self.authconfig.keys()) else "Not Set"
        new_pass = getpass.getpass('Enter CVM SSH Host Password [Press enter to use previous password]: ')
        cvm_pwd = None
        if new_pass == "":
            if current_pass == "Not Set":
                LOGGER_OBJ.LogMessage("error", FILE_NAME + " :: Error: Set CVM SSH Host Password.")
                exit_with_message("Error: Set CVM SSH Host Password.")
            cvm_pwd = current_pass
        else:
            confirm_pass = getpass.getpass('Re-Enter CVM SSH Host Password: ')
            if new_pass != confirm_pass:
                exit_with_message("\nError :Password miss-match. Please run \"ncc setup\" command again")
            cvm_pwd = Security.encrypt(new_pass)

        # Test SSH connection
        print "Checking CVM Connection Status:",
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: Checking CVM Connection Status")

        status, message = self.check_connectivity(cvm_ip, cvm_user, cvm_pwd)
        if status == True:
            print Fore.GREEN + " Connection successful" + Fore.RESET
        else:
            print Fore.RED + " Connection failure" + Fore.RESET
            exit_with_message(message)

        # print "cvm_ip :"+cvm_ip+" cvm_user :"+cvm_user+" cvm_pwd : "+cvm_pwd
        ncc_auth = dict()
        ncc_auth["cvm_ip"] = cvm_ip
        ncc_auth["cvm_user"] = cvm_user
        ncc_auth["cvm_pwd"] = cvm_pwd

        CheckerBase.save_auth_into_auth_config(self.get_name(), ncc_auth)
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: NCC configurations saved successfully")
        exit_with_message("NCC is configured Successfully ")
        return

    def check_connectivity(self,cvm_ip, cvm_user, cvm_pwd, req_type="cmd"):
        ssh = None
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(cvm_ip, username=cvm_user, password=Security.decrypt(cvm_pwd))
            ssh.close()
            return (True, None)
        except paramiko.AuthenticationException:
            LOGGER_OBJ.LogMessage("error", FILE_NAME + " :: NCC Authentication failed - Invalid username or password")
            if req_type == "cmd":
                return (False, ("Error : " + "Authentication failed - Invalid username or password \n\nPlease run \"ncc setup\" command to configure ncc."))
            else:
                return (False, "Error : Authentication failed - Invalid username or password")
        except paramiko.SSHException, exception_obj:
            LOGGER_OBJ.LogMessage("error", FILE_NAME + " :: NCC SSH Exception" + exception_obj.message)
            if req_type == "cmd":
                return (False, ("Error : " + str(exception_obj) + "\n\nPlease run \"ncc setup\" command again."))
            else:
                return (False, "Error : " + str(exception_obj))
        except socket.error, exception_obj:
            LOGGER_OBJ.LogMessage("error", FILE_NAME + " :: NCC Socket Error" + exception_obj.message)
            if req_type == "cmd":
                return (False, (str(exception_obj) + "\n\nPlease run \"ncc setup\" command again."))
            else:
                return (False, str(exception_obj))

