'''
Created on Jan 7, 2015

@author: RohitD
'''


import datetime

# This is a model - a class dealing with data representation of an object
# This example demonstrates usage of a web.py API
class DataModel:
    """
    This class will be the model class for deployer database
    we are performing all db activity here.
    
    """
    def __init__(self, db):
        self._db = db

    # Create database tables
    def init_schema(self):
        # We're using a multi-line string to not worry about line breaks
        self._db.query('''CREATE TABLE deployer_record (
            id INTEGER NOT NULL PRIMARY KEY,
            json_data TEXT NOT NULL,
            status VARCHAR(30),
            date_created TEXT NOT NULL)''')

    def init_customer_schema(self):
        self._db.query('''
            CREATE TABLE customer_data (
            customer_name TEXT NOT NULL,
            email VARCHAR(100) NOT NULL,
            phone VARCHAR(100) NOT NULL,
            customer_id VARCHAR(30) NOT NULL PRIMARY KEY,
            date_created default current_timestamp )

           ''')        

    def init_history_schema(self):
        self._db.query('''CREATE TABLE customer_history (
            id INTEGER NOT NULL PRIMARY KEY,
            task TEXT NOT NULL,
            date_created default current_timestamp,
            json_data TEXT  NULL,
            status varchar(30) NULL,
            report_file TEXT NULL,
            C_Id INTEGER,
            FOREIGN KEY (C_Id) REFERENCES customer_data(customer_id))''')          

    def init_module_status(self):
        self._db.query('''CREATE TABLE task_module_status (
            id INTEGER NOT NULL PRIMARY KEY,
            date_created default current_timestamp,
            module varchar(30) NOT  NULL ,
            status varchar(30) NULL,
            T_Id INTEGER,
            FOREIGN KEY (T_Id) REFERENCES customer_history(id))''')          
        

    def init_node_per_block_schema(self):
    
        self._db.query('''CREATE TABLE node_blocks (
            nodecount INTEGER  NOT NULL,
            model VARCHAR(80) PRIMARY KEY   NOT NULL
            )''')         

    def create(self, data):
    
        now = str(datetime.datetime.now())
        return self._db.insert('deployer_record', json_data=data, date_created=now)

    def add_customer(self, cust_name,cust_id,email,phone):
    
        now = str(datetime.datetime.now())
        return self._db.insert('customer_data', customer_name=cust_name, customer_id=cust_id,date_created=now,email=email,phone=phone)


    def get_all_customers(self):
        return list(self._db.select('customer_data'))

    def get_by_id(self, numberid):

        return list(self._db.select('customer_data', where='customer_id=$numberid',
                               vars=locals()))
    def get_history_by_id(self, customer_id):

        return list(self._db.select('customer_history', where='C_Id=$customer_id',
                               vars=locals()))
    def get_history_by_taskid(self,customer_id,task_id):

        return list(self._db.select('customer_history', where='id=$task_id and C_Id=$customer_id',
                               vars=locals()))  
    
    def list_report_files(self, customer_id):
        return list(self._db.select('customer_history',  what="report_file,date_created",where='C_Id=$customer_id',
                               vars=locals()))         

    def add_task(self,cust_id,json_data, task_type):
        now = str(datetime.datetime.now())
        return self._db.insert('customer_history',C_Id=cust_id,json_data=json_data,task=task_type,status="Pending")

    def update_task(self,task_id,task_status, report_file=None):
        now = str(datetime.datetime.now())
        return self._db.update('customer_history',where="id=$task_id",status=task_status,report_file=report_file,vars=locals())

    def get_number_of_nodes(self,model):
        
        return list(self._db.select('node_blocks', where='model=$model',
                               vars=locals())) 

    def create_task_module_status(self,t_id,module,status):
        return self._db.insert('task_module_status',T_Id=t_id,module=module,status=status)

    def update_task_module_status(self,t_id,module,status):
        return self._db.update('task_module_status', where="T_Id=$t_id and module=$module ", 
                               status = status,vars=locals())

    def get_task_status_by_id(self, task_id):
        return list(self._db.select('task_module_status', what="status,module", where='T_Id=$task_id',
                               vars=locals()))  

    def get_previous_task_form(self,cust_id,task_id):
        return list(self._db.select('customer_history',what="json_data",where="id=$task_id and C_Id=$cust_id",vars=locals()))
        
    def delete(self, numberid):
        self._db.delete('deployer_record', where='id=$numberid',
                               vars=locals())