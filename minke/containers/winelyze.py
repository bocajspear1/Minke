from minke.containers.base import BaseContainer
from minke.lib.job import MinkeJob

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
        super().__init__('minke-winelyze', name, network=True, logger=logger)
        self._interesting_syscalls = []
        self._depth_map = {}
        self._string_map = {}

        my_dir = os.path.dirname(os.path.realpath(__file__))
        data_path = os.path.join(my_dir, "..", "data", "interesting_syscalls.txt")
        data_file = open(data_path, "r")
        syscall_list_raw = data_file.read()
        data_file.close()
        syscall_split = syscall_list_raw.split("\n")
        for item in syscall_split:
            if item.strip() != "":
                if "|" in item:
                    item_split = item.split("|")
                    api_name = item_split[0].strip().lower()
                    self._interesting_syscalls.append(api_name)
                    self._depth_map[api_name] = int(item_split[len(item_split)-1])
                    print(f"Set depth of {api_name} to {self._depth_map[api_name]}")
                else:
                    self._interesting_syscalls.append(item.strip().lower())

    def find_process_pid_string(self, lines, procname):
        print("Looking for " + procname)
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

    def _process_tid_calls(self, job_obj : MinkeJob, call_list):
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
                        item_split = item.split("L\"", maxsplit=1)
                        args[j] = "\"" + item_split[1].strip()
                    elif "\"" in item:
                        item_split = item.split("\"", maxsplit=1)
                        args[j] = "\"" + item_split[1].strip()

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
                        if not os.path.exists(f"{job_obj.base_dir}/extracted"):
                            os.mkdir(f"{job_obj.base_dir}/extracted")
                        filename = os.path.basename(extract_path)
                        self.extract(extract_path, f"{job_obj.base_dir}/extracted")
                        new_filename = f"{job_obj.base_dir}/extracted/{filename}"
                        if os.path.exists(new_filename):
                            os.chmod(new_filename, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
                            job_obj.add_info('written_files', filename)
                        job_obj.save()

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

                    retnum = -1
                    if "=" in retval:
                        retnum = int(retval.split("=")[1], 16)

                    # Resolve any strings
                    for arg_i in range(len(args)):
                        if args[arg_i] in self._string_map:
                            args[arg_i] = self._string_map[args[arg_i]]
                            


                    skip = False
                    # Check if this is a string init API call
                    if api_name == "ntdll.rtlinitunicodestring" and len(args) == 2:
                        skip = True
                        self._string_map[args[0]] = args[1]
                        # print(self._string_map)
                    elif api_name == "ntdll.rtlinitansistring" and len(args) == 2:
                        skip = True
                        self._string_map[args[0]] = args[1]
                        # print(self._string_map)


                    if not skip:
                        _, sub_loaded_libs, sub_syscalls = self._process_tid_calls(job_obj, raw_subcalls)
                        loaded_libs += sub_loaded_libs
                        calls.append({
                            "api": api_name,
                            "args": args,
                            "ret": retnum,
                            "call":  data.strip() + " " + retval,
                            "subcalls": sub_syscalls
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
                    if loaded_item.endswith(".exe"):
                        loaded_item_split = loaded_item.split("\\")
                        proc_name = loaded_item
                    elif ".dll" in loaded_item:
                        loaded_item = loaded_item.replace("\\\\", "\\")
                        loaded_libs.append(loaded_item)
            i+=1

        return proc_name, loaded_libs, calls


    def _flatten_syscalls(self, call_list, depth, found=False):
        return_list = []
        for syscall in call_list:
            if len(syscall['subcalls']) > 0:
                return_list = self._flatten_syscalls(syscall['subcalls'], depth+1) + return_list
                syscall['subcalls'] = []
            if syscall['api'] in self._interesting_syscalls:
                if syscall['api'] in self._depth_map:
                    if int(self._depth_map[syscall['api']]) > depth:
                        return_list.append(syscall)
                else:
                    return_list.append(syscall)

        return return_list

    def process(self, job_obj : MinkeJob):

        username = self.vars['USER']
        execsample = self.vars['SAMPLENAME']
        screenshot_dir = self.vars['SCREENSHOT']
        log_file = self.vars['LOG']

        self.extract(f'/tmp/{log_file}', job_obj.base_dir)
        self.extract(f'/tmp/{screenshot_dir}', job_obj.base_dir)

        screenshot_raws = os.listdir(f"{job_obj.base_dir}/{screenshot_dir}")
        for item in screenshot_raws:
            new_name = item.replace("xscr", "png")
            subprocess.check_output(["/usr/bin/convert", f"xwd:{job_obj.base_dir}/{screenshot_dir}/{item}", f"{job_obj.base_dir}/{screenshot_dir}/{new_name}"])
            os.remove(f"{job_obj.base_dir}/{screenshot_dir}/{item}")
        
        self._logger.info("Processing Wine dump...")
        dump_file = open(os.path.join(job_obj.base_dir, log_file))
        dump_data = dump_file.read()
        dump_file.close()

        lines = dump_data.split("\n")
        pid = None

        # Trim for "start.exe"
        start_pid, i = self.find_process_pid_string(lines, "start.exe")
        if start_pid != "":
            lines = lines[i:]
        # Trim for wineconsole
        wineconsole_pid, i = self.find_process_pid_string(lines, "wineconsole.exe")
        if wineconsole_pid != "":
            lines = lines[i:]
        # Trim for conhost
        conhost_pid, i = self.find_process_pid_string(lines, "conhost.exe")
        if conhost_pid != "":
            lines = lines[i:]

        # Remove all calls from wineconsole and start.exe
        new_lines = []

        for line in lines:
            if start_pid != "" and line.startswith(start_pid):
                continue
            if wineconsole_pid != "" and line.startswith(wineconsole_pid):
                continue
            if conhost_pid != "" and line.startswith(conhost_pid):
                continue
            # if not line.startswith(start_pid) and not line.startswith(wineconsole_pid) \
            #     and not line.startswith(conhost_pid) and not line.startswith("Call window proc") \
            #     and not ": stub" in line:
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
                proc_name, loaded_libs, syscalls = self._process_tid_calls(job_obj, pid_list[pid][tid])

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

        output_file = open(os.path.join(job_obj.base_dir, "syscalls_raw.json"), "w+")
        json.dump(out_data, output_file, indent="    ")
        output_file.close()

        self._logger.info("Flattening Wine syscalls...")

        for pid in out_data['processes']:
            for tid in out_data['processes'][pid]['threads']:
                thread_list = out_data['processes'][pid]['threads'][tid]
                flattened_list = self._flatten_syscalls(thread_list, 0)
                out_data['processes'][pid]['threads'][tid] = flattened_list

        output_file = open(os.path.join(job_obj.base_dir, "syscalls_flattened.json"), "w+")
        json.dump(out_data, output_file, indent="    ")
        output_file.close()


        return True

        

        

        
        



        

        