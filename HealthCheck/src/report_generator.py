'''
Created on Oct 22, 2014

@author: krishnamurthy_b
'''
# -*- coding: utf-8 -*-

from reportlab.lib import colors

from reportlab.lib.pagesizes import inch, cm, landscape, letter
from reportlab.lib.styles import getSampleStyleSheet, StyleSheet1, ParagraphStyle
from reportlab.platypus import  LongTable, TableStyle, Image, Paragraph, Spacer, Table
from reportlab.platypus.doctemplate import SimpleDocTemplate
from reportlab.lib.enums import  TA_CENTER
from report_generator_helper import get_vc_check_actual_output_format,get_view_severity 
import copy
import time
import os
import csv
from utility import Logger

# registering the font colors for each message type
PSstyle1 = ParagraphStyle
styles = getSampleStyleSheet()
stylesheet = StyleSheet1()
NormalMsgStyle = styles['Normal']
HeadingMsgStyle = styles['Heading1']
stylesheet.add(PSstyle1(name='Footer',
                            parent=NormalMsgStyle,
                            fontName='Times-Roman'))
FooterMsgStyle = copy.deepcopy(stylesheet['Footer'])
FooterMsgStyle.alignment = TA_CENTER
stylesheet.add(PSstyle1(name='Cover',
                            parent=HeadingMsgStyle,
                            fontName='Times-Roman', fontSize=25))
CoverMsgStyle = copy.deepcopy(stylesheet['Cover'])
CoverMsgStyle.alignment = TA_CENTER
stylesheet.add(PSstyle1(name='Normal',
                            parent=NormalMsgStyle,
                            fontName='Times-Roman'))
NormalMessageStyle = copy.deepcopy(stylesheet['Normal'])
stylesheet.add(PSstyle1(name='Fail',
                            parent=NormalMsgStyle,
                            textColor=colors.red,
                            fontName='Times-Roman'))
FailMsgStyle = copy.deepcopy(stylesheet['Fail'])
stylesheet.add(PSstyle1(name='Pass',
                            parent=NormalMsgStyle,
                      textColor=colors.forestgreen,
                      fontName='Times-Roman'))
SuccessMsgStyle = copy.deepcopy(stylesheet['Pass'])
stylesheet.add(PSstyle1(name='Error',
                            parent=NormalMsgStyle,
                      textColor=colors.darkkhaki,
                      fontName='Times-Roman'))
ErrorMsgStyle = copy.deepcopy(stylesheet['Error'])
stylesheet.add(PSstyle1(name='Warning',
                            parent=NormalMsgStyle,
                      textColor=colors.purple,
                      fontName='Times-Roman'))
WarningMsgStyle = copy.deepcopy(stylesheet['Warning'])


loggerObj = Logger()

file_name = os.path.basename(__file__)

# Function for returning the font color based on the message
def getFontColor(status):
    
    if ((status == 'Fail') or (status == 'FAIL')):
        return FailMsgStyle
    elif ((status == 'Pass') or (status == 'PASS')) or ((status == 'Done') or (status == 'DONE')):
        return SuccessMsgStyle
    elif ((status == 'Warn') or (status == 'WARN')):
        return WarningMsgStyle
    elif ((status == 'err') or (status == 'Err')):
        return ErrorMsgStyle
    else:
        return NormalMessageStyle
# Function to add Header and footer to all pages except first page
def _header_footer(canvas, doc):
        # Save the state of our canvas so we can draw on it
        canvas.saveState()
        # Header
        png_path=os.path.dirname(__file__)+os.path.sep+'static'+os.path.sep+'images'+os.path.sep+'nutanixlogo.png'
        loggerObj.LogMessage("info",file_name + " :: PNG File path - " + png_path)        
        header = Image(png_path, height=0.50 * inch, width=5 * cm)
        w, h = header.wrap(doc.width, doc.topMargin)
        header.drawOn(canvas, doc.leftMargin, doc.height + doc.topMargin - h)
        
 
        # Footer
        
        footer = Paragraph('Tel: 1 (855) 688-2649 | Fax: 1 (408) 916-4039 | Email: info@nutanix.com. &copy 2014 Nutanix, Inc. All Rights Reserved.', FooterMsgStyle)
        w, h = footer.wrap(doc.width, doc.bottomMargin) 
        footer.drawOn(canvas, doc.leftMargin, h) 
        # Release the canvas
        canvas.restoreState()
        
        
