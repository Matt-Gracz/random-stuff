import datetime
import requests
import pandas as pd
import urllib #for formatting URL strings in the REST calls
from cryptography.fernet import Fernet # Securing the API credentials
import os

"""
Note from Matt on authenticating

To authenticate ReADY REST API calls you need to either:
a) get the private key from me and put it in the environment
variable READY_ENC_KEY if you're using the same servers as me,
OR
b) Run Fernet's encryption on your own server's password
OR
b) override the get_credentials() function with your own organization's
preferred method of securing basic auth API credentials.


# TODO: make this runnable from windows CLI

"""

## TODO put these all in a config file
SERVER = 'test' #prod -- TODO make this a CLI param
END_POINT = f'https://uwisc{SERVER}.assetworks.cloud/ready/api/reporting/request?'

TEMPLATE_PIECE = 'template'
REQUEST_ID_PIECE = 'request'
START_DATE_PIECE = 'startDate'
END_DATE_PIECE = 'endDate'
CLOSED_PIECE = 'closed'
# TODO - Nightly ETL the template names to a queryable resource
TEMPLATES = ['After Hours Call Center','Customer Request','Keys','Abatement Risk Asessment', 'Bio-Safety Cabinet Service',\
			'Move Request', 'AssetWorks Access Request', 'Remodel Project', 'Digger Request','Vehicle Maintenance',\
			'Helium / Nitrogen', 'Capital Project Support', 'Space Management WO', 'Heating Plant Internal Request', 'Physical Plant Asset Repair' ]
ALL_COMMON_FIELDS = ['template', 'values', 'title', 'additionalFieldsValues', 'closed', 'dateCreated', 'requestor',\
				'requestId', 'workflowStates', 'respondents', 'aimStatusHistory.primaryKey', 'workflowResponses']
COMMON_FIELDS = ['template', 'title', 'CLOSED_FLAG', 'dateCreated', 'requestor', 'requestId']
COMMON_FIELDS_CSV_BASE_NAME = 'todays_request_data'
CLOSED_FLAG = 'closed'
REQUEST_ID = 'requestId'
DEFAULT_DATE_FORMAT = '%Y-%m-%d'
OPEN_REQUEST_IDS_FNAME = 'open_request_ids.csv'
HTTP_TIMEOUT_TOLERANCE = 60 # Number of seconds to wait for response from the ReADY server
PRIVATE_KEY_ENV_VAR = 'READY_ENC_KEY' # Private key for the encrypted credentials
ENC_CREDS_VAR = 'READY_ENC_CREDS' # Encrypted credentials stored in env instead of a file

def get_credentials():
	# Load the private key and encrypted credentials from an env var
	# .encode is used because we need to pass in bytes not ascii text
	# to the decryption algorithm, and getenv returns a string. From
	# the manpage: "key, default and the result are str."
	key = os.getenv(PRIVATE_KEY_ENV_VAR).encode()
	encrypted_credentials = os.getenv(ENC_CREDS_VAR).encode()

	# Create a CBC. A CBC is a chain of small ciphers each working on a contiguous
	# subset of the plaintext.  Each cipher except the first constructs its internal
	# private key as a vectorized output of the previous cipher. The concat'd ciphered
	# (i.e., encrypted) text blocks together make up the entire key.
	# Fernet official documentation isn't great; this webpage explains it all well:
	# https://www.comparitech.com/blog/information-security/what-is-fernet/
	cipher_suite = Fernet(key)

	# Invoke decryption algorithm with the default: 128-bit AES in CBC mode
	# We use .decode for the inverse reason as above: we need to pass in plain
	# text to the API call.
	decrypted_credentials = cipher_suite.decrypt(encrypted_credentials).decode()

	# Return the username/password. Once decrypted, they are delimited by a colon
	return decrypted_credentials.split(':')
USER,PW = get_credentials()

# Since the date range can be very large, yielding the dates into a generator
# object to convert to a list later is faster than constructing the list here
def gen_date_range(start_date_str, end_date_str):
    start_date = datetime.datetime.strptime(start_date_str, DEFAULT_DATE_FORMAT).date()
    end_date = datetime.datetime.strptime(end_date_str, DEFAULT_DATE_FORMAT).date()
    
    for n in range(int((end_date - start_date).days) + 1):
        yield (start_date + datetime.timedelta(n)).strftime(DEFAULT_DATE_FORMAT)

# return a string formatted with YYYY-MM-DD that represents today's date 
def get_today_as_string():
	return datetime.datetime.strftime(datetime.datetime.now(), DEFAULT_DATE_FORMAT)

# Make a generic rest call to the ReADY SERVER
def make_REST_call(url):
	return requests.get(url, timeout=HTTP_TIMEOUT_TOLERANCE, auth=(USER,PW)).json()

# Constructs an API URL out of param:value pairs
def construct_url(params, values):
    # Use urlencode to handle parameter-value pairs and proper encoding
    # Depending on env it might use + to encode spaces.  This is OK, even
    # if it looks weird.

    # Map params to values
    param_map = dict(zip(params, values))
    # Parse text into HTML-friendly text
    param_part = urllib.parse.urlencode(param_map)

    return f'{END_POINT}{param_part}'

