
import uuid
import os
import json
import stat
import copy
import re
import base64

import magic

from .helper import file_clean

class MinkeJob():

    @classmethod
    def new(cls, sample_base):
        if not os.path.exists(sample_base):
            os.mkdir(sample_base)
        new_cls = cls(sample_base, uuid=str(uuid.uuid4()))
        return new_cls

    def __init__(self, sample_base, uuid):
        self._sample_base = sample_base
        self._uuid = uuid
        self._config = {}
        self._info = {
            'complete': False,
            "written_files": []
        }

    def get_info(self):
        return copy.deepcopy(self._info)

    def get_config(self):
        return copy.deepcopy(self._config)

    def exists(self):
        return os.path.exists(self.base_dir)

    def _load_json_file(self, path):
        if os.path.exists(path):
            load_file = open(path, "r")
            json_data = json.loads(load_file.read())
            load_file.close()
            return json_data
        else:
            return {}

    def _save_json_file(self, path, data):
        out_file = open(path, "w+")
        out_file.write(json.dumps(data, indent=4))
        out_file.close()

    def load(self):
        self._config = self._load_json_file(self.config_path)
        self._info = self._load_json_file(self.info_path)

        if not os.path.exists(self.base_dir):
            os.mkdir(self.base_dir)
        if not os.path.exists(self.files_dir):
            os.mkdir(self.files_dir)

    def save(self):
        self._save_json_file(self.config_path, self._config)
        self._save_json_file(self.info_path, self._info)

    def get_config_value(self, key):
        if key in self._config:
            return self._config[key]
        else:
            return None

    def add_file(self, filename):
        if 'files' not in self._info:
            self._info['files'] = []

        self._info['files'].append(filename)
        return os.path.join(self.files_dir, filename)

    def add_info(self, key, data):
        if key in self._info:
            if isinstance(self._info[key], dict):
                self._info[key] = data
            elif not isinstance(self._info[key], list):
                old_data = self._info[key]
                self._info[key] = [old_data]
                self._info[key].append(data)
            elif isinstance(self._info[key], list):
                self._info[key].append(data)
        else:
            self._info[key] = [data]

    def set_info(self, key, data):
        self._info[key] = data

    def setup_file(self, filename):
        filename = file_clean(filename)
        file_path = os.path.join(self.files_dir, filename)
        os.chmod(file_path, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)

    def get_file_type(self, filename):
        if filename not in self._info['files']:
            print(f"File {filename} not found")
            return None
        return magic.from_file(os.path.join(self.files_dir, filename), mime=True)

    def set_config_value(self, key, value):
        self._config[key] = value

    def list_files(self):
        return os.listdir(self.files_dir)

    def list_logs(self):
        return os.listdir(self.logs_dir)

    def write_log(self, log_name, log_data):
        log_name = file_clean(log_name)
        if not os.path.exists(self.logs_dir):
            os.mkdir(self.logs_dir)
        out_file = open(os.path.join(self.logs_dir, log_name), "w")
        out_file.write(log_data)
        out_file.close()

    def get_log(self, log_name):
        log_name = file_clean(log_name)
        log_path = os.path.join(self.logs_dir, log_name)
        if not os.path.exists(log_path):
            return None
        out_file = open(log_path, "r")
        out_data = out_file.read()
        out_file.close()
        return out_data

    def get_flattened_syscalls(self):
        file_path = os.path.join(self.base_dir, "syscalls_flattened.json")
        if not os.path.exists(file_path):
            return None
        
        out_file = open(file_path, "r")
        syscall_data = out_file.read()
        out_file.close()

        if syscall_data.strip() == "":
            return None

        return json.loads(syscall_data)

    def _get_ports4u_log(self, logname, raw=False):
        logname = file_clean(logname)

        net_log_dir = os.path.join(self.network_dir, "logs")

        net_data_path = os.path.join(net_log_dir, logname)
        if os.path.exists(net_data_path):
            flag = "r"
            if raw is True:
                flag = "rb"
            net_data_file = open(net_data_path, flag)
            net_data = net_data_file.read()
            net_data_file.close()
            return net_data.strip()
        else:
            return None

    def get_network_connections(self):
        conn_data = self._get_ports4u_log("conn_list.txt")
        if conn_data is not None:
            ret_list = []
            for item in conn_data.split("\n"):
                if item.strip() != "" and "<nil>" not in item:
                    ret_list.append(item.strip())
            return ret_list
        else:
            return []

    def get_ip_list(self):
        ip_data = self._get_ports4u_log("ip_list.txt")
        if ip_data is not None:
            return ip_data.split("\n")
        else:
            return []

    def get_domains(self):
        domain_data = self._get_ports4u_log("domains.txt")
        if domain_data is not None:
            return domain_data.split("\n")
        else:
            return []

    def get_network_data(self):
        conn_data = self.get_network_connections()
        ret_dict = {}
        for conn in conn_data:
            conn_split = conn.split("|")
            ip_addr = self._info['ip_addr']
            port = conn_split[2]

            conn_log_data = self._get_ports4u_log(f"{ip_addr}-{port}.log", raw=True)

            if conn_log_data is not None:
                ret_dict[conn] = []

                conn_split = re.split(b'<<<<<<<< [0-9.]+ ----------------------------', conn_log_data)
                for conn_section in conn_split:
                    
                    if conn_section.strip() == b"":
                        continue
                    dir_split = re.split(b'>>>>>>>> [0-9.]+ ----------------------------', conn_section)
                    if len(dir_split) == 1:
                        ret_dict[conn].append([base64.b64encode(dir_split[0]).decode(), ''])
                    else:
                        ret_dict[conn].append([base64.b64encode(dir_split[0]).decode(), base64.b64encode(dir_split[1]).decode()])

            return ret_dict

    @property
    def uuid(self):
        return str(self._uuid)

    @property
    def config_path(self):
        return os.path.join(self.base_dir, "config.json")

    @property
    def info_path(self):
        return os.path.join(self.base_dir, "info.json")

    @property
    def base_dir(self):
        return os.path.join(self._sample_base, self._uuid)

    @property
    def files_dir(self):
        return os.path.join(self.base_dir, "files")

    @property
    def logs_dir(self):
        return os.path.join(self.base_dir, "logs")

    @property
    def network_dir(self):
        return os.path.join(self.base_dir, "network")

    @property
    def is_done(self):
        pass
