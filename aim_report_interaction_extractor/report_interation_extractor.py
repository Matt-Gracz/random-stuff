'''
Title: AiM Report Interaction ETL
Purpose: To track the relative volume of AiM user report interactions throughout the day
Author :: Matt Gracz
Initially developed in Spring/Summer of 2024.
This code extracts AiM report interaction data from server log files, with each report interaction defined as the act of an AiM user running a report via the report manager in AiM. We model a single run of a report as a tuple:
(report_date, report_time, report_id), where report_date and report_time represent jointly when the report that maps
to report_id was run.  This script prepares for insertion into and formats the data it extracts for insertion as a 3 column row in a SQL database. I suggest employing an auto incrementing int as the PK.  It might be prudent to introduce a natural key of a combination of the report_id and report_date columns for quick sorting and aggregating once the table gets big enough.

The selected data types for a MySQL 8.x warehouse for the three fields we are extracting from the logs are:
 -- report_date as a DATE data type
 -- report_time as a TIME data type
 -- report_timezone as a VARCHAR data type
 -- report_id as a SMALLINT data type [small int ranges up to 32,000ish which will be more than enough for the usual AiM report ID range]


Issues:
- 2024-06-04 :: logging in GUI mode doesn't print to the terminal. Not a big deal.  Backburner.


Refer to here for the most up to date source files:
https://github.com/Matt-Gracz/random-stuff/tree/main/aim_report_interaction_extractor
'''

# Imports
import re   # we use regular expressions to process the logfile content; see bottom of the file for technical notes
from datetime import datetime # datetime module to help us format for storage in MySQL 8.x
import pandas as pd # needed for data manipulation and persistence operations
import logging # for sending debug and info output to a standard output stream
import os # to help with file handling
import traceback # for error handling
import json # to read in the config file

##### for performance testing this script
import time 
from datetime import timedelta
#####

##### For GUI
import tkinter as tk
from tkinter import messagebox, scrolledtext
import argparse
#####

# Application Config
config = None
with open('_report_interaction_etl_config.json', 'r') as config_file:
    config = json.load(config_file)
DEBUG = config["DEBUG"] # Only enable when debugging, obviously
DEBUG_LOOP_MAX = config["DEBUG_LOOP_MAX"] # max extraction loops to run before bailing manually
CLEAR_OUTPUT_UPFRONT = config["CLEAR_OUTPUT_UPFRONT"] # remove old output file from last ETL run
CLEAR_INPUT_AFTER_SUCCESS = config["CLEAR_INPUT_AFTER_SUCCESS"] # clear out the logs so they don't build up in the input dir
PERSIST_OUTPUT = config["PERSIST_OUTPUT"] # Save the output to disk; only set to false if debugging.
LOG_FILES_DIRECTORY = config['LOG_FILES_DIRECTORY'] # Where the AiM log files are stored
OUTPUT_FILE_NAME = config["OUTPUT_FILE_NAME"] # Stores the ETL'd data
FILENAME_PATTERN = config["FILENAME_PATTERN"] # The substring of a filename that denotes an AiM log file

# Constants
HEADLESS_MODE = 'headless' # Option 1: run this script without a GUI, i.e., in headless mode
GUI_MODE = 'GUI' # Option 2: run this script with the GUI, i.e., in GUI mode
# Note to reader: Documentation for this regex pattern is at the bottom of this python file
REGEX_PATTERN = r'\[([^:]+):([^s]+)\s([^\]]+).*?fmaxReportId=(\d+)'

# Setup logging
logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO, format='%(levelname)s: %(message)s')

### Functions:: There is one function per major conceptual operation this script goes through.  See below for details

## Step 1: Get a list of the full paths to all the input files to process
def retrieve_log_file_paths(directory):
    return [os.path.join(directory, f) for f in os.listdir(directory) if FILENAME_PATTERN in f]

## Step 2: Optionally delete the old output file to ensure stale file deletion even if the ETL fails
def clear_output(output_file):
    if CLEAR_OUTPUT_UPFRONT:
        try:
            if os.path.exists(output_file):
                os.remove(output_file)
                logging.info('Output file cleared.')
            else:
                logging.info('Output file does not exist.')
        except Exception as e:
            logging.error(f'Error removing output file: {str(e)}')
            # Issue a question to the user todo put in GUI mgracz
            key = input('Issue removing the output file. Continue anyway? (Y/N): ')
            if key.lower() != 'y':
                logging.info('Stopping the script.')
                exit()

