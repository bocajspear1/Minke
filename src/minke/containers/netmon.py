from minke.containers.base import BaseContainer
import json 
import os
import shutil

from minke.job import MinkeJob

class ExtractContainer(BaseContainer):

    DOCKERFILE_DIR = "netmon"

    def __init__(self, name):
        super().__init__('minke-netmon', name)

    def process(self, job_obj : MinkeJob):
        pass



        




