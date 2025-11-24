import os
import sys
import logging
from pathlib import Path

# Basisverzeichnis bestimmen (neben der EXE, wenn gefrozener PyInstaller-Build)
if getattr(sys, "frozen", False):
    base_dir = Path(sys.executable).parent
else:
    base_dir = Path(__file__).parent

log_path = base_dir / "startup.log"

logging.basicConfig(
    filename=str(log_path),
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s: %(message)s",
)

logging.debug("Vor allen Imports")
logging.debug("cwd=%s", os.getcwd())
logging.debug("executable=%s", sys.executable)
logging.debug("frozen=%s", getattr(sys, "frozen", False))

from PyQt5.QtWidgets import QApplication, QMainWindow, QActionGroup, QSizePolicy, QMessageBox
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView
import configparser

from SysMLAPI import getProjects, deleteProject
from SysMLwithLCA import SysMLLCAModel
from openLCAAPI import openLCAServer



def read_preferences():
    # Read preferences from a configuration file
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), 'preferences.ini')
    # the config file is expected to be in the same directory as this script
    config.read(config_path)

    preferences = config['DEFAULT']
    if len(preferences) == 0:
        # set default preferences
        preferences = {
            "sysmlserver": "http://localhost:9000",
            "openlcaserver": "http://localhost:8080",
            "recent_projects": ""
        }
    return preferences

def safe_preferences(preferences):
    config = configparser.ConfigParser()
    config['DEFAULT'] = preferences

    config_path = os.path.join(os.path.dirname(__file__), 'preferences.ini')
    with open(config_path, 'w') as configfile:
        config.write(configfile)
    
    pass

# create_gui() 

