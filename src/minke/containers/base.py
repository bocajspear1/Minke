import docker
import subprocess
import random 
import string
import logging
import time
import tarfile 
import os
import json


class BaseContainer():

    def __init__(self, image_name, name, network=False, logger=None):
        self._name = name 
        self._image = image_name
        self._ports4u_name = 'ports4u-' + self._name
        self._network = network
        self._client = docker.from_env()
        self._created = False
        self._switch = None
        self._tcpdump_proc = None
        if logger is None:
            self._logger = logging.getLogger(f'{self._name}-logger')
        else:
            self._logger = logger
        self.vars = {}

        if not self._is_debug():
            try:
                container = self._client.containers.get(self._name)
                container.remove()
            except docker.errors.NotFound:
                pass
            except docker.errors.APIError:
                pass 

            try:
                container = self._client.containers.get(self._ports4u_name)
                container.remove()
            except docker.errors.NotFound:
                pass
            except docker.errors.APIError:
                pass 

    def __del__(self):
        self.remove()

    def _is_debug(self):
        return os.getenv("MINKE_DEBUG") is not None

    def remove(self):
        try:
            container = self._client.containers.get(self._name)
            container.stop()
            if not self._is_debug():
                self._logger.info("Removing container %s", self._name)
                if self._switch:
                    subprocess.check_output(["/usr/bin/sudo", "/usr/bin/ovs-docker", "del-port", self._switch, "eth0", self._name])
                container.remove()
        except docker.errors.NotFound:
            pass
        except docker.errors.APIError:
            pass 

        try:
            container = self._client.containers.get(self._ports4u_name)
            container.stop()
            if not self._is_debug():
                self._logger.info("Removing container %s", self._ports4u_name)
                if self._switch:
                    subprocess.check_output(["/usr/bin/sudo", "/usr/bin/ovs-docker", "del-port", self._switch, "eth0", self._ports4u_name])
                container.remove()
        except docker.errors.NotFound:
            pass
        except docker.errors.APIError:
            pass 
        
        if self._tcpdump_proc is not None:
            self._tcpdump_proc.terminate()

        if self._switch is not None:
            self._logger.info("Removing switch %s", self._switch)
            subprocess.check_output(["/usr/bin/sudo", "/usr/local/bin/minke-remove-bridge", self._switch])
            
        
        
    def start(self, job_obj, share_dir, env_vars=None):

        share_dir = os.path.abspath(share_dir)

        environment = {}

        if env_vars is not None:
            environment = env_vars

        tmp_dir = '/tmp/' + ''.join(random.choice(string.ascii_lowercase) for i in range(8))

        vols = {
            share_dir: {"bind": tmp_dir, 'mode': 'ro'}
        }

        environment['TMPDIR'] = tmp_dir

        self.vars = environment

        if self._network:
            i = 0
            ok = False 
            while not ok:
                # Create private switch for analysis
                try:
                    self._switch = f"vmbr{i}"
                    subprocess.check_output(["/usr/bin/sudo", "/usr/local/bin/minke-create-bridge", self._switch])
                    ok = True 
                    self._logger.info("Created switch %s", self._switch)
                except:
                    i += 1

            self._tcpdump_proc = subprocess.Popen(["/usr/sbin/tcpdump", "-U", "-i", f"{self._switch}mon", "-s", "65535", "-w", f"{job_obj.base_dir}/traffic.pcap"])

            # Create ports4u container
            p_env = {
                "SLEEP_BEFORE": 5
            }
            p_container = self._client.containers.create('ports4u', environment=p_env, detach=True, name=self._ports4u_name, network_mode="none", cap_add=["NET_ADMIN", "NET_RAW"])
            p_container.start()
            subprocess.check_output(["/usr/bin/sudo", "/usr/bin/ovs-docker", "add-port", self._switch, "eth0", self._ports4u_name, "--ipaddress={}".format('172.16.3.1/24')])
            
            self._logger.info(f"Started container {self._ports4u_name}")
            time.sleep(5)

            

        container = None
        if self._network:
            container = self._client.containers.create(self._image, volumes=vols, environment=environment, detach=True, name=self._name, network_mode="none", dns=["172.16.3.1"])
        else:
            container = self._client.containers.create(self._image, volumes=vols, environment=environment, detach=True, name=self._name, network_mode="none")

        self._created = True
        container.start()
        self._logger.info(f"Started container {self._name}")

        ip_addr = None
        if self._network:
            try:
                subprocess.check_output(["/usr/bin/sudo", "/usr/bin/ovs-docker", "del-ports", self._switch, self._name], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            except:
                pass

            ip_addr = "172.16.3.4"
            subprocess.check_output(["/usr/bin/sudo", "/usr/bin/ovs-docker", "add-port", self._switch, "eth0", self._name, "--ipaddress={}".format(f'{ip_addr}/24'), "--gateway={}".format('172.16.3.1')])
            # subprocess.check_output(["/usr/bin/sudo", "/usr/local/bin/minke-setup-mirror", self._switch])
            

        return ip_addr

    def wait_and_stop(self):
        i = 0
        done = False
        
        while i < 12 and not done:
            time.sleep(15)
            container = self._client.containers.get(self._name)
            if container.status != "running":
                done = True
            else:
                i += 1

        if not done:
            print("Stopping container...")
            container = self._client.containers.get(self._name)
            container.stop()

        container = self._client.containers.get(self._name)
        main_docker_logs = container.logs().decode('utf8')
        network_docker_logs = ""
        if self._network:
            p_container = self._client.containers.get(self._ports4u_name)
            p_container.stop()
            network_docker_logs = p_container.logs().decode('utf8')


        return main_docker_logs, network_docker_logs

    def extract(self, cont_path, out_path):
        container = self._client.containers.get(self._name)
        try:
            strm, stat = container.get_archive(cont_path)
            results = open("/tmp/extract-data.tar", "wb")
            for chunk in strm:
                results.write(chunk)
            results.close()

            results_tar = tarfile.open("/tmp/extract-data.tar", "r")
            results_tar.extractall(path=out_path)
            results_tar.close()

            os.remove("/tmp/extract-data.tar")
        except docker.errors.NotFound:
            self._logger.info("Could not find file %s", cont_path)

    def process_network(self, job_obj):
        if self._network:
            tar_file = "/tmp/extract-network.tar"
            container = self._client.containers.get(self._ports4u_name)
            try:
                strm, stat = container.get_archive("/opt/ports4u/logs")
                results = open(tar_file, "wb")
                for chunk in strm:
                    results.write(chunk)
                results.close()

                results_tar = tarfile.open(tar_file, "r")
                results_tar.extractall(path=os.path.join(job_obj.base_dir, "network"))
                results_tar.close()
            except docker.errors.NotFound:
                pass

    def process(self, job_dir):
        raise NotImplementedError