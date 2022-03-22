from images.base import BaseContainer
from images.config import get_config, set_config
import os
import threading
import random
import string
import subprocess

class WinelyzeContainer(BaseContainer):

    def __init__(self, name):
        super().__init__('winelyze', name, network=True)

    def process(self, job_dir):

        pass
        


class WineylzeThread (threading.Thread):
    def __init__(self, uuid, job_dir):
        threading.Thread.__init__(self) 
        self.daemon = True
        self._uuid = uuid 
        self._job_dir = job_dir

    def run(self):

        container = WinelyzeContainer(f"winelyze-{self._uuid}")

        config = get_config(self._job_dir)
        execname = config['start-exec'] 

        username = ''.join(random.choice(string.ascii_lowercase) for i in range(5))
        screenshot = ''.join(random.choice(string.ascii_lowercase) for i in range(6))
        log_file = ''.join(random.choice(string.ascii_lowercase) for i in range(8))

        container.start(os.path.join(self._job_dir, "files"), {
            "SAMPLENAME": execname,
            "USER": username,
            "SCREENSHOT": screenshot,
            "LOG": log_file
        })

        container.wait_and_stop()

        self.extract(f'/tmp/{log_file}', self._job_dir)
        self.extract(f'/tmp/{screenshot}', self._job_dir)

        screenshot_raws = os.listdir(f"{self._job_dir}/{screenshot}")
        for item in screenshot_raws:
            new_name = item.replace("xscr", "png")
            subprocess.check_output(["/usr/bin/convert", f"xwd:{self._job_dir}/{screenshot}/{item}", f"{self._job_dir}/{screenshot}/{new_name}"])
            os.remove(f"{self._job_dir}/{screenshot}/{item}")



        

        