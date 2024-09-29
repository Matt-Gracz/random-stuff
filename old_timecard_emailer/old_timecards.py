import mysql.connector
import csv
import smtplib
from email.message import EmailMessage
from email.mime.base import MIMEBase
from email import encoders
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from io import StringIO
from cryptography.fernet import Fernet
import base64

config = {}
# !!! Remember: do not check in the config file !!!
with open('_old_tc_config.json', 'r') as f:
    config = json.load(f)

# Generate a key with this code and store it *outside of this file in a secure location*
# Ensure to run this on a trusted system and close out of the terminal you run this
# in when you have extracted the key and encrypted credentials to the correct resources.
'''
from cryptography.fernet import Fernet


key = Fernet.generate_key()
cipher_suite = Fernet(key)

username = b'[unencrypted username]'
password = b'[unencrypted password]'

encrypted_username = cipher_suite.encrypt(username)
encrypted_password = cipher_suite.encrypt(password)
print(key+'\n'+encrypted_username+'\n'+encrypted_password)



from cryptography.fernet import Fernet


key = Fernet.generate_key()
cipher_suite = Fernet(key)

username = b'mgracz'
password = b'dummy123!#@F03aX~'

encrypted_username = cipher_suite.encrypt(username)
encrypted_password = cipher_suite.encrypt(password)
print(key)
print(encrypted_username)
print(encrypted_password)

'''
key = config['key']

# Initialize the Fernet cipher suite
cipher_suite = Fernet(key)

# Get the Base64 encoded strings
encoded_username = config['encrypted_username']
encoded_password = config['encrypted_password']

# Decode from Base64 Dont think we need mgracz 8/28/24
#encrypted_username = base64.b64decode(encoded_username)
#encrypted_password = base64.b64decode(encoded_password)

# Database connection configuration using decrypted credentials
config = {
    'user': cipher_suite.decrypt(config['encrypted_username']).decode('utf-8'),
    'password': cipher_suite.decrypt(config['encrypted_password']).decode('utf-8'),
    'host': config['host'],
    'database': config['database']
}

# SQL query to extract unposted timecards older than 60 days
query = ''''SELECT
 tc.trans_no AS `Timecard Number`
,tc.sched_date AS `Timecard Date`
,CONCAT(emp.fname, ' ', emp.lname) AS `Full Name`
,shp_per.shop AS `Shop`

FROM
ae_p_wka_e tc
LEFT JOIN ae_l_shp_d shp_per
ON  tc.multitenant_id=shp_per.multitenant_id
AND tc.shop_person=shp_per.shop_person
LEFT JOIN ae_h_emp_e emp
ON  tc.multitenant_id=emp.multitenant_id
AND tc.shop_person=emp.shop_person

WHERE
tc.sched_date < (NOW() - INTERVAL 30 DAY) AND
tc.post_flag = 'N'

ORDER BY
shp_per.shop ASC'''

# Pre-loaded dictionary mapping shop values to lists of email addresses
# Do not check in email addresses
shop_email_dict = {
    'ShopA': ['email1@example.com', 'email2@example.com'],
    'ShopB': ['email3@example.com'],
    # Add more mappings as needed
}

# Connect to the MySQL database and fetch results
try:
    connection = mysql.connector.connect(**config)
    cursor = connection.cursor(dictionary=True)

    cursor.execute(query)
    rows = cursor.fetchall()

    # Initialize a dictionary to store results by shop
    shop_dict = {}
    for row in rows:
        shop_value = row['Shop']

        if shop_value not in shop_dict:
            shop_dict[shop_value] = []

        shop_dict[shop_value].append(row)

except mysql.connector.Error as err:
    print(f"Error: {err}")
finally:
    if cursor:
        cursor.close()
    if connection:
        connection.close()

# Function to send emails with CSV attachments
def send_email(shop, recipient_emails, csv_content):
    sender_email = 'your_gmail_account@gmail.com'
    sender_password = 'your_gmail_password'  # Use app password if 2FA is enabled

    # Create the email message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = ', '.join(recipient_emails)
    msg['Subject'] = f'Sales Data for {shop}'

    # Add email body text
    body = f"Please find attached the sales data for {shop}."
    msg.attach(MIMEText(body, 'plain'))

    # Create a CSV file from the content
    part = MIMEBase('application', 'octet-stream')
    part.set_payload(csv_content.getvalue())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename="{shop}_sales_data.csv"')
    msg.attach(part)

    # Send the email using Gmail's SMTP server
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()  # Secure the connection
            server.login(sender_email, sender_password)
            server.send_message(msg)
            print(f"Email sent to {recipient_emails} for shop {shop}.")
    except Exception as e:
        print(f"Failed to send email to {recipient_emails} for shop {shop}. Error: {e}")

# Generate and send CSV for each shop
for shop, rows in shop_dict.items():
    if shop in shop_email_dict:
        recipient_emails = shop_email_dict[shop]

        # Create a CSV file in memory
        csv_file = StringIO()
        csv_writer = csv.DictWriter(csv_file, fieldnames=rows[0].keys())
        csv_writer.writeheader()
        csv_writer.writerows(rows)

        # Send the email with the CSV attachment
        send_email(shop, recipient_emails, csv_file)

        # Close the StringIO object
        csv_file.close()
    else:
        print(f"No email addresses found for shop {shop}.")
