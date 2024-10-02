import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import keyring
import json
import os
import logging
import urllib
import requests

# Global variables for the program
PROGRAM_NAME = "ReAPI Hub"
SETTINGS_FILE = "reapi_hub_settings.json"
# Default values for settings
DEFAULT_SETTINGS = {
    "endpoint": "",
    "serverName": "",
    "fetchTimeout": 30,
    "dateFormat": "%Y-%m-%d",
    "loggingLevel": "INFO",
    "outputFilePath": ".",
    "outputFileName": "reapi_hub_export.csv",
    "logFilePath": ".",
    "logFileName": "reapi_hub_app_log.txt",
    "outputFileDelimiter": ",",
    "numberOfRetries": 2
}
TEMPLATE_FILE = "reapi_hub_templates.json"

# Set up the logger
logger = logging.getLogger(PROGRAM_NAME)
logger.setLevel(logging.INFO)  # This will be set dynamically from settings
log_handler = logging.FileHandler("reapi_hub_app_log.txt")
log_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(log_handler)

# Set columns for UI preview of fetched ready reqeust data
preview_columns = ["requestId", "template", "dateCreated", "title", "closed", "requestor"]

# Global for storing the parameter configuration (to be persisted/loaded)
param_config = {
    "closed": None,
    "stuck": None,
    "startDate": None,
    "endDate": None,
    "template": None,
    "limit": None,
    "title": None,
    "requestor": None
}
def save_param_config():
    """Persists the parameter configuration to a file."""
    with open(PARAM_CONFIG_FILE, "w") as f:
        json.dump(param_config, f)
    logger.info("Parameter configuration saved.")

def load_param_config():
    """Loads parameter configuration from a file."""
    global param_config
    if not PARAM_CONFIG_FILE or not os.path.exists(PARAM_CONFIG_FILE):
        logger.warning("No parameter configuration found to load.")
        return
    with open(PARAM_CONFIG_FILE, "r") as f:
        param_config = json.load(f)
    logger.info("Parameter configuration loaded.")

def get_creds():
    return keyring.get_password(PROGRAM_NAME, "username"), keyring.get_password(PROGRAM_NAME, "password")

# In-memory dictionary to store templates and their values
templates = {}

# In-memory settings
settings = DEFAULT_SETTINGS.copy()

# In-mwemory store of most recent API call
in_memory_requests = {}

class CredentialManager:
    """Manages user credentials for the application."""
    def __init__(self, root):
        self.root = root
        self.root.title(f"{PROGRAM_NAME} - Credential Manager")
        self.root.geometry("300x140")

        self.usernameLabel = tk.Label(root, text="Username:")
        self.usernameLabel.grid(row=0, column=0, padx=10, pady=5)
        self.usernameEntry = tk.Entry(root, show="*")
        self.usernameEntry.grid(row=0, column=1, padx=10, pady=5)

        self.passwordLabel = tk.Label(root, text="Password:")
        self.passwordLabel.grid(row=1, column=0, padx=10, pady=5)
        self.passwordEntry = tk.Entry(root, show="*")
        self.passwordEntry.grid(row=1, column=1, padx=10, pady=5)

        self.persistButton = tk.Button(root, text="Persist and continue...", command=self.persistCredentials)
        self.persistButton.grid(row=2, column=0, padx=10, pady=5)

        self.unpersistButton = tk.Button(root, text="Unpersist", command=self.unpersistCredentials, state=tk.DISABLED)
        self.unpersistButton.grid(row=2, column=1, padx=10, pady=5)

        self.quitButton = tk.Button(root, text="Quit", command=self.quitApplication)
        self.quitButton.grid(row=3, column=0, padx=10, pady=5)

        self.checkExistingCredentials()

    def quitApplication(self):
        """Quits both applications entirely"""
        self.root.destroy()
        root.destroy()

    def checkExistingCredentials(self):
        """Checks if credentials already exist."""
        username, password = get_creds()
        if username or password:
            self.unpersistButton.config(state=tk.NORMAL)

    def persistCredentials(self):
        """Persists the entered credentials."""
        username = self.usernameEntry.get()
        password = self.passwordEntry.get()
        if username and password:
            keyring.set_password(PROGRAM_NAME, "username", username)
            keyring.set_password(PROGRAM_NAME, "password", password)
            messagebox.showinfo("Success", "Credentials persisted successfully!")
            self.openMainApp()
        else:
            messagebox.showwarning("Warning", "Please enter both username and password.")

    def unpersistCredentials(self):
        """Removes the persisted credentials."""
        keyring.delete_password(PROGRAM_NAME, "username")
        keyring.delete_password(PROGRAM_NAME, "password")
        self.unpersistButton.config(state=tk.DISABLED)
        messagebox.showinfo("Success", "Credentials removed successfully!")

    def openMainApp(self):
        """Opens the main application windows."""
        self.root.destroy()
        openSettingsWindow()
        openMainWindow()