# Function to generate report for VC        
def vc_report(story, checks_list,vCenterIP):
    loggerObj.LogMessage("info",file_name + " :: vc_report() Enter")    
    count = 0
    for checks in checks_list:
            count += 1
            categoryList=""
            story.append(Spacer(1, 0.01 * inch))
            categoryListLen = len(checks.get('Category'))
            for category in checks.get('Category'):
                categoryList += category
                if(categoryListLen > 1):
                    categoryList += ", "
                    categoryListLen = categoryListLen - 1
                else : 
                    continue
            checks_data = [[str(count) + ". Check: " + checks.get('Name'), "  Category: "+ categoryList]]
            checks_para_table = Table(checks_data, hAlign='LEFT')
            checks_para_table.setStyle(TableStyle([('ALIGN', (0, 0), (1, 0), 'LEFT'),
                                                   ('FONTSIZE', (0, 0), (1, 0), 10.50)]))
            
            if checks.get('Name') == 'Network Resource Pool Settings':
                checks_property_data = [['Resource Pool','Exp Shares','Current Shares','Exp Level','Current Level','Exp Limit','Current Limit','Severity']]
                property_lenght = len(checks.get('Properties'))
                for properties in checks.get('Properties'):
                   
                    if properties is not None:
                        xprop_msg, xprop_actual, xprop_exp = properties.get('Message').split("=")
                                                                
                        xprop_actual = xprop_actual.split(' (')[0] or xprop_actual.split(' ')[0] or "None"
                        if xprop_actual is not None and xprop_actual != 'False':
                            xprop_actual = xprop_actual.split("[")[1].split("]")[0]
                            xprop_actual_list = xprop_actual.split(' ')
                            current_share = xprop_actual_list[1].split(':')[-1]
                            current_level = xprop_actual_list[2].split(':')[-1]
                            current_limit = xprop_actual_list[0].split(':')[-1]  
                                
                            xprop_exp = xprop_exp.split(' )')[0] or xprop_exp.split(' ')[0] or "None"
                            if xprop_exp is not None:
                                xprop_exp = xprop_exp.split("[")[1].split("]")[0]
                                xprop_exp_list = xprop_exp.split(' ')
                                expected_share = xprop_exp_list[1].split(':')[-1]
                                expected_level = xprop_exp_list[2].split(':')[-1]
                                expected_limit = xprop_exp_list[0].split(':')[-1]
                            
                            resource_pool = xprop_msg.split("[")[1].split("]")[0]
                                                     
                            checks_property_data.append([Paragraph(resource_pool, NormalMessageStyle),
                                                         Paragraph(expected_share, NormalMessageStyle),
                                                         Paragraph(current_share, NormalMessageStyle),
                                                         Paragraph(expected_level, NormalMessageStyle),
                                                         Paragraph(current_level, NormalMessageStyle),
                                                         Paragraph(expected_limit, NormalMessageStyle),
                                                         Paragraph(current_limit, NormalMessageStyle),
                                                         Paragraph('warning', NormalMessageStyle)])
                        else:
                            property_lenght-=1
                            continue
                                
                    else:
                        property_lenght-=1
                        continue
                                         
                checks_property_table = LongTable(checks_property_data, colWidths=[1.2*inch,1*inch,1.1*inch,0.8*inch,1.1*inch,0.8*inch,1.1*inch,0.65*inch])
                checks_property_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (7, 0), colors.fidlightblue),
                                                           ('ALIGN', (0, 0), (7, property_lenght), 'LEFT'),
                                            ('INNERGRID', (0, 0), (7, -1), 0.25, colors.black),
                                            ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                                            ('BOX', (0, 0), (1, property_lenght), 0.25, colors.black),
                                            ('TEXTFONT', (0, 0), (7, 0), 'Times-Roman'),
                                            ('FONTSIZE', (0, 0), (7, 0), 10)]))

            elif checks.get('Name') == 'JVM Memory for vSphere Server':
                checks_property_data = [['Entity Checked','Memory Configured','Memory Recommended','Severity']]
                property_lenght = len(checks.get('Properties'))
                for properties in checks.get('Properties'):
                   
                    if properties is not None and properties.get('Status') == 'FAIL':
                        xprop_msg, xprop_actual, xprop_exp = properties.get('Message').split("=")
                                
                        xprop_actual = xprop_actual.split(' (')[0] or xprop_actual.split(' ')[0] or "None"
                                
                        xprop_exp = xprop_exp.split(')')[0] or xprop_exp.split(' ')[0] or "None"
                        
                        if xprop_actual == 'SSH Connection Failed':
                            property_lenght-=1
                            continue
                        else:                             
                            checks_property_data.append([Paragraph(xprop_msg, NormalMessageStyle),
                                                         Paragraph(xprop_actual, NormalMessageStyle),
                                                         Paragraph(xprop_exp, NormalMessageStyle),
                                                         Paragraph("info", NormalMessageStyle)])
                    else:
                        property_lenght-=1
                        continue
                                         
                checks_property_table = LongTable(checks_property_data, colWidths=[2.8*inch,1.6*inch,1.75*inch,1.5*inch])
                checks_property_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (3, 0), colors.fidlightblue),
                                                           ('ALIGN', (0, 0), (3, property_lenght), 'LEFT'),
                                            ('INNERGRID', (0, 0), (3, -1), 0.25, colors.black),
                                            ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                                            ('BOX', (0, 0), (1, property_lenght), 0.25, colors.black),
                                            ('TEXTFONT', (0, 0), (3, 0), 'Times-Roman'),
                                            ('FONTSIZE', (0, 0), (3, 0), 10)]))

            elif checks.get('Name') == 'Check if Default Password has Changed':
                checks_property_data = [['Component Name','IP Address','Username','Severity']]
                property_lenght = len(checks.get('Properties'))
                for properties in checks.get('Properties'):
                   
                    if properties is not None and properties.get('Status') == 'PASS':
                        xprop_msg, xprop_actual, xprop_exp = properties.get('Message').split("=")
                           
                        xprop_actual = xprop_actual.split(' (')[0] or xprop_actual.split(' ')[0] or "None"

                                                     
                        if xprop_actual == 'SSH Connection Failed' or xprop_actual == 'Connection Failed':
                            property_lenght-=1
                            continue
                        else:  
                            xprop_msg_list =  xprop_msg.split()
                            if len(xprop_msg_list) == 5:
                                component,component_ip = xprop_msg.split()[3:]
                            elif len(xprop_msg_list) == 6:
                                component1,component2,component_ip = xprop_msg.split()[3:]
                                component = component1+" "+component2
                            component = component.strip(':')
                            if xprop_actual == 'Not Changed':
                                severity = 'info'
                            else:
                                severity = 'alert'
                           
                            if component == 'Host':
                                username = 'root'
                            elif component == 'vCenter Server':
                                username ='root'
                            elif component == 'CVM':
                                username = 'nutanix'
                            elif component == 'Prism':
                                username = 'admin'
                            elif component == 'IPMI':
                                username = 'ADMIN'    
                            checks_property_data.append([Paragraph(component, NormalMessageStyle),
                                                         Paragraph(component_ip, NormalMessageStyle),
                                                         Paragraph(username, NormalMessageStyle),
                                                         Paragraph(severity, NormalMessageStyle)])
                    else:
                        property_lenght-=1
                        continue
                                         
                checks_property_table = LongTable(checks_property_data, colWidths=[2.8*inch,1.6*inch,1.75*inch,1.5*inch])
                checks_property_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (3, 0), colors.fidlightblue),
                                                           ('ALIGN', (0, 0), (3, property_lenght), 'LEFT'),
                                            ('INNERGRID', (0, 0), (3, -1), 0.25, colors.black),
                                            ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                                            ('BOX', (0, 0), (1, property_lenght), 0.25, colors.black),
                                            ('TEXTFONT', (0, 0), (3, 0), 'Times-Roman'),
                                            ('FONTSIZE', (0, 0), (3, 0), 10)]))
                               
            else:
                checks_property_data = [['Entity Tested','Datacenter Name','Cluster Name','Expected Result','Check Status','Severity']]
                property_lenght = len(checks.get('Properties'))
                expected_result = checks.get('Expected_Result')
                for properties in checks.get('Properties'):
                   
                    if properties is not None:
                        entity_tested_name = properties.get('Entity')
                        datacenter_name = properties.get('Datacenter')
                        cluster_name = properties.get('Cluster')
                        #msg = '<br/>(Exp'.join(properties.get('Message').split('(Exp'))
                        xprop_msg, xprop_actual, xprop_exp = properties.get('Message').split("=")
                        if xprop_msg == "":
                                xprop_msg = check['name']
                        xprop_actual = xprop_actual.split(' (')[0] or xprop_actual.split(' ')[0] or "None"
    
                        actual_result, is_prop_include , severity =get_vc_check_actual_output_format(checks.get('Name'),
                                                                                                     xprop_actual,
                                                                                                     properties.get('Entity'),
                                                                                                     properties.get('Datacenter'),
                                                                                                     properties.get('Cluster'),
                                                                                                     properties.get('Host'),
                                                                                                     properties.get('Status'),
                                                                                                     properties.get('Message'),
                                                                                                     xprop_exp.strip(')'),
                                                                                                     vCenterIP)
                        
                        if is_prop_include == False:
                            property_lenght-=1
                            continue
                        
                        checks_property_data.append([Paragraph(entity_tested_name, NormalMessageStyle),
                                                     Paragraph(datacenter_name, NormalMessageStyle),
                                                     Paragraph(cluster_name, NormalMessageStyle),
                                                     Paragraph(expected_result, NormalMessageStyle),
                                                     Paragraph(actual_result, NormalMessageStyle),
                                                     Paragraph(severity, NormalMessageStyle)])
    
                
                if len(checks_property_data) == 1:
                    property_data = [['Status: PASS(Either all entities configured correctly or No entities found to run check)']]
                    checks_property_table = LongTable(property_data, colWidths=[7.7*inch])
                    checks_property_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (0, 0), colors.fidlightblue),
                                                               ('ALIGN', (0, 0), (0, property_lenght), 'LEFT'),
                                                ('INNERGRID', (0, 0), (0, -1), 0.25, colors.black),
                                                ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                                                ('BOX', (0, 0), (1, property_lenght), 0.25, colors.black),
                                                ('TEXTFONT', (0, 0), (0, 0), 'Times-Roman'),
                                                ('FONTSIZE', (0, 0), (0, 0), 10)]))
                
                elif len(checks_property_data) > 1:                            
                    checks_property_table = LongTable(checks_property_data, colWidths=[1*inch,1.2*inch,1*inch,1.15*inch,2.7*inch,0.65*inch])
                    checks_property_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (5, 0), colors.fidlightblue),
                                                               ('ALIGN', (0, 0), (5, property_lenght), 'LEFT'),
                                                ('INNERGRID', (0, 0), (5, -1), 0.25, colors.black),
                                                ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                                                ('BOX', (0, 0), (1, property_lenght), 0.25, colors.black),
                                                ('TEXTFONT', (0, 0), (5, 0), 'Times-Roman'),
                                                ('FONTSIZE', (0, 0), (5, 0), 10)]))
                
               
            story.append(checks_para_table)
            story.append(Spacer(1, 0.05 * inch))
            story.append(checks_property_table)
            story.append(Spacer(1, 0.3 * inch))

    loggerObj.LogMessage("info",file_name + " :: vc_report() Exit")    
    
            
