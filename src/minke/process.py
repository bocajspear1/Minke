import logging
import threading
import time
import random
import string

from minke.job import MinkeJob
from minke.vars import *
from minke.helper import get_containers

from minke.containers.winelyze import WinelyzeContainer
from minke.containers.qemu import QEMUMIPSELContainer
from minke.containers.extract import ExtractContainer

class SampleThread (threading.Thread):
    """
    Manages processing single submissions at a time. The server will create these threads to process process the submitted files
    instead of server thread. Allows a bit of scaling. The server creates the base job and passes the UUID
    to the thread via a queue to start processing.
    """
    def __init__(self, id, queue, config):
        threading.Thread.__init__(self)
        self._queue = queue 
        self._id = id
        self.daemon = True
        self._config = config
        self._log = logging.getLogger(f"SampleThread{self._id}")

    def run(self):
        while True:

            # Get our next job, blocking
            job_obj : MinkeJob = self._queue.get(block=True)
            print(job_obj.uuid)
            # job_dir = os.path.join(SAMPLE_DIR, uuid)
            # file_dir = os.path.join(job_dir, "files")

            # Get the submitted file to execute, since we can take multiple files
            execname = job_obj.get_config_value(START_EXEC_KEY)
            if execname is None:
                self._log.error("Got job with not exec-start")
                continue

            sample_files = job_obj.list_files()

            compressed = False

            for file_item in sample_files:
                if job_obj.get_file_type(file_item) in ('application/zip',):
                    compressed = True
                    self._log.info("Detected compressed file %s, extracting...", file_item)
                    extract_cont = ExtractContainer("extract-" + job_obj.uuid)
                    extract_cont.start(job_obj, job_obj.files_dir, {
                        "EXECSAMPLE": execname
                    })
                    time.sleep(3)
                    extract_cont.process(job_obj)

                
            if compressed is True:
                new_sample_files = job_obj.list_files()
                new_sample_files.remove(execname)

                if len(new_sample_files) > 1:
                    self._log.error("Multiple files, but no execname set. Cannot continue")
                    continue
                elif len(new_sample_files) == 0:
                    self._log.error("Failed to extract files. Cannot continue")
                    continue
                else:
                    execname = new_sample_files[0]
                job_obj.set_config_value(START_EXEC_KEY, execname)
                job_obj.save()


            exec_type = job_obj.get_file_type(execname)
            file_id = job_obj.get_file_id(execname).lower()

            username = self._config['username']

            screenshot = ''.join(random.choice(string.ascii_lowercase) for i in range(6))
            log_file = ''.join(random.choice(string.ascii_lowercase) for i in range(8))
            self._log.debug("exec: %s, user: %s", execname, username)

            container = None
            container_name = ""

            print(exec_type)

            container_list = get_containers()

            cont_inst = None

            for container in container_list:
                if not hasattr(container, "can_process"):
                    continue
                container_name = f"{container.DOCKERFILE_DIR}-{job_obj.uuid}"
                cont_inst = container(container_name, logger=self._log)
                can_process = cont_inst.can_process(exec_type, file_id, execname)
                if not can_process:
                    continue
                self._log.info("Using %s container for sample %s", container.__name__, execname)

                ip_addr = cont_inst.start(job_obj, job_obj.files_dir, {
                    "SAMPLENAME": execname,
                    "USER": username,
                    "SCREENSHOT": screenshot,
                    "LOG": log_file
                })

                job_obj.set_info('ip_addr', ip_addr)
                job_obj.save()

                break


            if cont_inst is not None:
                main_logs, network_logs = cont_inst.wait_and_stop()
                if main_logs.strip() != "":
                    job_obj.write_log(f"{container_name}.log", main_logs)
                if network_logs.strip() != "":
                    job_obj.write_log(f"ports4u-container.log", network_logs)
                cont_inst.process(job_obj)
                cont_inst.process_network(job_obj)
                self._log.info("Analysis %s completed", job_obj.uuid)
                job_obj.set_info('complete', True)
                job_obj.set_info('end_time', time.time())
                job_obj.save()
                del cont_inst
            else:
                self._log.error("No analysis container found")

            time.sleep(.5)