from minke.containers.base import BaseContainer
import json 
import os
import shutil

from minke.lib.job import MinkeJob

class ExtractContainer(BaseContainer):

    def __init__(self, name):
        super().__init__('minke-extract', name)

    def process(self, job_obj : MinkeJob):
        newfiles = os.path.join(job_obj.base_dir, "newfiles")
        self.extract("/tmp/out", newfiles)

        out_files = os.listdir(os.path.join(newfiles, "out"))
        
        for item in out_files:
            new_path = job_obj.add_file(item)
            shutil.move(os.path.join(newfiles, "out", item), new_path)
            job_obj.setup_file(item)

        shutil.rmtree(newfiles)

        return True



        