# Function to generate report for NCC
def ncc_report(story, checks_list):
    loggerObj.LogMessage("info",file_name + " :: ncc_report() Enter")        
    property_lenght = len(checks_list)
    checks_property_data = [['Properties Tested', 'Status']]
    for checks in checks_list:
    
            status = checks.get('Status')
            msg = checks.get('Name')
            checks_property_data.append([Paragraph(msg, NormalMessageStyle), Paragraph(status, getFontColor(status))])
          
            
                   
    checks_property_table = LongTable(checks_property_data, colWidths=[6 * inch, 0.75 * inch])
    # style sheet for table
    checks_property_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (1, 0), colors.fidlightblue),
                                                       ('ALIGN', (0, 0), (1, property_lenght), 'LEFT'),
                                        ('INNERGRID', (0, 0), (2, -1), 0.25, colors.black),
                                        ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                                        ('BOX', (0, 0), (1, property_lenght), 0.25, colors.black),
                                        ('TEXTFONT', (0, 0), (1, 0), 'Times-Roman'),
                                        ('FONTSIZE', (0, 0), (1, 0), 10)]))
            
           
            # story.append(checks_para_table)
    story.append(Spacer(1, 0.05 * inch))
    story.append(checks_property_table)
    story.append(Spacer(1, 0.3 * inch))
    
    loggerObj.LogMessage("info",file_name + " :: vc_report() Exit")    


