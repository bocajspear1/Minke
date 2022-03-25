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

    def __init__(self, image_name, name, network=False):
        self._name = name 
        self._image = image_name
        self._ports4u_name = 'ports4u-' + self._name
        self._network = network
        self._client = docker.from_env()
        self._created = False
        self._logger = logging.getLogger(f'{self._name}-logger')
        self.vars = {}

        try:
            container = self._client.containers.get(self._name)
            container.remove()
        except docker.errors.NotFound:
            pass
        except docker.errors.APIError:
            pass 

    def __del__(self):
        try:
            container = self._client.containers.get(self._name)
            container.remove()
        except docker.errors.NotFound:
            pass
        except docker.errors.APIError:
            pass 

    def start(self, share_dir, env_vars=None):

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
                    subprocess.check_output(["/usr/bin/sudo", "/usr/bin/ovs-vsctl", "add-br", self._switch], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                    ok = True 
                    self._logger.info("Create switch %s", self._switch)
                except:
                    i += 1

                # Create ports4u container
                p_container = self._client.containers.create('ports4u', detach=True, name=self._ports4u_name, network_mode="none", cap_add=["NET_ADMIN", "NET_RAW"])
                p_container.start()

                subprocess.check_output(["/usr/bin/sudo", "/usr/bin/ovs-docker", "add-port", self._switch, "eth0", self._ports4u_name, "--ipaddress={}".format('172.16.3.1/24')])

        container = None
        if self._network:
            container = self._client.containers.create(self._image, volumes=vols, environment=environment, detach=True, name=self._name, network_mode="none", dns=["172.16.3.1"])
        else:
            container = self._client.containers.create(self._image, volumes=vols, environment=environment, detach=True, name=self._name, network_mode="none")

        self._created = True
        container.start()
        self._logger.info(f"Started container {self._name}")

        if self._network:

            try:
                subprocess.check_output(["/usr/bin/sudo", "/usr/bin/ovs-docker", "del-ports", self._switch, self._name], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            except:
                pass

            subprocess.check_output(["/usr/bin/sudo", "/usr/bin/ovs-docker", "add-port", self._switch, "eth0", self._name, "--ipaddress={}".format('172.16.3.4/24'), "--gateway={}".format('172.16.3.1')])


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

    def extract(self, cont_path, out_path):
        container = self._client.containers.get(self._name)
        strm, stat = container.get_archive(cont_path)
        results = open("/tmp/extract-data.tar", "wb")
        for chunk in strm:
            results.write(chunk)
        results.close()

        results_tar = tarfile.open("/tmp/extract-data.tar", "r")
        results_tar.extractall(path=out_path)
        results_tar.close()

        os.remove("/tmp/extract-data.tar")

    def process(self):
        raise NotImplementedError