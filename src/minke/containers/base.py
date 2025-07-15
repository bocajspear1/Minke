import docker
import subprocess
import ipaddress 
import string
import logging
import time
import tarfile 
import os
import json

from minke.job import MinkeJob

class BaseContainer():

    def __init__(self, client, image_name, name, network=False, logger=None):
        self._name = name 
        self._image = image_name
        self._ports4u_name = 'ports4u-' + self._name
        self._netmon_name = 'netmon-' + self._name
        self._network_name = 'net-' + self._name
        self._network = network
        self._client = client
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
    

    def _get_next_range(self):

        networks = self._client.networks.list()

        octet = 18
        highest_network = ipaddress.IPv4Network("172." + str(octet) + ".0.0/24")
        for network in networks:
            if "IPAM" in network.attrs and "Config" in network.attrs['IPAM'] and \
                network.attrs['IPAM']['Config'] is not None:

                for net_config in network.attrs['IPAM']['Config']:
                    ip_range = ipaddress.IPv4Network(net_config['Subnet'])
                    if ip_range == highest_network:
                        octet += 1
                        highest_network = ipaddress.IPv4Network("172." + str(octet) + ".0.0/24")
        
        return highest_network
    
    def _get_network(self, network_name):
        try:
            return self._client.networks.get(network_name)
        except docker.errors.NotFound:
            return None
        except docker.errors.APIError:
            return None

    def _remove_container(self, container_name):
        
        try:
            container = self._client.containers.get(container_name)
            container.stop()
            if not self._is_debug():
                self._logger.info("Removing container %s", container_name)
                container.remove()
        except docker.errors.NotFound:
            # self._logger.warning("Did not find container %s", container_name)
            pass
        except docker.errors.APIError:
            self._logger.warning("Error removing container %s", container_name)

    def remove(self):

        self._remove_container(self._name)
        self._remove_container(self._netmon_name)
        self._remove_container(self._ports4u_name)

        network = self._get_network(self._network_name)
        if network is not None:
            network.remove()

        
    def start(self, job_obj : MinkeJob, env_vars=None):

        environment = {}

        if env_vars is not None:
            environment = env_vars

        self._logger.debug("Environment = %s", str(environment))

        environment['TMPDIR'] = "/opt/samples"

        self.vars = environment

        network_mode = "none"
        analysis_ip = None

        if self._network:
            # Create network for analysis

            open_subnet = self._get_next_range()

            host_list = list(open_subnet.hosts())
            gateway_ip = str(host_list[0])
            analysis_ip = str(host_list[8])
            fake_gateway_addr = str(host_list[-1])

            ipam_pool = docker.types.IPAMPool(
                subnet=str(open_subnet),
                gateway=fake_gateway_addr,
            )

            ipam_config = docker.types.IPAMConfig(pool_configs=[ipam_pool])

            network = self._client.networks.create(self._network_name, driver="bridge", internal=True, options={
                "com.docker.network.bridge.inhibit_ipv4": "true",
                "com.docker.network.bridge.enable_ip_masquerade": "false",
                # "com.docker.network.bridge.gateway_mode_ipv4": "isolated"
            }, ipam=ipam_config)

            # Create the Ports4U container. This container needs extra capabilities to do traffic sniffing and iptables stuff
            # It also serves as the analysis gateway
            p_env = {
                "SLEEP_BEFORE": 2
            }

            ports4u = self._client.containers.create("ports4u", environment=p_env, detach=True, name=self._ports4u_name, network=self._network_name, networking_config={
                self._network_name: self._client.api.create_endpoint_config(
                    ipv4_address=gateway_ip
                )}, cap_add=["NET_ADMIN", "NET_RAW"])

            ports4u.start()
            self._logger.info(f"Started ports4u container {self._ports4u_name}")

            # Create the netmon container.  This container needs extra capabilities to do traffic sniffing and network configuration
            # The network used by the analysis container actually attaches to this container's networking namespace.
            # This avoids giving the analysis container extra capabilities. 

            networking = self._client.containers.create("minke-netmon", detach=True, name=self._netmon_name, network=self._network_name, 
                                                        environment={"GATEWAY": gateway_ip}, dns=[str(gateway_ip)], networking_config={
                self._network_name: self._client.api.create_endpoint_config(
                    ipv4_address=analysis_ip
                )}, cap_add=["NET_ADMIN", "NET_RAW"])
            networking.start()
            self._logger.info(f"Started netmon container {self._netmon_name}")

            network_mode = "container:" + self._netmon_name

            time.sleep(2)

        # Create our container
        container = self._client.containers.create(self._image, environment=environment, detach=True, name=self._name, network_mode=network_mode)
        self._created = True

        # Copy in our sample files
        archive_path = f"/tmp/{job_obj.uuid}-samples.tar"
        with tarfile.open(archive_path, "w") as tar:
            sample_files = job_obj.list_files()
            for name in sample_files:
                full_path = os.path.join(job_obj.files_dir, name)
                tar.add(full_path, arcname=name)

        with open(archive_path, "rb") as tar:
            container.put_archive("/opt/samples", tar.read())

        time.sleep(1)
        os.unlink(archive_path)

        # Start the container
        container.start()
        self._logger.info(f"Started container {self._name}")

        return analysis_ip

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
            self._logger.info("Stopping container...")
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
    
    def _extract_tar(self, container_name, container_path, tar_path, out_path):
        container = self._client.containers.get(container_name)

        try:
            strm, stat = container.get_archive(container_path)
            results = open(tar_path, "wb")
            for chunk in strm:
                results.write(chunk)
            results.close()

            results_tar = tarfile.open(tar_path, "r")
            results_tar.extractall(path=out_path)
            results_tar.close()

            os.remove(tar_path)
        except docker.errors.NotFound:
            self._logger.info("Could not find path %s", container_path)

    def extract(self, container_path, out_path):
        
        tar_path = f"/tmp/extract-{self._name}.tar"
        self._extract_tar(self._name, container_path, tar_path, out_path)
        

    def process_network(self, job_obj):
        
        if self._network:

            tar_path = f"/tmp/network-{self._name}.tar"
            self._extract_tar(self._ports4u_name, "/opt/ports4u/logs", tar_path, os.path.join(job_obj.base_dir, "network"))

            tar_path = f"/tmp/pcap-{self._name}.tar"
            self._extract_tar(self._netmon_name, "/opt/out/traffic.pcap", tar_path, os.path.join(job_obj.base_dir, "network"))


    def process(self, job_dir):
        raise NotImplementedError