class MainWindow(QMainWindow):
    preferences=None
    sysmlserver=None
    openLCAServerURL=None
    theModel=None


    def __init__(self):
        super().__init__()
        self.setWindowTitle("SysML-LCA connector")
        self.preferences=read_preferences()
        # tbd: handle missing preferences
        self.sysmlserver=self.preferences["sysmlserver"]
        self.setWindowIcon(QIcon('logo.png'))
        self.openLCAServerURL=self.preferences["openlcaserver"]

        self.createMenuBar()
        # Create a QWebEngineView widget
        self.browser = QWebEngineView()
        self.setCentralWidget(self.browser)
        self.browser.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Set HTML content
        html_content = """
        <p>Click on the "Open" menu to select a project</p>
        """
        self.browser.setHtml(html_content)
        self.createStatusBar()
    
    def createStatusBar(self):
        self.statusBar().showMessage("Ready")

    def updateStatusBar(self, message):
        self.statusBar().showMessage(message)

    def clearStatusBar(self):
        self.statusBar().clearMessage()

    def select_project_dialog(self):
        project = None
        try:
            projects = getProjects(self.sysmlserver)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to get projects: {e}")
            return
        filtered_projects = projects

        dialog = QDialog(self)
        dialog.setWindowTitle("Select Project from " + self.sysmlserver)
        dialog.setGeometry(100, 100, 1000, 800)

        layout = QVBoxLayout(dialog)

        search_label = QLabel("Search")
        layout.addWidget(search_label)

        search_entry = QLineEdit()
        layout.addWidget(search_entry)

        project_listbox = QListWidget()
        for project in filtered_projects:
            project_listbox.addItem(project["name"])
        layout.addWidget(project_listbox)

        button_layout = QHBoxLayout()
        select_button = QPushButton("Open")
        synchronize_button = QPushButton("Synchronize with openLCA")
        delete_button = QPushButton("Delete")
        button_layout.addWidget(select_button)
        button_layout.addWidget(synchronize_button)
        button_layout.addWidget(delete_button)
        layout.addLayout(button_layout)

        def search_projects():
            search_term = search_entry.text().lower()
            project_listbox.clear()
            nonlocal filtered_projects
            nonlocal projects
            filtered_projects = [project for project in projects if (project["name"] is not None and search_term in project["name"].lower())]
            for project in filtered_projects:
                project_listbox.addItem(project["name"])

        search_entry.textChanged.connect(search_projects)

        def select_project():
            index = project_listbox.currentRow()
            project = filtered_projects[index]
            dialog.accept()
            self.open_project(project)
            return project
        
        def synchronize_project():
            index = project_listbox.currentRow()
            project = filtered_projects[index]
            dialog.accept()
            self.open_project(project)
            self.synchronizeProcesses()
            return project

        def delete_project():
            index = project_listbox.currentRow()
            project = filtered_projects[index]
            dialog.accept()
            try :
                deleteProject(self.sysmlserver, project['@id'])
                print("project deleted: ", project)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete project: {e}")
                print(f"Failed to delete project: {e}")

        select_button.clicked.connect(select_project)
        synchronize_button.clicked.connect(synchronize_project)
        delete_button.clicked.connect(delete_project)

        dialog.exec_()
        pass

    def projectFromString(self,project):
        name=project.split("(")[0].strip() # everything before the first ( is the name
        uuid = project.split("(")[-1].strip(")") # everything in between () is the uuid
        theProject = {"@id": uuid, "name": name }
        return theProject

    def update_recent_projects_menu(self):
        self.recent_projects_menu.clear()
        recent_projects = self.preferences.get("recent_projects", "").split(",")
        for project in recent_projects:
            if project:
                self.recent_projects_menu.addAction(project, lambda proj=project: self.open_project(self.projectFromString(proj)))

    def update_recent_projects(self, uuid, name):
        recent_projects = self.preferences.get("recent_projects", "").split(",")
        recent_projects = [proj for proj in recent_projects if proj]
        # remove the project if it already exists
        recent_projects = [proj for proj in recent_projects if uuid not in proj]
        
        recent_projects.insert(0, f"{name} ({uuid})")
        
        self.preferences["recent_projects"] = ",".join(recent_projects[:3])
        safe_preferences(self.preferences)
        self.update_recent_projects_menu()

    def open_project(self, theProject):
        self.updateStatusBar(f"Opening project {theProject['name']}")
        # tbd: is not updated WTF
        print(f"Opening project {theProject['name']}")
        self.theModel= SysMLLCAModel(self.sysmlserver, theProject['@id'])
        self.update_recent_projects(theProject['@id'],theProject['name'])
        self.setWindowTitle(f"{self.theModel.name} - SysML Life cycle analyzer")
        self.set_SysML_Model_view()
        self.updateStatusBar("Ready")
        pass
    
    recent_projects_menu=None

    def createMenuBar(self):
        menu_bar = self.menuBar()

        # Create a file menu
        file_menu = menu_bar.addMenu("File")
        open_action = file_menu.addAction("Open")
        open_action.triggered.connect(self.select_project_dialog)
        save_action = file_menu.addAction("Save")
        recent_projects_menu = file_menu.addMenu("Recent Projects")
        self.recent_projects_menu = recent_projects_menu
        preferences_action = file_menu.addAction("Preferences")
        preferences_action.triggered.connect(self.open_preferences_dialog)
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)

        self.update_recent_projects_menu()

        # Create an edit menu
        edit_menu = menu_bar.addMenu("Edit")
        cut_action = edit_menu.addAction("Cut")
        copy_action = edit_menu.addAction("Copy")
        paste_action = edit_menu.addAction("Paste")
        copy_all_action = edit_menu.addAction("Copy all")
        copy_all_action.triggered.connect(self.copyAll)
        search_action = edit_menu.addAction("Search")
        search_action.triggered.connect(self.search_textbox)

        # Create a run menu
        run_menu = menu_bar.addMenu("Run")
        synchronize_action = run_menu.addAction("synchronize")
        synchronize_action.triggered.connect(self.synchronizeProcesses)

        # Create a view menu
        view_menu = menu_bar.addMenu("View")
      
        self.sysml_model_action = view_menu.addAction("SysML Model")
        self.sysml_model_action.setCheckable(True)
        self.sysml_model_action.setChecked(True)
        self.sysml_model_action.triggered.connect(lambda: self.set_SysML_Model_view())

        lca_processes_action = view_menu.addAction("LCA Processes")
        lca_processes_action.setCheckable(True)
        lca_processes_action.triggered.connect(lambda: self.set_LCA_Processes_view())

        lca_flows_action = view_menu.addAction("LCA Flows")
        lca_flows_action.setCheckable(True)
        lca_flows_action.triggered.connect(lambda: self.set_LCA_Flows_view())

        view_group = QActionGroup(self)
        view_group.addAction(self.sysml_model_action)
        view_group.addAction(lca_processes_action)
        view_group.addAction(lca_flows_action)

    def open_preferences_dialog(self):
        # Open a dialog to handle preferences
        # Implement your logic here to open a dialog for handling preferences
        # You can use tkinter's messagebox or a custom dialog box
        def ok_button_clicked():
            self.sysmlserver = entrySysML.get()
            self.preferences["sysmlserver"] = self.sysmlserver
            self.openLCAServerURL = entryLCA.get()
            self.preferences["openlcaserver"] = self.openLCAServerURL
            safe_preferences(self.preferences)
            dialog.destroy()

        def cancel_button_clicked():
            dialog.destroy()

        dialog = QDialog(self)
        dialog.setWindowTitle("Preferences Dialog")
        dialog.setGeometry(100, 100, 500, 200)

        layout = QVBoxLayout(dialog)

        sysmlserver_label = QLabel("SysML Server")
        layout.addWidget(sysmlserver_label)

        entrySysML = QLineEdit()
        entrySysML.setText(self.sysmlserver)
        layout.addWidget(entrySysML)

        openLCA_label = QLabel("openLCA Server")
        layout.addWidget(openLCA_label)

        entryLCA = QLineEdit()
        entryLCA.setText(self.openLCAServerURL)
        layout.addWidget(entryLCA)

        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        def ok_button_clicked():
            self.sysmlserver = entrySysML.text()
            self.preferences["sysmlserver"] = self.sysmlserver
            self.openLCAServerURL = entryLCA.text()
            self.preferences["openlcaserver"] = self.openLCAServerURL
            safe_preferences(self.preferences)
            dialog.accept()

        def cancel_button_clicked():
            dialog.reject()

        ok_button.clicked.connect(ok_button_clicked)
        cancel_button.clicked.connect(cancel_button_clicked)

        dialog.exec_()
        
        pass

    def search_textbox(self):
        def perform_search():
            search_term = search_entry.text()
            print("perform_search", search_term)
            self.browser.page().runJavaScript("""
                var elements = document.querySelectorAll('.highlight');
                elements.forEach(function(element) {
                    element.classList.remove('highlight');
                });
            """)
            if search_term:
                self.browser.page().runJavaScript(f"""
                    var search_term = "{search_term}";
                    var regex = new RegExp(search_term, 'gi');
                    document.body.innerHTML = document.body.innerHTML.replace(regex, function(matched) {{
                        return "<span class='highlight'>" + matched + "</span>";
                    }});
                    var elements = document.querySelectorAll('.highlight');
                    elements.forEach(function(element) {{
                        element.style.backgroundColor = 'yellow';
                        element.style.color = 'black';
                    }});
                """)
            search_dialog.accept()
        
        search_dialog = QDialog(self)
        search_dialog.setWindowTitle("Search")
        search_dialog.setGeometry(100, 100, 300, 100)

        layout = QVBoxLayout(search_dialog)

        search_label = QLabel("Search for:")
        layout.addWidget(search_label)

        search_entry = QLineEdit()
        layout.addWidget(search_entry)

        search_button = QPushButton("Search")
        search_button.clicked.connect(perform_search)
        layout.addWidget(search_button)

        search_dialog.exec_()

    def copyAll(self):
        def handle_html(html):
            clipboard = QApplication.clipboard()
            clipboard.clear()
            clipboard.setText(html)
        
        self.browser.page().toHtml(handle_html)

    def get_LCA_processes(self):
        s="<no model selected>"
        if self.theModel:
            s=f"""
            <!doctype html>
            <html><head><meta charset=\"UTF-8\"><title>{self.theModel.name}</title>
            <style>p {{ margin-left: 10px; margin-top:0px; margin-bottom:0px;}}
            h3 {{margin-bottom:0px;}}</style>
            </head>
            <body>
            """
            for p in self.theModel.getLCAParts():
                s+=f"<h3>{p['name']}</h3>\n"
                for exch in p['exchanges']:
                    unit = self.theModel.getElement(exch['value']['mRef'])
                    if unit: 
                        unit = unit.get('declaredShortName')
                    else:
                        unit = "Number of items"
                    s+=f"<p>{exch['name']} : {exch['value']['num']} {unit}</p>\n"
            s+="</body></html>"
        return s

    def set_LCA_Flows_view(self):
        try:
            theLCAServer= openLCAServer(self.openLCAServerURL)
            self.browser.setHtml("")
            flowsPackage = theLCAServer.getSysMLFlowsPackage("sysml")
            self.browser.setHtml(f"<html><body><pre><code>{flowsPackage}</code></pre></body></html>")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

    def set_LCA_Processes_view(self):
        self.browser.setHtml(self.get_LCA_processes())
 

    def set_SysML_Model_view(self):
        print("set_SysML_Model_view")
        self.sysml_model_action.setChecked(True)
        self.browser.setHtml("")
        print ("set_SysML_Model_view", self.theModel.asHTML())
        if self.theModel:
            self.browser.setHtml(self.theModel.asHTML())    

    def synchronizeProcesses(self):
        try:
            theLCAServer= openLCAServer(self.openLCAServerURL)
            if self.theModel:
                parts = self.theModel.getLCAParts()
                if len(parts) == 0:
                    QMessageBox.warning(self, "Error", "No parts with lca exchanges found in the SysML model.")
                else: 
                    for p in parts:
                        self.updateStatusBar(f"Synchronizing {p['name']} process")
                        theLCAServer.createProcess(p['name'],p['exchanges'])
                    QMessageBox.information(self, "Success", f"Synchronized {len(parts)} processes successfully.") 
                    self.updateStatusBar(f"Synchronized {len(parts)} processes successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to synchronize: {e}.")

if __name__ == "__main__":
    logging.debug("im main block")
    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
