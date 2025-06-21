from minke.containers.base import BaseContainer
import json 
import os
import shutil

from minke.job import MinkeJob

class ExtractContainer(BaseContainer):

    DOCKERFILE_DIR = "netmon"

    def __init__(self, client, name):
        super().__init__(client, 'minke-netmon', name)

    def process(self, job_obj : MinkeJob):
        pass



        




