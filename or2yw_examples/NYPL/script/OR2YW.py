# import all library needed for this class
import json

from openrefine_client_master.google.refine import refine


class OR2YW:
    def __init__(self,server_ip=None,server_port=None):
        """
        Init function for this class, put any initialization attributes that you need here
        """
        self.server_ip=server_ip
        self.server_port=server_port
        pass

    def get_projects(self):
        """
        return the list of projects (project_id,name) and or some rows sample for all projects in the server
        :return:
        """
        return refine.Refine(refine.RefineServer(refine_port=self.server_port,server=self.server_ip)).list_projects()

    def get_json(self,id):
        """
        id: project id which we want to create workflow with
        return the list of operations (json/dictionary) gathered using ORClientAPI
        :return:
        """
        outputs=refine.RefineProject(refine.RefineServer(refine_port=self.server_port,server=self.server_ip),refine_port=self.server_port,project_id=id).get_operations()
        return json.loads(outputs.read())

    def generate_yw_script(self,operations):
        """
        given a list of operations in dictionary format, return yes workflow script in text
        id: list of operations dictionary / json format
        return yw_script (text / string)
        :return:
        """
        pass

    def generate_yw_image(self,yw_script,image_type=None):
        """
        given a yw_script return the image based on choice
        id: yw_script string
        return binary image
        :return:
        """
        pass
