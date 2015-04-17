import web
from model import * 
import json
db = web.database(dbn='sqlite', db='deployer')
model = DataModel(db)
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
canvas = canvas.Canvas("form.pdf", pagesize=letter)

class GeneratePdf:
    
    def GET(self):
        data = web.input()
        cid = data['cid']
        tid = data['tid']
        canvas.setLineWidth(.3)
        canvas.setFont('Helvetica', 12)
        canvas.drawString(200,750,'FOUNDATION CONFIGURATION')
      #  canvas.line(200,750,580,747)
        canvas.setFont('Helvetica', 8)

        canvas.drawString(50,700,'SERVER:')
        get_customer_specific_task = model.get_history_by_taskid(cid,tid)
        configuration =  json.loads(get_customer_specific_task[0]['json_data'])
        canvas.drawString(150,700,configuration['foundation']['server'])
 
        canvas.drawString(50,680,'Cluster External IP: ')
        canvas.drawString(180,680,configuration['foundation']['restInput']['cluster_external_ip'])
        canvas.drawString(250,680,'Redundancy Factor:')
        canvas.drawString(420,680,configuration['foundation']['restInput']['redundancy_factor'])

        canvas.drawString(50,660,'Ipmi Netmask:  ')
        canvas.drawString(130,660,configuration['foundation']['restInput']['ipmi_netmask'])
        canvas.drawString(210,660,'Cvm Netmask:')
        canvas.drawString(290,660,configuration['foundation']['restInput']['cvm_netmask'])
        canvas.drawString(380,660,'Hypervisor Netmask:')
        canvas.drawString(510,660,configuration['foundation']['restInput']['hypervisor_netmask'])        

        canvas.drawString(50,630,'CVM Netmask: ')
        canvas.drawString(180,630,configuration['foundation']['restInput']['cvm_netmask'])
        canvas.drawString(280,630,'Cvm Gateway:')
        canvas.drawString(420,630,configuration['foundation']['restInput']['cvm_gateway'])

        canvas.drawString(50,600,'Cvm Dns Servers: ')
        canvas.drawString(180,600,configuration['foundation']['restInput']['cvm_dns_servers'])
        canvas.drawString(280,600,'Cvm Ntp Servers:')
        canvas.drawString(420,600,configuration['foundation']['restInput']['cvm_ntp_servers'])

        canvas.drawString(50,570,'Hypervisor ntp servers: ')
        canvas.drawString(180,570,configuration['foundation']['restInput']['hypervisor_ntp_servers'])
        canvas.drawString(280,570,'Hypervisor Nameserver:')
        canvas.drawString(420,570,configuration['foundation']['restInput']['hypervisor_nameserver'])

        canvas.drawString(50,530,'Hypervisor Password: ')
        canvas.drawString(180,530,configuration['foundation']['restInput']['hypervisor_password'])
        canvas.drawString(280,530,'Hypervisor Gateway:')
        canvas.drawString(420,530,configuration['foundation']['restInput']['hypervisor_gateway'])
        
        canvas.drawString(50,500,'Ipmi Password: ')
        canvas.drawString(180,500,configuration['foundation']['restInput']['ipmi_password'])
        canvas.drawString(280,500,'Ipmi User:')
        canvas.drawString(420,500,configuration['foundation']['restInput']['ipmi_user'])

        canvas.drawString(50,470,'Ipmi Netmask: ')
        canvas.drawString(180,470,configuration['foundation']['restInput']['ipmi_netmask'])
        canvas.drawString(280,470,'Ipmi Gateway:')
        canvas.drawString(420,470,configuration['foundation']['restInput']['ipmi_gateway'])

        canvas.drawString(50,430,'BLOCKS')
        height = 400
        blocknum = 1
        nodnum = 1
        for oneblock in configuration['foundation']['restInput']['blocks']:
            canvas.drawString(50,height,'BLOCKS'+ str(blocknum))
            if oneblock['nodes'][0]:
                for onenode in oneblock['nodes']:
                    height = height - 20 
                    canvas.drawString(80,height,'Ipmi Mac: ')
                    canvas.drawString(180,height,onenode['ipmi_mac'])
                    canvas.drawString(280,height,'Ipv6 address:')
                    canvas.drawString(420,height,onenode['ipv6_address'])
                    height = height - 20 
                    canvas.drawString(80,height,'Image Now: ')
                    canvas.drawString(180,height,str(onenode['image_now']))
                    canvas.drawString(280,height,'Node Position:')
                    canvas.drawString(420,height,onenode['node_position'])
                    height = height - 20 
                    
                    canvas.drawString(80,height,'Image Successful: ')
                    canvas.drawString(180,height,onenode['image_successful'])
                    canvas.drawString(280,height,'Ipmi Configured:')
                    canvas.drawString(420,height,str(onenode['ipmi_configured']))
                    height = height - 20 

                    canvas.drawString(80,height,'Hypervisor Hostname: ')
                    canvas.drawString(220,height,onenode['hypervisor_hostname'])
                    canvas.drawString(310,height,'Cvm gb ram:')
                    canvas.drawString(420,height,str(onenode['cvm_gb_ram']))
                    height = height - 20 

                    canvas.drawString(80,height,'Ipmi Ip: ')
                    canvas.drawString(180,height,onenode['ipmi_ip'])
                    canvas.drawString(280,height,'Cluster Member:')
                    canvas.drawString(420,height,str(onenode['cluster_member']))
                    height = height - 20 

                    canvas.drawString(80,height,'Cvm Ip: ')
                    canvas.drawString(180,height,onenode['cvm_ip'])
                    canvas.drawString(280,height,'Ipmi configure now:')
                    canvas.drawString(420,height,str(onenode['ipmi_configure_now']))
                    height = height - 40 
                   
                    if height < 100:
        
                        height = 750
                        canvas.showPage()
                        canvas.setFont('Helvetica', 8)
                    canvas.drawString(80,height,'Hypervisor Ip: ')
                    canvas.drawString(180,height,onenode['hypervisor_ip'])
                    canvas.drawString(280,height,'Ipv6 Interface:')
                    canvas.drawString(420,height,onenode['ipv6_interface'])

                nodnum = nodnum + 1
                

            height = height - 20   
            blocknum = blocknum +1
       
        canvas.setFont('Helvetica', 12)
       
        canvas.drawString(200,height,'PRISM CONFIGURATION')
      #  canvas.line(200,750,580,747)
        canvas.setFont('Helvetica', 8)
        
        if configuration['prismDetails']:
            height = height - 20 
            prismDetails =  configuration['prismDetails']
            canvas.drawString(80,height,'Rest url: ')
            canvas.drawString(180,height,prismDetails['restURL'])
            height = height - 20
            canvas.drawString(80,height,'Container:')
            canvas.drawString(180,height,prismDetails['container']['name'])           

            height = height - 20
            prismDetails =  configuration['prismDetails']
            canvas.drawString(80,height,'UserName: ')
            canvas.drawString(180,height,prismDetails['authentication']['username'])
            height = height - 20
            canvas.drawString(80,height,'Password:')
            canvas.drawString(180,height,prismDetails['authentication']['password'])   

            height = height - 20
            canvas.drawString(80,height,'Storage Pool:')
            canvas.drawString(180,height,prismDetails['storagepool']['name'])   
            height = height - 20

        canvas.setFont('Helvetica', 12)
       
        canvas.drawString(200,height,'Vcenter CONFIGURATION')
      #  canvas.line(200,750,580,747)
        canvas.setFont('Helvetica', 8)
            
        if configuration['vCenterConf']:
            height = height - 20 
            prismDetails =  configuration['vCenterConf']
            canvas.drawString(80,height,'Host: ')
            canvas.drawString(180,height,prismDetails['host'])
            height = height - 20
            canvas.drawString(80,height,'User:')
            canvas.drawString(180,height,prismDetails['user'])           

            height = height - 20
            canvas.drawString(80,height,'password: ')
            canvas.drawString(180,height,prismDetails['password'])
            height = height - 20
            canvas.drawString(80,height,'port:')
            canvas.drawString(180,height,prismDetails['port'])   

            height = height - 20
            canvas.drawString(80,height,'datacenter: ')
            canvas.drawString(180,height,prismDetails['datacenter'])
            height = height - 20
            canvas.drawString(80,height,'datacenter_reuse_if_exist:')
            canvas.drawString(180,height,prismDetails['datacenter_reuse_if_exist'])   

            height = height - 20
            canvas.drawString(80,height,'cluster: ')
            canvas.drawString(180,height,prismDetails['cluster'])
            height = height - 20
            canvas.drawString(80,height,'cluster_reuse_if_exist:')
            canvas.drawString(180,height,prismDetails['cluster_reuse_if_exist'])  
            height = height - 20 
            canvas.drawString(80,height,'HOSTS: ')
            
            
            for onehost in prismDetails['hosts']:
                   
                   
                    canvas.drawString(120,height,'IP: ')
                    canvas.drawString(180,height,onehost['ip'])
                    canvas.drawString(280,height,'user:')
                    canvas.drawString(320,height,onehost['user'])
                    
                    canvas.drawString(420,height,'Password: ')
                    canvas.drawString(480,height,str(onehost['pwd']))

                    height = height - 20 
                                    

        canvas.save()
        web.header('Content-Type', 'application/pdf')
        web.header('Content-Disposition','filename=form.pdf')
        data = open('form.pdf', 'rb').read()
        return data
    