## Step 3: The actual ETL routine. Returns a pandas DataFrame containing one row per report interaction to extract from the input files.
def extract_report_interactions(file_paths):
    raw_interactions = [] # init in-memory the extracted raw data
    line_count = 0 # use this to track performance metrics
    debug_loop = 0 # track which iteration of the loop we're in
    start_time = time.time() # performance tracking
    
    for file_path in file_paths:
        with open(file_path, 'r') as log_file:
            for line in log_file:
                if DEBUG and debug_loop >= DEBUG_LOOP_MAX:
                    break
                try:
                    line_count += 1
                    matches = re.search(REGEX_PATTERN, line)
                    if matches and len(matches.groups()) == 4:
                        date_str, time_str, timezone, report_id = matches.groups() # this extracts the raw data
                        print(date_str, time_str, timezone, report_id)
                        # Extract date and time components and store them in 
                        # a MySQL 8.x friendly format.
                        report_date = datetime.strptime(date_str, '%d/%b/%Y').strftime('%Y-%m-%d')
                        report_time = datetime.strptime(time_str, '%H:%M:%S').strftime('%H:%M:%S')
                        report_timezone = timezone.strip() # lop off any whitespace; otherwise we just want it as a raw string
                        # report_id doesn't need to be cast to int since we're saving to CSV
                        raw_interactions.append([report_date, report_time, report_timezone, report_id])
                        if DEBUG:
                            logging.debug(f'Extracted: {report_date}, {report_time}, {report_id}')
                        debug_loop += 1
                except Exception as e:
                    logging.error(f'Error processing line: {str(e)}\nTraceback: {traceback.format_exc()}')
    
    elapsed_time = str(timedelta(seconds=time.time() - start_time))
    # A note on some uncommon syntax in the formatted string: The signifier of a colon followed by a comma after a an int or float, like line_count:, forces commas into big numbers being printed. E.g., 10,000 instead of 10000
    logging.info(f'Extracted {len(raw_interactions):,} report interactions from {line_count:,} lines in {elapsed_time}')
    return pd.DataFrame(raw_interactions, columns=['report_date', 'report_time', 'report_timezone', 'report_id'])

## Step 4: optionally persist the output to disk
def save_output_to_disk(data_frame, output_file):
    if PERSIST_OUTPUT:
        try:
            # index=False means it won't persist an extra column with integer indexes.  We don't need them.
            data_frame.to_csv(output_file, index=False)
            if os.path.exists(output_file):
                logging.info('Output file successfully saved.')
            else:
                logging.error('Error saving output file to disk.')
        except Exception as e:
            logging.error(f'Error saving CSV: {str(e)}, {traceback.format_exc()}')

## Step 5: Optionally clear out the input log files, since there can be a lot of them.
def clear_input_files(file_paths):
    if CLEAR_INPUT_AFTER_SUCCESS:
        for file_path in file_paths:
            try:
                os.remove(file_path)
                if os.path.exists(file_path):
                    logging.warning(f'Failed to remove {file_path}')
            except Exception as e:
                logging.error(f'Error removing file {file_path}: {str(e)}')
        logging.info('Attempted to delete input files.')

