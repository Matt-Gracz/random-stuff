import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import keyring
import json
import os
import logging

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

# In-memory dictionary to store templates and their values
templates = {}

# In-memory settings
settings = DEFAULT_SETTINGS.copy()

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
        username = keyring.get_password(PROGRAM_NAME, "username")
        password = keyring.get_password(PROGRAM_NAME, "password")
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
    """Opens the main application window."""
    mainWindow = tk.Tk()
    mainWindow.title(f"{PROGRAM_NAME} - Main Application")
    mainWindow.geometry("600x400")
    tk.Label(mainWindow, text="Main Application Window").grid(row=0, column=0, padx=10, pady=5)
    tk.Button(mainWindow, text="Open Settings...", command=openSettingsWindow).grid(row=0, column=1, padx=10, pady=5)
    tk.Button(mainWindow, text="Quit Application", command=mainWindow.destroy).grid(row=0, column=2, padx=10, pady=5)
    mainWindow.mainloop()
def open_main_window():
    """Main application window."""
    def fetch_data():
        """Fetches data based on the parameter configuration."""
        # Collect the selected parameters based on the checkboxes
        selected_params = {}
        for param, checkbox_var in checkbox_vars.items():
            if checkbox_var.get():  # Only include params with checked checkboxes
                selected_params[param] = param_entries[param].get()

        logger.info(f"Fetching data with params: {selected_params}")
        # Simulate fetching data
        fetch_result = [{"requestId": "1234", "template": "Heating Plant Request", "dateCreated": "2024-01-12",
                         "title": "FIX A SINK", "closed": "false", "requestor": "dude@a.com"},
                        {"requestId": "43353", "template": "Digger Request", "dateCreated": "2022-05-15",
                         "title": "do something else", "closed": "true", "requestor": "otherGuy@where.com"}]

        # Limit to 100 entries
        fetch_result = fetch_result[:100]
        # Display the results in the table
        update_results_table(fetch_result)
    
    def update_results_table(data):
        """Populates the results table with fetched data."""
        for row in results_table.get_children():
            results_table.delete(row)
        
        for i, row_data in enumerate(data):
            results_table.insert("", "end", values=list(row_data.values()))
    
    def persist_fetched_data():
        """Persist fetched data (stub function)."""
        logger.info("Persisting fetched data to disk.")
        # Here would be the logic to save the fetched data

    def persist_params():
        """Save the current parameter configuration."""
        save_param_config()

    def load_params():
        """Load parameter configuration from a file."""
        load_param_config()
        # Update the UI with loaded params
        for param, value in param_config.items():
            param_entries[param].delete(0, tk.END)
            param_entries[param].insert(0, value)

    def clear_params():
        """Clear all parameter entries and checkboxes."""
        for param_entry in param_entries.values():
            param_entry.delete(0, tk.END)
        for checkbox_var in checkbox_vars.values():
            checkbox_var.set(0)

    def open_custom_field_selector():
        """Opens the Custom Field Selector window (stub)."""
        custom_field_window = tk.Toplevel(main_window)
        custom_field_window.title("Custom Field Selector")
        tk.Label(custom_field_window, text="This is the Custom Field Selector window (stub)").pack()

    def open_job_manager():
        """Opens the Job Manager window (stub)."""
        job_manager_window = tk.Toplevel(main_window)
        job_manager_window.title("Job Manager")
        tk.Label(job_manager_window, text="This is the Job Manager window (stub)").pack()

    # Main window setup
    main_window = tk.Tk()
    main_window.title("ReAPIHub - Main Application")
    main_window.geometry("800x600")

    # Create the menu bar
    menubar = tk.Menu(main_window)
    window_menu = tk.Menu(menubar, tearoff=0)
    window_menu.add_command(label="Open Settings...")
    window_menu.add_command(label="Open Template Manager...")
    window_menu.add_separator()
    window_menu.add_command(label="Close Main Application", command=main_window.quit)
    menubar.add_cascade(label="Window", menu=window_menu)
    main_window.config(menu=menubar)

    # API Tools section
    api_tools_frame = tk.Frame(main_window)
    api_tools_frame.pack(side=tk.LEFT, padx=10, pady=10)

    # Parameter section with checkboxes and entries
    param_names = ["closed", "stuck", "startDate", "endDate", "template", "limit", "title", "requestor"]
    param_entries = {}
    checkbox_vars = {}

    for i, param in enumerate(param_names):
        checkbox_vars[param] = tk.IntVar()
        checkbox = tk.Checkbutton(api_tools_frame, variable=checkbox_vars[param])
        checkbox.grid(row=i, column=0, sticky="w")
        label = tk.Label(api_tools_frame, text=param)
        label.grid(row=i, column=1, padx=5)
        param_entry = tk.Entry(api_tools_frame)
        param_entry.grid(row=i, column=2, padx=5)
        param_entries[param] = param_entry

    # API Tools action buttons
    fetch_data_button = tk.Button(api_tools_frame, text="Fetch Data", command=fetch_data, bg="purple")
    fetch_data_button.grid(row=0, column=3, padx=10, pady=5)

    persist_fetched_data_button = tk.Button(api_tools_frame, text="Persist Fetched Data", command=persist_fetched_data, bg="green")
    persist_fetched_data_button.grid(row=1, column=3, padx=10, pady=5)

    custom_field_selector_button = tk.Button(api_tools_frame, text="Custom Field Selector...", command=open_custom_field_selector, bg="cyan")
    custom_field_selector_button.grid(row=2, column=3, padx=10, pady=5)

    persist_field_selection_button = tk.Button(api_tools_frame, text="Persist Field Selection", command=lambda: logger.info("Persisting field selection"), bg="blue")
    persist_field_selection_button.grid(row=3, column=3, padx=10, pady=5)

    open_job_manager_button = tk.Button(api_tools_frame, text="Open Job Manager...", command=open_job_manager, bg="orange")
    open_job_manager_button.grid(row=4, column=3, padx=10, pady=5)

    # Buttons to persist/load params
    persist_params_button = tk.Button(api_tools_frame, text="Persist Params", command=persist_params)
    persist_params_button.grid(row=5, column=0, padx=5, pady=5)

    load_params_button = tk.Button(api_tools_frame, text="Load Params", command=load_params)
    load_params_button.grid(row=5, column=1, padx=5, pady=5)

    clear_params_button = tk.Button(api_tools_frame, text="Clear Params", command=clear_params)
    clear_params_button.grid(row=5, column=2, padx=5, pady=5)

    # Results section
    results_frame = tk.Frame(main_window)
    results_frame.pack(side=tk.TOP, padx=10, pady=10, fill=tk.BOTH, expand=True)

    columns = ["requestId", "template", "dateCreated", "title", "closed", "requestor"]
    results_table = ttk.Treeview(results_frame, columns=columns, show="headings")
    for col in columns:
        results_table.heading(col, text=col)
        results_table.column(col, width=120)
    results_table.pack(fill=tk.BOTH, expand=True)

    # Logging console (using ScrolledText)
    console_frame = tk.Frame(main_window)
    console_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
    log_console = ScrolledText(console_frame, height=5)
    log_console.pack(fill=tk.BOTH, expand=True)

    # Stub for logging to console
    def log_to_console(message):
        log_console.insert(tk.END, f"{message}\n")
        log_console.see(tk.END)  # Auto-scroll to the bottom

    # Example of using the logging to console
    logger.info("Main application window loaded.")
    log_to_console("ReAPIHub Log [INFO] Main application window loaded.")

    main_window.mainloop()

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