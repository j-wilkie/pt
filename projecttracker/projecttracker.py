import sys
import time
from projectmanager import ProjectManager
from deckmanager import DeckMissingError
from PySide2.QtCore import Qt, Slot, QSize, QThread, QThreadPool, QObject, QTimer, QMimeData, SIGNAL
from PySide2.QtGui import QPainter, QIcon, QImage, QPixmap, QDrag
from PySide2.QtWidgets import (QAction, QApplication, QHeaderView, QHBoxLayout, QLabel, QLineEdit,
                               QMainWindow, QPushButton, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget, QListWidget, QListWidgetItem, QFileDialog, 
                               QAbstractItemView, QDialog, QTabWidget, QMessageBox)
from PySide2.QtCharts import QtCharts

class Widget(QWidget):
    def __init__(self):
        QWidget.__init__(self)

# Buttons
class ButtonWidget(QWidget):
    def __init__(self, project_manager, project_list):
        QWidget.__init__(self)
        self.project_manager = project_manager
        self.project_list = project_list

        new_proj_button = QPushButton("New Project")
        new_proj_button.clicked.connect(self.new_project)
        export_button = QPushButton("Export data")
        export_button.clicked.connect(self.export_data)

        # Make horizontal layout
        layout = QHBoxLayout()
        layout.addWidget(new_proj_button)
        layout.addWidget(export_button)
        self.setLayout(layout)

    @Slot()
    def new_project(self):
        dialog = NewProjectDialog(self.project_manager)
        if dialog.exec_():
            self.project_list.list.fill_list(True)

    @Slot()
    def export_data(self):
        path = QFileDialog.getSaveFileName(self, "Export file", "", "(*.csv)")
        self.project_manager.export_task_durations(path[0])

class NewProjectDialog(QDialog):
    def __init__(self, project_manager, parent = None):
        super(NewProjectDialog, self).__init__(parent)
        self.project_manager = project_manager
        self.setWindowTitle("New Project")

        self.project_name = QLineEdit("Enter project name")

        self.icon_button = QPushButton("Browse for icon")
        self.icon_button.clicked.connect(self.find_icon_path)
        self.icon_path = ''

        self.create_button = QPushButton("Create project")
        self.create_button.clicked.connect(self.create_new_project)

        layout = QVBoxLayout()
        layout.addWidget(self.project_name)
        layout.addWidget(self.icon_button)
        layout.addWidget(self.create_button)
        self.setLayout(layout)
     
    @Slot()
    def find_icon_path(self):
        path = QFileDialog.getOpenFileName(self, "Open Image", "", "Image Files (*.png *.jpg *.bmp)")
        self.icon_path = path[0] 
        

    @Slot()
    def create_new_project(self):
        proj_name = self.project_name.text()
        if(not self.project_manager.project_name_in_use(proj_name)):
            self.project_manager.add_new_project(proj_name, self.icon_path)
            self.accept()
        else:
            self.reject()
            # need to deal with if name in use

class ProjectItem(QListWidgetItem):
    def __init__(self):
        QListWidgetItem.__init__(self)

# Project list widget
class ProjectList(QListWidget):
    def __init__(self, project_manager, req_project_status):
        QListWidget.__init__(self)
        self.project_manager = project_manager
        self.setIconSize(QSize(40, 40))
        #self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setAcceptDrops(False)
        self.itemClicked.connect(self.itemCliked)
        self.fill_list(req_project_status)
        self.selected_project = None
    
    def fill_list(self, req_project_status):
        self.clear()
        for name, project in self.project_manager.get_projects().items():
            if req_project_status == project.is_active():
                item = ProjectItem()
                item.setText(name)
                item.setIcon(QIcon(project.get_icon_path())) 
                self.addItem(item)

    def itemCliked(self, item):
        drag = QDrag(self)
        mimeData = QMimeData()
        self.selected_project = item.text()
        mimeData.setText(item.text())
        drag.setMimeData(mimeData)

    def get_selected_project(self):
        return self.selected_project

# Active project list
class ActiveProjectList(QWidget):
    def __init__(self, project_manager, req_project_status):
        QWidget.__init__(self)
        self.project_manager = project_manager
        layout = QVBoxLayout()
        self.list = ProjectList(project_manager, True)
        button = QPushButton("Archive project")
        button.clicked.connect(self.archive_project)
        layout.addWidget(self.list)
        layout.addWidget(button)
        self.setLayout(layout)
        
    @Slot()
    def archive_project(self):
        project_name = self.list.get_selected_project()
        self.project_manager.archive_project(project_name)
        self.list.fill_list(True) # Currently stream deck won't remove archived image 
        # button should be inactive if no project selected

# Archived project list
class ArchivedProjectList(QWidget):
    def __init__(self, project_manager, req_project_status):
        QWidget.__init__(self)
        self.project_manager = project_manager
        layout = QVBoxLayout()
        self.list = ProjectList(project_manager, False)
        button = QPushButton("Activate project")
        button.clicked.connect(self.activate_project)
        layout.addWidget(self.list)
        layout.addWidget(button)
        self.setLayout(layout)

    @Slot()
    def activate_project(self):
        project_name = self.list.get_selected_project()
        self.project_manager.activate_project(project_name)
        self.list.fill_list(False)
        
        

# Stream deck image widget
class StreamDeckLayout(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        label = QLabel(self)
        pixmap = QPixmap('images/stream-deck.jpg')
        label.setPixmap(pixmap)

    def sizeHint(self):
        return QSize(500, 500)    

class MainWindow(QMainWindow):
    def __init__(self, widget, project_manager):
        QMainWindow.__init__(self)
        self.setWindowTitle("Project Manager")
        self.pm = project_manager

        # Menu
        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu("File")

        # Exit QAction
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.exit_app)
        self.file_menu.addAction(exit_action)

        # Layout
        layout2 = QVBoxLayout()
        self.project_tabs = QTabWidget()
        self.project_tabs.connect(self.project_tabs, SIGNAL('currentChanged(int)'), self.changed_tab)
        
        self.active_project_list = ActiveProjectList(project_manager, True)
        self.achived_project_list = ArchivedProjectList(project_manager, False)
        self.project_tabs.addTab(self.active_project_list, "Active projects")
        self.project_tabs.addTab(self.achived_project_list, "Archived")
        layout2.addWidget(self.project_tabs)
        layout2.addWidget(ButtonWidget(project_manager, self.active_project_list))

        self.layout = QHBoxLayout()
        self.layout.addWidget(StreamDeckLayout())
        self.layout.addItem(layout2)

        self.timer = QTimer()
        self.timer.timeout.connect(project_manager.poll)
        self.timer.start(200)

        widget.setLayout(self.layout)
        self.setCentralWidget(widget)
    

    def closeEvent(self, event):
        self.timer.stop()
        self.pm.exit()
        event.accept()


    @Slot()
    def exit_app(self, checked):
        QApplication.quit()
    
    def changed_tab(self, tab_index):
        if tab_index == 0:
            self.active_project_list.list.fill_list(True)
        elif tab_index == 1:
            self.achived_project_list.list.fill_list(False)

if __name__ == "__main__":
    app = QApplication([])

    try:
        pm = ProjectManager()
        widget = Widget()
        # QMainWindow using QWidget as central widget
        window = MainWindow(widget, pm)
        window.resize(800, 600)
        window.show()
        sys.exit(app.exec_())
    except DeckMissingError:
        msgBox = QMessageBox()
        msgBox.setWindowTitle("Missing deck error")
        msgBox.setText("A stream deck couldn't be found attached to your computer. Please attach one and restart the program")
        msgBox.exec_()


    