# Function to generate report for VIEW
def view_report(story, checks_list):
    loggerObj.LogMessage("info",file_name + " :: view_report() Enter")        
    count = 0
    for checks in checks_list:
            count += 1
            categoryList=""
            story.append(Spacer(1, 0.01 * inch))
            categoryListLen = len(checks.get('Category'))
            for category in checks.get('Category'):
                categoryList += category
                if(categoryListLen > 1):
                    categoryList += ","
                    categoryListLen = categoryListLen - 1
                else : 
                    continue   
            checks_data = [[str(count) + ". Check: " + checks.get('Name'), "  Category: "+ categoryList]]
            checks_para_table = Table(checks_data, hAlign='LEFT')
            checks_para_table.setStyle(TableStyle([('ALIGN', (0, 0), (1, 0), 'LEFT'),
                                                   ('FONTSIZE', (0, 0), (1, 0), 10.50)]))
            checks_property_data = [['Actual Result', 'Expected Result','Check Status','Severity']]
            property_lenght = len(checks.get('Properties'))
            for properties in checks.get('Properties'):
               
                if properties is not None:
                    xprop_actual,xprop_result, xprop_exp = properties.get('Message').split(":=")
                    actual_result = xprop_result.split("(Expected")[0]
                    expected_result = xprop_exp[:-1]
                    check_status = properties.get('Status')
                    
                    severity_info =  get_view_severity(checks.get('Name'))

                    
                checks_property_data.append([Paragraph(actual_result.replace(';','<br/>'), NormalMessageStyle),
                                             Paragraph(expected_result.replace(';','<br/>'), NormalMessageStyle),
                                             Paragraph(check_status,getFontColor(check_status)),
                                             Paragraph(severity_info, NormalMessageStyle)])

            checks_property_table = LongTable(checks_property_data, colWidths=[2.5*inch,2.75*inch,1*inch,0.75*inch])
            checks_property_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (3, 0), colors.fidlightblue),
                                                       ('ALIGN', (0, 0), (3, property_lenght), 'LEFT'),
                                        ('INNERGRID', (0, 0), (3, -1), 0.25, colors.black),
                                        ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                                        ('BOX', (0, 0), (1, property_lenght), 0.25, colors.black),
                                        ('TEXTFONT', (0, 0), (3, 0), 'Times-Roman'),
                                        ('FONTSIZE', (0, 0), (3, 0), 10)]))
            
            story.append(checks_para_table)
            story.append(Spacer(1, 0.05 * inch))
            story.append(checks_property_table)
            story.append(Spacer(1, 0.3 * inch))
            
    loggerObj.LogMessage("info",file_name + " :: view_report() Exit")    
            
    
