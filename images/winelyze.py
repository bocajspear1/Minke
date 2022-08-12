from images.base import BaseContainer
from images.config import get_config, set_config
import os
import threading
import random
import stat
import subprocess
from csv import reader
import json

GENERIC_WRITE = 0x40000000

class WinelyzeContainer(BaseContainer):

    def __init__(self, name, logger=None):
        super().__init__('winelyze', name, network=True, logger=logger)

    def find_process_pid_string(self, lines, procname):
        i = 0 
        while i < len(lines):
            line = lines[i]
            if "loaddll:build_module Loaded" in line and procname in line:
                line_split = line.split(":", 2)
                pid = line_split[0]
                self._logger.debug(f"Found pid for %s: %s => %s", procname, pid, int(pid, 16))
                return pid, i
            i+=1

        return "", 0

    def _process_tid_calls(self, job_dir, call_list):
        i = 0

        calls = []
        loaded_libs = []
        proc_name = "UNKNOWN"

        while i < len(call_list):
            line = call_list[i]
            oper = line[0]
            data = line[1]
            if oper == "Call":
                # We need the "ret" value to determine return value for call
                # Check to ensure we have it, not having it should not happen often
                if "ret=" not in data:
                    i+=1 
                    continue

                # Extract the API name, 
                data_split = data.split("(")
                api_name = data_split[0].lower()

                

                # Process the arguments
                arg_split = data_split[1].split(")")
                args = []

                if arg_split[0].strip() != "":
                    for arg_item in reader([arg_split[0]]):
                        args += arg_item

                for j in range(len(args)):
                    item = args[j]
                    if "L\"" in item:
                        item_split = item.split("L\"")
                        args[j] = "\"" + item_split[1]

                if api_name in ("kernel32.createfilew", "kernel32.createfilea", "kernel32.createfiletransacteda", "kernel32.createfiletransacteda"):
                    access_mask = int(args[1], 16)
                    if GENERIC_WRITE & access_mask != 0:
                        winpath = args[0][1:-1]
                        self._logger.info("Found written file %s", winpath)
                        name = self.vars['USER']
                        drive_split = winpath.split(":")
                        convert_path = winpath
                        if len(drive_split) > 1:
                            convert_path = drive_split[1]
                        convert_path = convert_path.replace("\\", "/").replace("//", "/")
                        extract_path = f"/home/{name}/.wine/drive_c/{convert_path}"
                        self._logger.info("Converted to path %s", extract_path)
                        if not os.path.exists(f"{job_dir}/extracted"):
                            os.mkdir(f"{job_dir}/extracted")
                        filename = os.path.basename(extract_path)
                        self.extract(extract_path, f"{job_dir}/extracted")
                        os.chmod(f"{job_dir}/extracted/{filename}", stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)

                # Do ret processing
                ret_id = data.split("ret=")[1]

                raw_subcalls = []
                found = False
                i_start = i
                i+=1
                # Loop until we find a "Ret" operation with our ret_id
                while i < len(call_list) and not found:
                    next_line = call_list[i]
                    if "Ret" == next_line[0] and f"ret={ret_id}" in next_line[1]:
                        found = True
                        raw_subcalls.append(next_line)
                    else:
                        raw_subcalls.append(next_line)
                        i+=1

                # If we found our ret_id, and process subcalls
                if found:
                    # print(("    " * depth) + "Found match: ", str(next_line))
                    resplit = next_line[1].split(" ")
                    retval = resplit[-2]
                    calls.append({
                        "api": api_name,
                        "args": args,
                        "ret": int(ret_id, 16),
                        "call":  data.strip() + " " + retval,
                        "subcalls": self._process_tid_calls(job_dir, raw_subcalls)[2]
                    })
                else:
                    calls.append({
                        "api": api_name,
                        "args": args,
                        "ret": "???",
                        "call":  data.strip() + " retval=???",
                        # "subcalls": get_called(raw_subcalls, depth+1)
                        "subcalls": []
                    })
                    i = i_start+1
            elif "trace:loaddll:build_module" in oper:
                if "Loaded" in data:
                    load_split = data.split(" ")
                    loaded_item = load_split[1][2:-1]
                    if ".exe" in loaded_item:
                        loaded_item_split = loaded_item.split("\\")
                        proc_name = loaded_item_split[len(loaded_item_split)-1]
                    elif ".dll" in loaded_item:
                        loaded_libs.append(loaded_item)
            i+=1

        return proc_name, loaded_libs, calls


    def process(self, job_dir):

        username = self.vars['USER']
        execsample = self.vars['SAMPLENAME']
        screenshot_dir = self.vars['SCREENSHOT']
        log_file = self.vars['LOG']

        self.extract(f'/tmp/{log_file}', job_dir)
        self.extract(f'/tmp/{screenshot_dir}', job_dir)

        screenshot_raws = os.listdir(f"{job_dir}/{screenshot_dir}")
        for item in screenshot_raws:
            new_name = item.replace("xscr", "png")
            subprocess.check_output(["/usr/bin/convert", f"xwd:{job_dir}/{screenshot_dir}/{item}", f"{job_dir}/{screenshot_dir}/{new_name}"])
            os.remove(f"{job_dir}/{screenshot_dir}/{item}")
        
        self._logger.info("Processing Wine dump...")
        dump_file = open(os.path.join(job_dir, log_file))
        dump_data = dump_file.read()
        dump_file.close()

        lines = dump_data.split("\n")
        pid = None

        # Trim for "start.exe"
        start_pid, i = self.find_process_pid_string(lines, "start.exe")
        lines = lines[i:]
        # Trim for wineconsole
        wineconsole_pid, i = self.find_process_pid_string(lines, "wineconsole.exe")
        lines = lines[i:]
        # Trim for wineconsole
        conhost_pid, i = self.find_process_pid_string(lines, "conhost.exe")

        # Remove all calls from wineconsole and start.exe
        new_lines = []
        for line in lines:
            if not line.startswith(start_pid) and not line.startswith(wineconsole_pid) \
                and not line.startswith(conhost_pid) and not line.startswith("Call window proc") \
                and not ": stub" in line:
                new_lines.append(line)

        # Get PID for sample
        sample_pid, _ = self.find_process_pid_string(new_lines, execsample)

        if sample_pid == "":
            self._logger.error("Could not determine target pid")
            return False

        pid_list = {}
        for line in new_lines:

            line_split = line.split(":", 2)

            if len(line_split) < 3:
                continue
            
            pid = int(line_split[0], 16)
            tid = int(line_split[1], 16)
            syscall_data = line_split[2].split(" ", 1)
            

            if pid not in pid_list:
                pid_list[pid] = {}

            if tid not in pid_list[pid]:
                pid_list[pid][tid] = []

            pid_list[pid][tid].append(syscall_data)

        self._logger.info("Processing Wine syscalls...")
        new_pid_list = {}
        for pid in pid_list:
            for tid in pid_list[pid]:
                proc_name, loaded_libs, syscalls = self._process_tid_calls(job_dir, pid_list[pid][tid])

                if pid not in new_pid_list:
                    new_pid_list[pid] = {
                        "name": proc_name,
                        "libraries": [],
                        "threads": {}
                    }

                if proc_name != "UNKNOWN":
                    new_pid_list[pid]['name'] = proc_name
                new_pid_list[pid]['libraries'] += loaded_libs
                new_pid_list[pid]['threads'][tid] = syscalls

        out_data = {
            "operating_system": "windows",
            "processes": new_pid_list
        }

        output_file = open(os.path.join(job_dir, "syscalls.json"), "w+")
        json.dump(out_data, output_file, indent="    ")
        output_file.close()

        return True

        

        

        
        



        

        