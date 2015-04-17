'''
    This module is a driver script for running command line health check tool.
'''
__author__ = 'subashatreya'

from checkers.ncc_checker import NCCChecker
from checkers.vc_checker import VCChecker
from checkers.view_checker import HorizonViewChecker
from checkers.base_checker import CheckerBase
from reporters import DefaultConsoleReporter
from report_generator import PDFReportGenerator, CSVReportGenerator
from prettytable import PrettyTable
import json
import sys
import os
from utility import Logger

LOGGER_OBJ = Logger()

FILE_NAME = os.path.basename(__file__)

def exit_with_message(message):
    ''' Use for Exiting from health check command line with appropriate message '''
    print message+"\n"
    sys.exit(1)

def usage(checkers, message=None):
    ''' Use to display the command line usage help for user '''
    p_table = PrettyTable(["Name", "Description"])
    p_table.align["Name"] = "l"
    p_table.align["Description"] = "l" # Left align city names
    p_table.padding_width = 1 # One space between column edges and contents (default)

    for checker in checkers:
        p_table.add_row([checker.get_name(), checker.get_desc()])

    p_table.add_row(["run_all", "Runs all health checks"])

    message = message is None and str(p_table) or "\nERROR : "+ message + "\n\n" + str(p_table)
    exit_with_message(message)


def main():
    ''' main function - execution of health check tool starts from this line'''
    LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: Starting Healthcheck - inside main()")
    checkers = {}
    for checker_class in CheckerBase.__subclasses__():
        checker = checker_class()
        checkers[checker.get_name()] = checker

    args = sys.argv[1:]
    if len(args) == 0:
        usage(checkers.values())

    option = args[0]

    if option == "run_all":
        checkers_list = checkers.keys()
        if len(args) > 1:
            usage(checkers.values(), "No parameter expected after run_all")
        else:
            # We need to pass through run_all arg to the module
            args.append("run_all")

    elif option == "help":
        usage(checkers.values(), None)

    elif option not in checkers.keys():
        usage(checkers.values(), "Invalid module name " + option)

    else:
        checkers_list = [option]

    # We call configure on each module first so that we can fail-fast
    # in case some module is not configured properly
    for checker in checkers_list:
        conf_path = os.path.abspath(os.path.dirname(__file__))+os.path.sep \
        +"conf"
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: Checker configration path " \
                             + conf_path)

        checker_conf_file = conf_path + os.path.sep + checker + ".conf" 
        file_ptr = open(checker_conf_file, 'r')
        checker_config = json.load(file_ptr)
        file_ptr.close()

        knowledge_file = conf_path + os.path.sep + "knowledge_base.json" 
        file_ptr = open(knowledge_file, 'r')
        knowledge_config = json.load(file_ptr)
        file_ptr.close()

        checker_module = checkers[checker]
        reporter = DefaultConsoleReporter(checker)
        checker_module.configure(checker_config, knowledge_config, reporter)
        LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: Configured checker Details"+checker)

        
    results = {}
    for checker in checkers_list:
        checker_module = checkers[checker]
        result = checker_module.execute(args[1:])[0]
        results[checker] = result.to_dict()
    healthcheckreportfolder = os.getcwd() + os.path.sep +"reports"
    LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: HealthCheck report folder - " \
                         + healthcheckreportfolder)
    if not os.path.exists(healthcheckreportfolder):
        os.mkdir(healthcheckreportfolder)
    #Generate Json Reports
    outfile = open(os.getcwd() + os.path.sep +"reports" + os.path.sep + "results.json", 'w')
    json.dump(results, outfile, indent=2)
    outfile.close()
    LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: Results JSON generated successfully")
    #Generate CSV Reports
    CSVReportGenerator(results)
    LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: CSV report generated successfully")
    #Generate PDF Report based on results.
    PDFReportGenerator(results)
    LOGGER_OBJ.LogMessage("info", FILE_NAME + " :: PDF report generated successfully")

if __name__ == "__main__":
    main()

