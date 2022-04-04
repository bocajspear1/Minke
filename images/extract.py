from images.base import BaseContainer
import json 
import os
import shutil

class ExtractContainer(BaseContainer):

    def __init__(self, name):
        super().__init__('extract', name)

    def process(self, job_dir):
        newfiles = os.path.join(job_dir, "newfiles")
        filesdir = os.path.join(job_dir, "files")
        self.extract("/tmp/out", newfiles)

        for item in os.listdir(os.path.join(newfiles, "out")):
            print(item)
            shutil.move(os.path.join(newfiles, "out", item), os.path.join(filesdir, item))

        shutil.rmtree(newfiles)

        return True



        