def openSettingsWindow():
    """Opens the settings window."""
    global settingsWindow
    settingsWindow = tk.Tk()
    settingsWindow.title(f"{PROGRAM_NAME} - Settings")
    settingsWindow.geometry("625x250")

    menuBar = tk.Menu(settingsWindow)
    windowMenu = tk.Menu(menuBar, tearoff=0)
    windowMenu.add_command(label="Open ReAPI Main Application Window...", command=openMainWindow)
    windowMenu.add_command(label="Open Template Manager...", command=openTemplateManager)
    windowMenu.add_separator()
    windowMenu.add_command(label="Close Settings", command=settingsWindow.destroy)
    menuBar.add_cascade(label="Window", menu=windowMenu)
    settingsWindow.config(menu=menuBar)

    # Layout settings in a grid
    def selectOutputFolder():
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            settings["outputFilePath"] = folder_selected
            outputFilePathEntry.delete(0, tk.END)
            outputFilePathEntry.insert(0, settings["outputFilePath"])

    def selectLogFolder():
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            settings["logFilePath"] = folder_selected
            logFilePathEntry.delete(0, tk.END)
            logFilePathEntry.insert(0, settings["logFilePath"])

    labels = [
        "Endpoint:", "Server Name:", "Timeout Tolerance (sec):", "Date Format:", 
        "Logging Level:", tk.Button(settingsWindow, text="Select Output Folder", command=selectOutputFolder),
        "Output File Name:", tk.Button(settingsWindow, text="Select Log Folder", command=selectLogFolder), 
        "Log File Name:", "Output File Delimiter:", "Number of Retries:"
    ]
    entries = [
        tk.Entry(settingsWindow),  # endpoint
        tk.Entry(settingsWindow),  # serverName
        tk.Entry(settingsWindow),  # fetchTimeout
        tk.Entry(settingsWindow),  # dateFormat
        tk.StringVar(settingsWindow),  # loggingLevel
        tk.Entry(settingsWindow),  # outputFilePath
        tk.Entry(settingsWindow),  # outputFileName
        tk.Entry(settingsWindow),  # logFilePath
        tk.Entry(settingsWindow),  # logFileName
        tk.Entry(settingsWindow),  # outputFileDelimiter
        tk.Entry(settingsWindow)   # numberOfRetries
    ]
    for i, (label, entry) in enumerate(zip(labels, entries)):
        if isinstance(label, tk.Button):
            label.grid(row=i//2, column=(i%2)*2, padx=10, pady=5, sticky="e")
        else:
            tk.Label(settingsWindow, text=label).grid(row=i//2, column=(i%2)*2, padx=10, pady=5, sticky="e")
        if isinstance(entry, tk.StringVar):
            entry.set(settings["loggingLevel"])
            tk.OptionMenu(settingsWindow, entry, "INFO", "DEBUG", "ERROR").grid(row=i//2, column=(i%2)*2+1, padx=10, pady=5)
        else:
            entry.grid(row=i//2, column=(i%2)*2+1, padx=10, pady=5)

    global endpointEntry, serverNameEntry, fetchTimeoutEntry, dateFormatEntry
    global loggingLevelEntry, outputFilePathEntry, outputFileNameEntry, logFilePathEntry
    global logFileNameEntry, outputFileDelimiterEntry, numberOfRetriesEntry

    endpointEntry, serverNameEntry, fetchTimeoutEntry, dateFormatEntry,\
    loggingLevelEntry, \
    outputFilePathEntry, outputFileNameEntry, logFilePathEntry,\
    logFileNameEntry, outputFileDelimiterEntry, numberOfRetriesEntry = entries

    saveButton = tk.Button(settingsWindow, text="Persist Settings to Disk", command=saveSettings)
    saveButton.grid(row=7, column=0, padx=10, pady=5)

    loadButton = tk.Button(settingsWindow, text="Load Settings from Disk...", command=loadSettings)
    loadButton.grid(row=7, column=1, padx=10, pady=5)

    resetButton = tk.Button(settingsWindow, text="Reset Settings to Default", command=resetSettings)
    resetButton.grid(row=7, column=2, padx=10, pady=5)

    resetCredentialsButton = tk.Button(settingsWindow, text="Reset Credentials...", command=resetCredentials)
    resetCredentialsButton.grid(row=7, column=3, padx=10, pady=5)

    setDefaultValues()
    loadSettingsOnStartup()

    settingsWindow.mainloop()

def resetCredentials():
    """Resets the credentials by bringing up the Credential Manager."""
    if messagebox.askyesno("Confirm", "Are you sure you want to reset credentials?"):
        settingsWindow.destroy()
        root = tk.Tk()
        app = CredentialManager(root)
        root.mainloop()

def openMainWindow():
    """Main application window."""

    def fetchData():
        """Fetches data based on the parameter configuration."""
        # Collect the selected parameters based on the checkboxes
        selectedParams = {}
        for param, checkboxVar in checkboxVars.items():
            if checkboxVar.get():  # Only include params with checked checkboxes
                selectedParams[param] = paramEntries[param].get()
        param_url_component = urllib.parse.urlencode(selectedParams)
        # +settings['serverName'] may not be do-able/feasible for all campuses
        full_api_url = settings['endpoint']+param_url_component
        raw_data = {}
        for i in range(settings['numberOfRetries']):
            try:
                response = requests.get(
                                        full_api_url,
                                        timeout=settings['fetchTimeout'],
                                        auth=get_creds()
                                        )
                logger.info(f'Fetch successful - result is {response.status_code}')
                status = response.status_code
                if 200 <= status <= 399 and response.headers['Content-type'] == 'application/json':
                    raw_data = response.json()
                # Limit GUI to 100 entries and just the template-agnostic columns
                preview_entries = [ {key:entry[key]} for key in preview_columns for entry in raw_data[:100] ]
                # Display the preview in the results table
                updateResultsTable(preview_entries)


                # # Simulate fetching data
                # fetchResult = [{"requestId": "1234", "template": "Heating Plant Request", "dateCreated": "2024-01-12",
                #                  "title": "FIX A SINK", "closed": "false", "requestor": "dude@a.com"},
                #                 {"requestId": "43353", "template": "Digger Request", "dateCreated": "2022-05-15",
                #                  "title": "do something else", "closed": "true", "requestor": "otherGuy@where.com"}]
                global in_memory_requests
                in_memory_requests = raw_data
            except:
                logger.error(f'Error fetching for url {full_api_url} on try {i}')
        
    def updateResultsTable(data):
        """Populates the results table with fetched data."""
        for row in resultsTable.get_children():
            resultsTable.delete(row)
        
        for i, rowData in enumerate(data):
            resultsTable.insert("", "end", values=list(rowData.values()))
    
    def persistFetchedData():
        """Persist fetched data (stub function)."""
        logger.info("Persisting fetched data to disk.")
        # Here would be the logic to save the fetched data

    def persistParams():
        """Save the current parameter configuration."""
        saveParamConfig()

    def loadParams():
        """Load parameter configuration from a file."""
        loadParamConfig()
        # Update the UI with loaded params
        for param, value in paramConfig.items():
            paramEntries[param].delete(0, tk.END)
            paramEntries[param].insert(0, value)

    def clearParams():
        """Clear all parameter entries and checkboxes."""
        for paramEntry in paramEntries.values():
            paramEntry.delete(0, tk.END)
        for checkboxVar in checkboxVars.values():
            checkboxVar.set(0)

    def openCustomFieldSelector():
        """Opens the Custom Field Selector window (stub)."""
        customFieldWindow = tk.Toplevel(mainWindow)
        customFieldWindow.title("Custom Field Selector")
        tk.Label(customFieldWindow, text="This is the Custom Field Selector window (stub)").pack()

    def openJobManager():
        """Opens the Job Manager window (stub)."""
        jobManagerWindow = tk.Toplevel(mainWindow)
        jobManagerWindow.title("Job Manager")
        tk.Label(jobManagerWindow, text="This is the Job Manager window (stub)").pack()

    # Main window setup
    mainWindow = tk.Tk()
    mainWindow.title("ReAPIHub - Main Application")
    mainWindow.geometry("1400x350")

    # Create the menu bar
    menubar = tk.Menu(mainWindow)
    windowMenu = tk.Menu(menubar, tearoff=0)
    windowMenu.add_command(label="Open Settings...", command=openSettingsWindow)
    windowMenu.add_command(label="Open Template Manager...", command=openTemplateManager)
    windowMenu.add_separator()
    windowMenu.add_command(label="Close Main Application", command=mainWindow.quit)
    menubar.add_cascade(label="Window", menu=windowMenu)
    mainWindow.config(menu=menubar)

    # API Tools section
    apiToolsFrame = tk.Frame(mainWindow)
    apiToolsFrame.pack(side=tk.LEFT, anchor="nw")#padx=10, pady=10)

    # Parameter section with checkboxes and entries
    paramNames = ["closed", "stuck", "startDate", "endDate", "template", "limit", "title", "requestor"]
    paramEntries = {}
    checkboxVars = {}

    for i, param in enumerate(paramNames):
        checkboxVars[param] = tk.IntVar()
        checkbox = tk.Checkbutton(apiToolsFrame, variable=checkboxVars[param])
        checkbox.grid(row=i, column=0, sticky="w")
        label = tk.Label(apiToolsFrame, text=param)
        label.grid(row=i, column=1, padx=5)
        paramEntry = tk.Entry(apiToolsFrame)
        paramEntry.grid(row=i, column=2, padx=5)
        paramEntries[param] = paramEntry

    # API Tools action buttons
    fetchDataButton = tk.Button(apiToolsFrame, text="Fetch Data", command=fetchData, bg="purple")
    fetchDataButton.grid(row=0, column=3, padx=10, pady=5)

    persistFetchedDataButton = tk.Button(apiToolsFrame, text="Persist Fetched Data", command=persistFetchedData, bg="green")
    persistFetchedDataButton.grid(row=1, column=3, padx=10, pady=5)

    customFieldSelectorButton = tk.Button(apiToolsFrame, text="Custom Field Selector...", command=openCustomFieldSelector, bg="cyan")
    customFieldSelectorButton.grid(row=2, column=3, padx=10, pady=5)

    persistFieldSelectionButton = tk.Button(apiToolsFrame, text="Persist Field Selection", command=lambda: logger.info("Persisting field selection"), bg="blue")
    persistFieldSelectionButton.grid(row=3, column=3, padx=10, pady=5)

    openJobManagerButton = tk.Button(apiToolsFrame, text="Open Job Manager...", command=openJobManager, bg="orange")
    openJobManagerButton.grid(row=4, column=3, padx=10, pady=5)

    # Buttons to persist/load params
    persistParamsButton = tk.Button(apiToolsFrame, text="Persist Params", command=persistParams)
    persistParamsButton.grid(row=10, column=0, padx=5, pady=5)

    loadParamsButton = tk.Button(apiToolsFrame, text="Load Params", command=loadParams)
    loadParamsButton.grid(row=10, column=1, padx=5, pady=5)

    clearParamsButton = tk.Button(apiToolsFrame, text="Clear Params", command=clearParams)
    clearParamsButton.grid(row=10, column=2, padx=5, pady=5)

    # Results section
    resultsFrame = tk.Frame(mainWindow)
    resultsFrame.pack(side=tk.TOP, padx=10, pady=10, fill=tk.BOTH, expand=True)

    resultsTable = ttk.Treeview(resultsFrame, columns=preview_columns, show="headings")
    for col in columns:
        resultsTable.heading(col, text=col)
        resultsTable.column(col, width=120)
    resultsTable.pack(fill=tk.BOTH, expand=True)

    # Logging console (using ScrolledText)
    consoleFrame = tk.Frame(mainWindow)
    consoleFrame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
    logConsole = ScrolledText(consoleFrame, height=5)
    logConsole.pack(fill=tk.BOTH, expand=True)

    # Stub for logging to console
    def logToConsole(message):
        logConsole.insert(tk.END, f"{message}\n")
        logConsole.see(tk.END)  # Auto-scroll to the bottom

    # Example of using the logging to console
    logger.info("Main application window loaded.")
    logToConsole("ReAPIHub Log [INFO] Main application window loaded.")

    mainWindow.mainloop()

def saveSettings():
    """Saves the settings to a file."""
    settings.update({
        "endpoint": endpointEntry.get(),
        "serverName": serverNameEntry.get(),
        "fetchTimeout": fetchTimeoutEntry.get(),
        "dateFormat": dateFormatEntry.get(),
        "loggingLevel": loggingLevelEntry.get(),
        "outputFilePath": settings["outputFilePath"],
        "outputFileName": outputFileNameEntry.get(),
        "logFilePath": settings["logFilePath"],
        "logFileName": logFileNameEntry.get(),
        "outputFileDelimiter": outputFileDelimiterEntry.get(),
        "numberOfRetries": numberOfRetriesEntry.get()
    })
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)
    messagebox.showinfo("Success", "Settings persisted to disk successfully!")

def loadSettings():
    """Loads the settings from a file."""
    filePath = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
    if filePath:
        with open(filePath, "r") as f:
            loaded_settings = json.load(f)
        settings.update(loaded_settings)
        applySettings()

def loadSettingsOnStartup():
    """Loads the settings from the default settings file if it exists."""
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            loaded_settings = json.load(f)
        settings.update(loaded_settings)
        applySettings()

def applySettings():
    """Applies the settings to the UI elements."""
    endpointEntry.delete(0, tk.END)
    endpointEntry.insert(0, settings.get("endpoint", DEFAULT_SETTINGS["endpoint"]))
    serverNameEntry.delete(0, tk.END)
    serverNameEntry.insert(0, settings.get("serverName", DEFAULT_SETTINGS["serverName"]))
    fetchTimeoutEntry.delete(0, tk.END)
    fetchTimeoutEntry.insert(0, settings.get("fetchTimeout", DEFAULT_SETTINGS["fetchTimeout"]))
    dateFormatEntry.delete(0, tk.END)
    dateFormatEntry.insert(0, settings.get("dateFormat", DEFAULT_SETTINGS["dateFormat"]))
    loggingLevelEntry.set(settings.get("loggingLevel", DEFAULT_SETTINGS["loggingLevel"]))
    outputFilePathEntry.delete(0, tk.END)
    outputFilePathEntry.insert(0, settings.get("outputFilePath", DEFAULT_SETTINGS["outputFilePath"]))
    outputFileNameEntry.delete(0, tk.END)
    outputFileNameEntry.insert(0, settings.get("outputFileName", DEFAULT_SETTINGS["outputFileName"]))
    logFilePathEntry.delete(0, tk.END)
    logFilePathEntry.insert(0, settings.get("logFilePath", DEFAULT_SETTINGS["logFilePath"]))
    logFileNameEntry.delete(0, tk.END)
    logFileNameEntry.insert(0, settings.get("logFileName", DEFAULT_SETTINGS["logFileName"]))
    outputFileDelimiterEntry.delete(0, tk.END)
    outputFileDelimiterEntry.insert(0, settings.get("outputFileDelimiter", DEFAULT_SETTINGS["outputFileDelimiter"]))
    numberOfRetriesEntry.delete(0, tk.END)
    numberOfRetriesEntry.insert(0, settings.get("numberOfRetries", DEFAULT_SETTINGS["numberOfRetries"]))

def resetSettings():
    """Resets the settings to default values."""
    settings.update(DEFAULT_SETTINGS)
    applySettings()
    messagebox.showinfo("Success", "Settings reset to default values!")

def setDefaultValues():
    """Sets the default values for the settings."""
    settings.update(DEFAULT_SETTINGS)
    applySettings()

def loadTemplates():
    """Loads templates from the JSON file into the in-memory dictionary."""
    global templates
    if os.path.exists(TEMPLATE_FILE):
        with open(TEMPLATE_FILE, "r") as f:
            templates = json.load(f)
    else:
        templates = {}

def saveTemplates():
    """Saves the in-memory templates dictionary to the JSON file."""
    with open(TEMPLATE_FILE, "w") as f:
        json.dump(templates, f)

def parseTemplate(filePath):
    """Parses a template file to extract values and additionalFieldValues."""
    with open(filePath, "r") as f:
        templateData = json.load(f).get("requestTemplate")
    
    templateName = templateData.get("templateName", "Unnamed Template")
    values = templateData.get("values", {})
    additionalFields = templateData.get("additionalFieldsValues", {})
    
    templates[templateName] = {**values, **additionalFields}

def openTemplateManager():
    """Opens the template manager window using a Listbox for multiselection."""

    def refreshTemplateList():
        """Refreshes the list of templates displayed in the Listbox."""
        templateListBox.delete(0, tk.END)  # Clear the listbox
        for templateName in templates.keys():
            templateListBox.insert(tk.END, templateName)  # Add each template to the listbox

    def deleteSelectedTemplates():
        """Deletes the selected templates."""
        selected_templates = list(templateListBox.curselection())  # Get indices of selected templates
        if not selected_templates:
            messagebox.showwarning("No Selection", "Please select at least one template to delete.")
            return
        
        toDelete = [templateListBox.get(i) for i in selected_templates]
        for name in toDelete:
            del templates[name]  # Delete from templates dictionary
        
        saveTemplates()  # Persist the changes
        refreshTemplateList()  # Refresh the list after deletion

    def selectAll():
        """Selects all items in the Listbox."""
        templateListBox.select_set(0, tk.END)

    def deselectAll():
        """Deselects all items in the Listbox."""
        templateListBox.select_clear(0, tk.END)

    def uploadTemplate():
        """Uploads a new template."""
        filePath = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if filePath:
            parseTemplate(filePath)  # Parse the uploaded template
            saveTemplates()  # Save the new template to file
            refreshTemplateList()  # Refresh the UI to display the new template

    # Create the template manager window
    templateManagerWindow = tk.Tk()
    templateManagerWindow.title("Template Manager")
    templateManagerWindow.geometry("415x300")
    templateManagerWindow.attributes("-topmost", True) # Don't let users mess with other parts of the app

    # Load the templates from the file when the window opens
    loadTemplates()

    # Create the Listbox for displaying templates with multiple selection enabled
    templateListBox = tk.Listbox(templateManagerWindow, selectmode=tk.MULTIPLE, activestyle="dotbox")
    templateListBox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # Create buttons for managing templates
    buttonFrame = tk.Frame(templateManagerWindow)
    buttonFrame.pack(fill=tk.X)

    uploadButton = tk.Button(buttonFrame, text="Upload Template", command=uploadTemplate)
    uploadButton.pack(side=tk.LEFT, padx=5, pady=5)

    deleteButton = tk.Button(buttonFrame, text="Delete Selected", command=deleteSelectedTemplates)
    deleteButton.pack(side=tk.LEFT, padx=5, pady=5)

    selectAllButton = tk.Button(buttonFrame, text="Select All", command=selectAll)
    selectAllButton.pack(side=tk.LEFT, padx=5, pady=5)

    deselectAllButton = tk.Button(buttonFrame, text="Deselect All", command=deselectAll)
    deselectAllButton.pack(side=tk.LEFT, padx=5, pady=5)

    closeButton = tk.Button(buttonFrame, text="Close", command=templateManagerWindow.destroy)
    closeButton.pack(side=tk.RIGHT, padx=5, pady=5)

    # Initialize the template list after loading templates
    refreshTemplateList()

    templateManagerWindow.mainloop()

def main():
    global root # mgracz - hack to allow quit buttons to kill the application
    root = tk.Tk()
    if not keyring.get_password(PROGRAM_NAME, "username") or not keyring.get_password(PROGRAM_NAME, "password"):
        app = CredentialManager(root)
        root.mainloop()
    else:
        root.destroy()
        openMainWindow()
    
if __name__ == "__main__":
    main()