# TODO logging instead of printing


# set only_open to False to get all requests in the range; will be markedly
# slower and more likely to time out
def get_requests_from_str_range(start_date_str, end_date_str, only_open=True):
	requests_to_return = []
	for template in TEMPLATES:
		try:
			# IMPORTANT: Order of URL pieces matters
			url = construct_url(params=(TEMPLATE_PIECE, START_DATE_PIECE, END_DATE_PIECE),\
								values= (template, start_date_str, end_date_str))
			print(url)

			ready_requests = make_REST_call(url)
			print('done with call')
			for ready_request in ready_requests:
				if not only_open or (only_open and not ready_request[CLOSED_FLAG]):
					requests_to_return.append(ready_request)
		except Exception as e:
			print(f'Something went wrong with {template} for {(start_date_str, end_date_str)}') #TODO - logging
			print(f'Error: {str(e)}')
		print(f'Done with {template}.  Num requests:{len(requests_to_return)}')
	return requests_to_return


def get_requests_day_by_day(start_date_str, end_date_str, only_open=True):
	return [request\
			for date in gen_date_range(start_date_str, end_date_str)\
			for request in get_requests_from_str_range(date, date, only_open=only_open)]


def get_todays_open_requests():
	today_string = get_today_as_string() 
	# be exlicit about only getting open requests
	return get_requests_from_str_range(today_string, today_string, only_open=True)

# Save request ids to disk.  We will typically read this later as yesterday's open requests to compare
# against the next day's open ReADY requests when updating our daily requests.  This operation
# overwrites the last file; it doesn't append the requests to yesterday's as that would introduce
# a rolling unncessary duplication of requests shared between the days, every time this is run.
def persist_request_ids(iterable_requests, file_name):
	pd.DataFrame([request[REQUEST_ID] for request in iterable_requests]).to_csv(file_name, header=None)

# Extracts all of today's open requests and requests closed today and save it to a CSV
# to be processed into DB tables later.
def do_etl_for_today():
	# get yesterday's open requests' IDs.
	# squeeze converts it from a 2D dataframe to a 1D data series.
	# Makes it easer to compute set difference later
	yesterdays_open_ids = pd.read_csv(OPEN_REQUEST_IDS_FNAME).squeeze()

	# Reqeusts that are open can change, so we need to grab all the currently open
	# requests for consideration for UPSERT into whatever DB it ultimately lands in
	todays_open = get_todays_open_requests()

	todays_open_ids = [request[REQUEST_ID] for request in todays_open]

	# The only closed requests that may have changed are ones that closed today.  In order to
	# find those, we compute set difference to find requests open yesterday but not today.
	closed_today_ids_set = set(yesterdays_open_ids) - set(todays_open_ids)
	closed_today_ids = list(closed_today_ids_set) # convert to list for operations that come later

	# Extract reqeusts that were closed today, one by one.  Normally going request-by-request is
	# slow, but usually there aren't more than 50 requests that get closed on any particular day,
	# which is an acceptable volume.
	closed_today = []
	for request_id in closed_today_ids:
		try:
			url = f'{END_POINT}{REQUEST_ID_PIECE}{request_id}'
			ready_requests = make_REST_call(url)
			ready_request = ready_requests[0]
			closed_today.append(ready_request)
		except Exception as e:
			pass #TODO : error handling

	all_today_requests = todays_open + closed_today
	todays_file_name = f'{COMMON_FIELDS_CSV_BASE_NAME}-{get_today_as_string()}.csv'

	is_saved_correctly = False
	try:
		# Save to disk all the fields that are common/shared by our ReADY requests, independent of template-specific fields
		pd.DataFrame([[request[field] for field in COMMON_FIELDS] for request in all_today_requests], columns=COMMON_FIELDS)\
					 .to_csv(todays_file_name, header=COMMON_FIELDS)
		todays_ids_disk = [request[REQUEST_ID] for request in pd.read_csv(todays_file_name)]
		todays_ids_memory = [request[REQUEST_ID] for request in all_today_requests]
		is_saved_correctly = (set(todays_ids_disk) == set(todays_ids_memory))\
							 and len(set(todays_ids_disk) == len(todays_ids_disk))\
							 and len(set(todays_ids_memory)) == len(todays_ids_memory)
		# If all went well we can safely save todays open IDs for comparison to tomorrow's open IDs.
		if is_saved_correctly:
			persist_request_ids(todays_open_ids, OPEN_REQUEST_IDS_FNAME)
		else:
			pass #todo log something went wrong and, todo later: try again?
	except:
		pass #todo

# Old auth; it's unencrypted yet impossible for a bot to detect and very
# difficult to decipher by hand: Saving it for now for future ideas
def _____():
	with open('._') as _:
		return _.readline()[:20], (lambda ____: (____.seek(0), ____.readline()))(_)[1][20:]
____,___ = _____()[::-1]