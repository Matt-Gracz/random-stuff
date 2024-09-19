import pandas as pd
import mysql.connector
import json
import re

# Store program paramater values securely in a config file
with open('phone_etl.json', 'r') as config_file:
	config = json.load(config_file)

# Regex pattern to extract phone numbers consistently across data sets
def extract_nums(x):
	try:
		return None if x is None else re.sub(r'\D', '',x)
	except:
		return None

# Dataset 1: Calero/Pinnacle - These data are from the cell phone billing portal,
# Calero/Pinnacle.  We drop dupes, select only the name, phone, and emp id, and
# then rename the columns for my sanity.
calero_data = pd.read_csv('phone_data/calero.csv')\
	.drop_duplicates(subset='Subscriber ID')\
	[['Subscriber ID', 'Name', 'Service Number']]\
	.rename(columns={
    'Subscriber ID': 'emp_id_calero',
    'Name': 'name_calero',
    'Service Number': 'cell_phone_calero'
})

# Dataset 2: AiM Employee Contact data - cell phone data we input manually into AiM
# Establish a connection to the MySQL database
conn = mysql.connector.connect(
	host = config['host'],
	database = config['database'],
	user = config['user'],
	password = config['password']

)
# MySQL query to get phone numbers, emp ids, and names out of AiM
query = config['query']
# Execute the query and load the results into a pandas DataFrame
aim_raw = pd.read_sql(query, conn)
conn.close() # always have to close the connection
# Grab only the numerals from the cell phone data to match Calero
aim_raw['cell_phone_aim'] = aim_raw['cell_phone_aim'].apply(extract_nums)
aim_data = aim_raw # name the data sets consistently for my sanity

# Dataset 3:  Telecom Portal Data
# Telecom portal is another animal.  It can have duplicates that we need to match
# against AiM and calero cell phone numbers to see what numbers in the telecom
# portal are valid.  It's a little intricate.
telecom_raw = pd.read_excel('phone_data/telecom.xlsx')
# FYI: There's a trailing space in the key field 'Name ' in the telecom data.  It needs
#      to be included when referencing that column in the telecom data.
telecom_data = telecom_raw[telecom_raw['Line Type']=='Cellular']\
	[['Name ', 'Number']]\
	.rename(columns={
    	'Name ' : 'name_telecom',
    	'Number' : 'cell_phone_telecom'})
telecom_data['cell_phone_telecom'] = telecom_data['cell_phone_telecom'].apply(extract_nums)
# Some numbers are entered incorrectly into the telecom portal.  We'll dump them and then
# eliminate them from the main data set
telecom_data[telecom_data['cell_phone_telecom'].str.len() != 10].to_csv(name='misentered_cellphone_telecom.csv',index=False)
telecom_data = telecom_data[telecom_data['cell_phone_telecom'].str.len() == 10]
dupes_telecom = telecom_data[telecom_data.duplicated(subset='name_telecom',keep=False)]




