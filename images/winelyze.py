from images.base import BaseContainer
from images.config import get_config, set_config
import os
import threading
import random
import string

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

        