def PDFReportGenerator(resultJson,curdir=None):
    file_name = os.path.basename(__file__)
    loggerObj.LogMessage("info",file_name + " :: PDFReportGenerator() Enter")    
     
    # Adding timestamp to the report name  
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    
    # path for generating the report
    if curdir is None:
        pdffilename = os.getcwd() + os.path.sep +"reports" + os.path.sep+ 'Healthcheck-' + timestamp + '.pdf'
    else:
        pdffilename =  curdir + os.path.sep +"reports" + os.path.sep+ 'Healthcheck-' + timestamp + '.pdf' 

    loggerObj.LogMessage("info",file_name + " :: PDF report path is - " + pdffilename)    
        
    doc = SimpleDocTemplate(pdffilename, pagesizes=letter, format=landscape, rightMargin=inch / 8, leftMargin=inch / 12, topMargin=inch, bottomMargin=inch / 4)
    story = []
    date = time.strftime("%B %d, %Y")
    png_path=os.path.abspath(os.path.dirname(__file__))+os.path.sep+'static'+os.path.sep+'images'+os.path.sep+'hcr.png'
    headingdata = [["   ", "   ", "  ", "  ", Image(png_path, height=0.37 * inch, width=12 * cm)],
                    [ "    ", "    ", "   ", "   ", "  " , date]]
    headingtable = Table(headingdata)
    headingtable.setStyle(TableStyle([('ALIGN', (0, 1), (4, 1), 'RIGHT'),
                                      ('TEXTFONT', (0, 1), (4, 1), 'Times-Roman'),
                                      ('FONTSIZE', (0, 1), (4, 1), 12)]))
    story.append(headingtable)

    
    for checkers in resultJson.keys():
        checkers_table_data = []
        # Adding heading to the document based on the checkers
        if checkers == 'ncc':
            checkers_table_data = [["Nutanix Cluster"+ " ["+resultJson[checkers].get('ip')+"] "+" Health Check Results"]]
            checkers_table_data.append([Paragraph("Username:" + resultJson[checkers].get('user'), NormalMessageStyle)])
        elif checkers == 'vc':
            checkers_table_data = [["vCenter"+ " ["+resultJson[checkers].get('ip')+"] "+" Health Check Results"]]
            checkers_table_data.append([Paragraph("Username:" + resultJson[checkers].get('user'), NormalMessageStyle)])
        elif checkers == 'view':
            checkers_table_data = [["VMware View"+ " ["+resultJson[checkers].get('ip')+"] "+" Check Results"]]
            checkers_table_data.append([Paragraph("Username:" + resultJson[checkers].get('user'), NormalMessageStyle)])        
        
        checkers_table = LongTable(checkers_table_data)
        # style sheet for table
        checkers_table.setStyle(TableStyle([('ALIGN', (0, 0), (0, 0), 'CENTRE'),
                                            ('TEXTFONT', (0, 0), (0, 1), 'Times-Bold'),
                                            ('FONTSIZE', (0, 0), (0, 0), 14),
                                            ('BACKGROUND', (0, 0), (0, 0), colors.fidlightblue)]))
        story.append(checkers_table)
        story.append(Spacer(1, 0.03 * inch))
        # calling the function based on the checkers
        if resultJson[checkers].get('checks') is None:
            exit()
        if checkers == 'vc':
            loggerObj.LogMessage("info",file_name + " :: PDF report for vc")                    
            vc_report(story, resultJson[checkers].get('checks'),resultJson[checkers].get('ip'))
        if checkers == 'ncc':
            loggerObj.LogMessage("info",file_name + " :: PDF report for ncc")                    
            ncc_report(story, resultJson[checkers].get('checks'))
        if checkers == 'view':
            loggerObj.LogMessage("info",file_name + " :: PDF report for view")                    
            view_report(story, resultJson[checkers].get('checks'))            
    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    
    pdf_report_name = pdffilename.split(os.path.sep)[-1]
    generic_report_name = pdf_report_name.split('.')[0]

    if curdir is None:
        print "\nReport ("+pdf_report_name+") generated successfully at :: " + os.getcwd() + os.path.sep +"reports"
    else:
        print "\nReport ("+pdf_report_name+") generated successfully at :: " + curdir + os.path.sep +"reports" 
    
    loggerObj.LogMessage("info",file_name + " :: PDF report generated successfully")        
    loggerObj.LogMessage("info",file_name + " :: PDFReportGenerator() Exit")    
         
    return pdf_report_name