# GUI
# We use the tkinter library to develop the UI. It's mostly self explanatory.
class ETLApp:
    def __init__(self, root):
        self.root = root
        self.root.title('AiM Report interaction ETL')
        self.root.iconbitmap('etl_icon.ico')

        # Parameters to expose to the UI
        self.params = {
            'DEBUG': tk.BooleanVar(value=DEBUG),
            'DEBUG_LOOP_MAX': tk.IntVar(value=DEBUG_LOOP_MAX),
            'CLEAR_OUTPUT_UPFRONT': tk.BooleanVar(value=CLEAR_OUTPUT_UPFRONT),
            'CLEAR_INPUT_AFTER_SUCCESS': tk.BooleanVar(value=CLEAR_INPUT_AFTER_SUCCESS),
            'PERSIST_OUTPUT': tk.BooleanVar(value=PERSIST_OUTPUT),
            'LOG_FILES_DIRECTORY': tk.StringVar(value=LOG_FILES_DIRECTORY),
            'OUTPUT_FILE_NAME': tk.StringVar(value=OUTPUT_FILE_NAME),
            'FILENAME_PATTERN': tk.StringVar(value=FILENAME_PATTERN)
        }

        # Create UI Elements
        self.create_ui()

    # This function sets up the entire user interface for display when the window is rendered
    def create_ui(self):
        row = 0 # the notion of rows/cols in a tkinter window are how elements are placed in a grid

        # Dynamically create UI elements for each parameter we want to expose.  Simply adjust the
        # instantiation of self.params if you want to modify that.
        for param, var in self.params.items():
            tk.Label(self.root, text=param).grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
            if isinstance(var, tk.BooleanVar):
                tk.Checkbutton(self.root, variable=var).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
            else:
                tk.Entry(self.root, textvariable=var).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
            row += 1

        # Action Function Buttons
        tk.Button(self.root, text='Retrieve Log Files', command=self.retrieve_log_file_paths).grid(row=row, column=0, padx=5, pady=5)
        tk.Button(self.root, text='Clear Output', command=self.clear_output).grid(row=row, column=1, padx=5, pady=5)
        row += 1
        tk.Button(self.root, text='Extract Report interactions', command=self.extract_report_interactions).grid(row=row, column=0, padx=5, pady=5)
        tk.Button(self.root, text='Save Output to Disk', command=self.save_output_to_disk).grid(row=row, column=1, padx=5, pady=5)
        row += 1
        tk.Button(self.root, text='Clear Input Files', command=self.clear_input_files).grid(row=row, column=0, padx=5, pady=5)
        tk.Button(self.root, text='Show Logs', command=self.show_logs).grid(row=row, column=1, padx=5, pady=5)
        row += 1
        tk.Button(self.root, text='Exit', command=self.root.destroy).grid(row=row, column=0, columnspan=2, padx=5, pady=5)


    # Action Functions
    def retrieve_log_file_paths(self):
        paths = retrieve_log_file_paths(self.params['LOG_FILES_DIRECTORY'].get())
        messagebox.showinfo('Log File Paths', '\n'.join(paths))

    def clear_output(self):
        clear_output(self.params['OUTPUT_FILE_NAME'].get())

    def extract_report_interactions(self):
        log_file_paths = retrieve_log_file_paths(self.params['LOG_FILES_DIRECTORY'].get())
        df = extract_report_interactions(log_file_paths)
        self.report_interactions_df = df
        messagebox.showinfo('Extract Report interactions', f'Extracted {len(df)} records.')

    def save_output_to_disk(self):
        if hasattr(self, 'report_interactions_df'):
            save_output_to_disk(self.report_interactions_df, self.params['OUTPUT_FILE_NAME'].get())
            messagebox.showinfo('Save Output', 'Output file successfully saved.')
        else:
            messagebox.showwarning('Save Output', 'No data to save. Extract report interactions first.')

    def clear_input_files(self):
        log_file_paths = retrieve_log_file_paths(self.params['LOG_FILES_DIRECTORY'].get())
        clear_input_files(log_file_paths)

    def show_logs(self):
        log_window = tk.Toplevel(self.root)
        log_window.title('Logs')
        log_text = scrolledtext.ScrolledText(log_window, width=100, height=30)
        log_text.pack(padx=10, pady=10)
        with open('logfile.log', 'r') as log_file:
            log_text.insert(tk.END, log_file.read())
        log_text.config(state=tk.DISABLED)

##### END GUI Code

# ::::: Application Root :::::
# There are two ways to run this script, both from command line:
# 1. Headless mode | simply run the script
# 2. GUI mode      | run the script with a -u or --ui option. I.e., %run report_interaction_extractor.py -u

