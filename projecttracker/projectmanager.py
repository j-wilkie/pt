import time
import csv
import pickle
import queue
from deckmanager import DeckManager
from deckmanager import DeckMissingError
from pathlib import Path

class ProjectManager:
    def __init__(self):
        self.file_path = Path(__file__)
        self.projects_file = self.file_path.parent / "save" / "projects.pkl"
        try:
            self.projects = self.load_projects()
        except FileNotFoundError:
            self.projects = {}
            self.save_projects(self.projects)

        self.selected_proj = None
        self.button_press_queue = queue.Queue()
        try:
            self.dm = DeckManager(self.button_press_queue)
            self.projects_on_keys = {}
            self.assign_projects_to_keys()
            self.selected_proj_start_time = None
        except DeckMissingError:
            # deck not found 
            raise DeckMissingError("No deck has been found")
        

    # Temp method to assign projects to deck keys. Wont be required once drag and drop implemented to set deck keys
    def assign_projects_to_keys(self):
        project_keys = list(self.projects.keys())
        key_data = []
        for i in range(15): # change to deck num keys
            if i < len(project_keys) and self.projects[project_keys[i]].is_active():
                self.projects_on_keys[i] = project_keys[i]
                project = self.projects[project_keys[i]]
                key_data.append((project.get_icon_path(), project.get_name()))
            else:
                self.projects_on_keys[i] = None
        self.dm.set_keys(key_data)

    # TODO tidy up
    def key_press(self, key):
        proj_id = self.projects_on_keys[int(key)]
        if proj_id != None: # key press has an assigned project
            if proj_id == self.selected_proj: # stop current project don't select a new projects
                self.store_project_use(proj_id)
                self.selected_proj = None
                self.selected_proj_start_time = None
            else:
                if self.selected_proj != None: 
                    self.store_project_use(self.selected_proj)
                self.selected_proj = proj_id
                self.selected_proj_start_time = time.time()

    def store_project_use(self, proj_id):
        self.projects[proj_id].add_project_use(
            time.ctime(self.selected_proj_start_time), 
            int(time.time() - self.selected_proj_start_time))
        self.save_projects(self.projects)    

    def export_task_durations(self, path):
        # need to check valid path
        with open(path, 'w') as f:
            for key in self.projects.keys():
                f.write("{}, ".format(key))
                project = self.projects[key]
                for project_use in project.get_project_uses():
                    f.write("{}, {},".format(project_use.get_start_time_stamp(), 
                        project_use.get_duration()))
                f.write('\n')

    def get_projects(self):
        return self.projects

    def project_name_in_use(self, name):
        for key in self.projects:
            if key == name:
                return True
        return False

    def add_new_project(self, name, icon_path):
        if icon_path == "": # icon image was empty set default
            icon_path = self.file_path.parent / "images" / "default.png" 
            icon_path = str(icon_path.absolute())
        self.projects[name] = Project(name, icon_path)
        self.save_projects(self.projects)

    def archive_project(self, name):
        self.projects[name].set_project_status(False)
        # if active need to stop
        # if in current selection need to remove and redraw deck
        if name in self.projects_on_keys:
            # remove from dict
            del self.projects_on_keys[name]
            # redraw
            self.assign_projects_to_keys()

        self.save_projects(self.projects)

    def activate_project(self, name):
        self.projects[name].set_project_status(True)
        self.save_projects(self.projects)

    # move to seperate thread
    def save_projects(self, projects):
        with open(self.projects_file, 'wb') as f:  
            pickle.dump(projects, f, pickle.HIGHEST_PROTOCOL)

    def load_projects(self):
        with open(self.projects_file, 'rb') as f:
            return pickle.load(f)

    def poll(self):
        try:
            msg = self.button_press_queue.get(0)   
            self.key_press(msg)  
        except queue.Empty:
            # Queue is empty do nothing
            pass
            

    def exit(self):
        self.dm.stop()
        if self.selected_proj != None: # currently a project is selected
            self.store_project_use(self.selected_proj)


class Project:
    def __init__(self, name, icon_path):
        self.name = name
        self.icon_path = icon_path
        self.project_uses = []
        self.project_active = True

    def get_name(self):
        return self.name

    def get_icon_path(self):
        return self.icon_path

    def get_project_uses(self):
        return self.project_uses

    def is_active(self):
        return self.project_active

    def set_project_status(self, status):
        self.project_active = status

    def add_project_use(self, time_stamp, duration):
        self.project_uses.append(ProjectUse(time_stamp, duration))

class ProjectUse:
    def __init__(self, start_time_stamp, duration):
        self.start_time_stamp = start_time_stamp
        self.duration = duration

    def get_start_time_stamp(self):
        return self.start_time_stamp

    def get_duration(self):
        return self.duration