def CSVReportGenerator(resultJson,curdir=None): 
    file_name = os.path.basename(__file__)
    loggerObj.LogMessage("info",file_name + " :: CSVReportGenerator() Enter")    
       
    timestamp = time.strftime("%Y%m%d-%H%M%S")  
    if curdir is None:
        csvfilename = os.getcwd() + os.path.sep +"reports" + os.path.sep+ 'Healthcheck-' + timestamp + '.csv'
    else:
        csvfilename =  curdir + os.path.sep +"reports" + os.path.sep+ 'Healthcheck-' + timestamp + '.csv'      

    loggerObj.LogMessage("info",file_name + " :: CSV report path is - " + csvfilename)    
        
    rows = []
    details = []
    details.append(["Nutanix Cluster Health Check Results"])
    rows.append(["Category", "Health Check Variable","Entity Tested","Datacenter Name","Cluster Name","Expected Result","Check Status","Check Category", "Severity"])
    for xchecker,allChecks in resultJson.iteritems():
        details.append(["IP",allChecks['ip']])
        details.append(["Category",allChecks['Name']])
        details.append(["User Name",allChecks['user']])
        details.append(["Timestamp",str(time.strftime("%B %d, %Y %H:%M:%S"))])
        #details.append(["Overall Check Status",allChecks['Status']])
            
        try:
            for xcheck in allChecks['checks']:
                if isinstance(xcheck['Properties'], list):
                    #rows.append([xchecker, xcheck['Name'],"Overall Status",xcheck['Status'], xcheck['Severity']])
                    for prop in xcheck['Properties']:
                        if(xchecker == "vc"):
                            xprop_msg, xprop_actual, xprop_exp = prop['Message'].split("=")
                            if xprop_msg == "":
                                xprop_msg = check['name']
                            xprop_actual = xprop_actual.split(' (')[0] or xprop_actual.split(' ')[0] or "None"
    
                            actual_result, is_prop_include , severity =get_vc_check_actual_output_format(xcheck['Name'],
                                                                                                     xprop_actual,
                                                                                                     prop['Entity'],
                                                                                                     prop['Datacenter'],
                                                                                                     prop['Cluster'],
                                                                                                     prop['Host'],
                                                                                                     prop['Status'],
                                                                                                     prop['Message'],
                                                                                                     xprop_exp.strip(')'),
                                                                                                     allChecks['ip'])
                            if is_prop_include == False:
                               continue
                           
                            rows.append([xchecker, xcheck['Name'],prop['Entity'],prop['Datacenter'],prop['Cluster'],xcheck['Expected_Result'],actual_result,'|'.join(xcheck['Category']), severity])
                        elif(xchecker == "view"):  
                            xprop_actual,xprop_result, xprop_exp = prop.get('Message').split(":=")
                            actual_result = xprop_result.split("(Expected")[0]
                            expected_result = xprop_exp[:-1]
                            check_status = prop.get('Status')
                    
                            severity_info =  get_view_severity(xcheck['Name'])
                            rows.append([xchecker, xcheck['Name'],None,None,None,expected_result,actual_result,'|'.join(xcheck['Category']), severity_info])   
                else:
                    if(xchecker == "vc"):
                        pass
                    elif(xchecker == "ncc"):
                        rows.append([xchecker, xcheck['Name'],None,None,None,None,xcheck['Status'],None,None])
        except KeyError:
                #It means- No checks were executed for this checker. 
            continue
        
#    if len(rows) > 1:
    details.append([None])
    csv_file_name = csvfilename
    csv_file = open(csv_file_name ,'wb')
    csv_writer = csv.writer(csv_file, delimiter=',', quoting=csv.QUOTE_MINIMAL)
    csv_writer.writerows(details)
    csv_writer.writerows(rows)
    csv_file.close()

    loggerObj.LogMessage("info",file_name + " :: CSVReportGenerator() Exit")    
             