def main():
    # Command-Line Argument Parsing
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--ui', action='store_true', help=''''\
        Call without args to run in headless mode.  Call with -u or --ui to the launch the GUI''')
    args = parser.parse_args() # fill the args variable with symbols based on the cmd line args
    mode = GUI_MODE if (args.ui == True) else HEADLESS_MODE # not necessary to compare to True but done for readability
    logging.info(f'Running the script in {mode} mode at {datetime.now().strftime("%Y-%m-%d %H:%M")}')

    if mode == GUI_MODE: # true iff -u or --ui was passed in to the script
        # Fire up the UI
        root = tk.Tk()
        app = ETLApp(root)
        root.mainloop()
    else:
        # Running the script in headless mode
        log_file_paths = retrieve_log_file_paths(LOG_FILES_DIRECTORY)
        clear_output(os.path.join(LOG_FILES_DIRECTORY, OUTPUT_FILE_NAME))
        report_interactions_df = extract_report_interactions(log_file_paths)
        save_output_to_disk(report_interactions_df, os.path.join(LOG_FILES_DIRECTORY, OUTPUT_FILE_NAME))
        clear_input_files(log_file_paths)
        logging.info('Script execution completed.')

if __name__ == '__main__':
    main()


r'''
::::: Documentation of the employment of regex in this script :::::

Due to the textual nature of the logfile data, and therefore to ensure
good performance and reliability of the data extraction, we employ a
regex pattern to capture the datetime of when a given report was run,
along with its corresponding report ID.  The regex pattern is:

            \[([^:]+):([^s]+)\s([^\]]+).*?fmaxReportId=(\d+)

An important term in the regex world is 'capture group', which in a
regular expression pattern is any text inside of a pair of parentheses.
The general form is ([sub_pattern]), where [sub_pattern] is any arbitrary
substring of our regex pattern.  The parentheses indicate to the regex
engine to 'capture' the part of the input string that matches the sub_pattern,
precisely so that we can use it as actual data later.  Each pair of parens
is a different capture group, and you can have 0 to an arbitrary N number
of capture groups in regex. In our case we have exactly four capture groups:
the first group captures the date of the user's interaction with the report,
the second is the time of interaction, the third is the timezone, and
the fourth is the ID of the report being interacted with.

What follows is an explanation of how this all works, by explaining each
piece of the pattern in turn, going left to right in the pattern:

                Piece 1: Capturing the date of report interaction
                            \[([^:]+)
The escaped bracket at the beggining of the pattern, \[, finds the
bracket in the logfile line that directly precedes the date.  ([^:]+) can be
read as "capture all characters that aren't a colon until you find a colon"
The reason we do this is the colon separates the date from the time in the
logfile string. The brackets [] stipulate to capture multiple characters
in a row, the caret ^ negates the colon and the + tells it to find as
many characters as it can that match the subpattern (i.e., characters 
that aren't colons) until it finds a colon.

                Piece 2: Capturing the time
                            :([^s]+)
Similarly to the date being preceded by an open bracket, we know the
time will be differentiated from the date by a colon, so we place the
colon outside of the parens to denote where to start capturing. ([^s]+) is
exactly the same logic as above, but the negation is applying to whitespace
instead of a colon.  This means the regex engine will capture everything
that is not whitepspace until it hits a space, which demarcates where
the timezone starts.

                Piece 3: Capturing the timezone
                            \s([^\]]+)
Similarly to the time being preceded by a colon, we know the timezone
will be differentiated from the time by a space, so we don't include
that space in the parens as we don't need to capture it, but we need
to tell the regex engine where to start the next capture group, which
is after the space. \s([^\]]+) is exactly the same logic as above, but
the negation is applying to a closed bracket instead of a colon.  This
means the regex engine will capture everything that is not a closed
bracket until it hits the closed bracket that delineates the end of the
datetime substring, and therefore the end of the timezone.

                Piece 4: Skipping everything until the Report ID:
                            .*?fmaxReportId=
With no parens in this part of the regex pattern we are simlpy instructing
the regex engine to skip over all the characters that match the pattern. 
In this case we skip over everything until we hit fmaxReportId= which we
also don't capture but spelling out fmaxReportId= allows the regex engine
to start the next capture group in the right spot.

                Piece 5: Capturing the Report ID
                            (\d+)
This sub-pattern captures into the second capture group all the next
digits that appear after the equals sign from the previous sub-pattern,
i.e., the report ID we're after. \d stands for "digit" and the + again
signifies to capture as many digits in a row as the regex engine can.
It stops capturing once it hits a non-digit, i.e., the end of the report
ID substring.  The rest of the line in the logfile is ignored, which is
implied simply by the regex pattern terninating at this second capture group.

'''