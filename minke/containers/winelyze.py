from minke.containers.base import BaseContainer
from minke.lib.job import MinkeJob
from minke.lib.screenshots import images_are_same

import os
import threading
import shlex
import stat
import subprocess
from csv import reader
import json

GENERIC_WRITE = 0x40000000



def process_subcalls(string_map, lib_list, child_procs, extract_files, new_subcall_list):
    ret_calls = []
    
    i = 0
    while i < len(new_subcall_list):
        line = new_subcall_list[i]
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
                is_string = False
                if "L\"" in item:
                    is_string = True
                    item_split = item.split("L\"", maxsplit=1)
                    args[j] = "\"" + item_split[1].strip()
                elif "\"" in item:
                    is_string = True
                    item_split = item.split("\"", maxsplit=1)
                    args[j] = "\"" + item_split[1].strip()
                
                if is_string:
                    args[j] = args[j].replace("\\\\", "\\")
                

            # Special processing for certain calls
            if api_name in ("kernel32.createfilew", "kernel32.createfilea", "kernel32.createfiletransacteda", "kernel32.createfiletransacteda"):
                access_mask = int(args[1], 16)
                if GENERIC_WRITE & access_mask != 0:
                    winpath = args[0][1:-1]
                    extract_files.append(winpath)
            elif api_name in ("kernel32.createprocessw",):
                app_path = args[0]
                if "\\" not in app_path:
                    cmd_line = args[1]
                    app_path = shlex.split(cmd_line)[0]
                else:
                    app_path = app_path[1:-1]

                app_path = app_path.split("\\")
                
                # winpath = winpath.replace("\\\\", "\\")
                child_procs.append(app_path[-1])


            # Do ret processing
            ret_id = data.split("ret=")[1]

            end_line = ""
            subsubcall_list = []
            found = False
            i_start = i
            i+=1
            # Loop until we find a "Ret" operation with our ret_id
            while i < len(new_subcall_list) and not found:
                next_line = new_subcall_list[i]
                if "Ret" == next_line[0] and f"ret={ret_id}" in next_line[1]:
                    found = True
                    subsubcall_list.append(next_line)
                    end_line = next_line
                else:
                    subsubcall_list.append(next_line)
                    i+=1
            
            # If we found our ret_id, and process subcalls
            if found:
                # print(("    " * depth) + "Found match: ", str(next_line))
                resplit = end_line[1].split(" ")
                retval = resplit[-2]

                retnum = -1
                if "=" in retval:
                    retnum = int(retval.split("=")[1], 16)

                # Resolve any strings
                for arg_i in range(len(args)):
                    if args[arg_i] in string_map:
                        args[arg_i] = string_map[args[arg_i]]

                skip = False
                # Check if this is a string init API call
                if api_name == "ntdll.rtlinitunicodestring" and len(args) == 2:
                    skip = True
                    string_map[args[0]] = args[1]
                    # print(self._string_map)
                elif api_name == "ntdll.rtlinitansistring" and len(args) == 2:
                    skip = True
                    string_map[args[0]] = args[1]
                    # print(self._string_map)


                if not skip:
                    sub_syscalls = process_subcalls(string_map, lib_list, child_procs, extract_files, subsubcall_list)
                    ret_calls.append({
                        "api": api_name,
                        "args": args,
                        "ret": retnum,
                        "call":  data.strip() + " " + retval,
                        "subcalls": sub_syscalls
                    })
            # Not found, just try our best
            else:
                ret_calls.append({
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
                loaded_path = line[1].split('"')[1]
                if loaded_path.endswith(".dll"):
                    loaded_path = loaded_path.replace("\\\\", "\\")
                    lib_list.append(loaded_path)
        i+=1

    return ret_calls

def process_subprocess(process_name, lines):
    pid = None
    full_path = ""
    proc_search = process_name
    if "\\" not in process_name:
        proc_search = "\\" + process_name

    start = -1
    end = -1

    proc_threads = {}
    loaded_libs = []
    to_remove = []
    
    # Extract all lines that belong to this process
    for i in range(len(lines)):
        line = lines[i]
        line_split = line.split(":", 2)
        if "loaddll:build_module Loaded" in line:
            if proc_search in line:
                if start == -1:
                    start = i
                    pid = line_split[0]
                    full_path = line.split('"')[1]
                    full_path = full_path.replace("\\\\", "\\")
                else:
                    end = i

        if start > -1 and end == -1 and line_split[0] == pid:
            # Parse out the TID and put in separate lists
            tid = line_split[1]
            if tid not in proc_threads:
                proc_threads[tid] = []
            data_split = line_split[2].split(" ", 1)
            data_split[0] = data_split[0].strip()
            data_split[1] = data_split[1].strip()
            proc_threads[tid].append(data_split)
            to_remove.append(line)

    for rline in to_remove:
        lines.remove(rline)
    
    loaded_libs = []
    extract_files = []
    child_processes = []

    child_out_list = []
    thread_out_map = {}
    
    # print(proc_lines)
    for tid in proc_threads:
        thread_calls = proc_threads[tid]
        string_map = {}
        thread_out_map[int(tid, 16)] = process_subcalls(string_map, loaded_libs, child_processes, extract_files, thread_calls)
    
    for child_process in child_processes:
        child_out_list.append(process_subprocess(child_process, lines))

    return {
        "pid": int(pid, 16),
        "path": full_path,
        "libraries": loaded_libs,
        "threads": thread_out_map,
        "child_processes": child_out_list,
        "files_to_extract": extract_files
    }
            
def process_wine_calls(wine_file):
    dump_file = open(wine_file)
    dump_data = dump_file.read()
    dump_file.close()

    lines = dump_data.split("\n")
    all_procs = []
    main_tree_data = process_subprocess("start.exe", lines)
    # start.exe and wineconsole.exe are the top of the tree
    # Let's remove them
    wineconsole_proc = main_tree_data['child_processes'][0]
    sample_proc = wineconsole_proc['child_processes'][0]
    all_procs.append(sample_proc)

    # Maybe some other process was started that was not in the main tree
    # We remove lines from the list as we process, so anything left in lines
    # is not in the main tree
    c = 0
    while c < len(lines):
        line = lines[c]
        if "loaddll:build_module Loaded" in line:
            extra_path = line.split('"')[1]
            if extra_path.endswith(".exe"):
                extra_path = extra_path.replace("\\\\", "\\")
                extra_name = extra_path.split("\\")[-1]
                c = 0
                extra_proc = process_subprocess(extra_name, lines)
                all_procs.append(extra_proc)
        c += 1
                

    return all_procs

def load_syscall_map(syscall_file):
    return_map = {}
    data_file = open(syscall_file, "r")
    syscall_list_raw = data_file.read()
    data_file.close()
    syscall_split = syscall_list_raw.split("\n")
    for syscall_line in syscall_split:
        if syscall_line.strip() != "":
            if "|" in syscall_line:
                item_split = syscall_line.split("|")
                api_name = item_split[0].strip().lower()
                return_map[api_name] = int(item_split[-1])
                print(f"Set depth of {api_name} to {return_map[api_name]}")
            else:
                return_map[syscall_line.strip().lower()] = -1
    
    return return_map

def flatten_thread_syscalls(interesting_syscalls, thread_list, depth):
    return_list = []
    for syscall in thread_list:
        if len(syscall['subcalls']) > 0:
            return_list = flatten_thread_syscalls(interesting_syscalls, syscall['subcalls'], depth+1) + return_list
            syscall['subcalls'] = []
        if syscall['api'] in interesting_syscalls:
            max_depth = interesting_syscalls[syscall['api']]
            if max_depth != -1:
                if max_depth > depth:
                    return_list.append(syscall)
            else:
                return_list.append(syscall)

    return return_list

def flatten_process_syscalls(interesting_syscalls, proc_list):
    for proc in proc_list:
        for tid in proc['threads']:
            proc['threads'][tid] = flatten_thread_syscalls(interesting_syscalls, proc['threads'][tid], 0)
        flatten_process_syscalls(interesting_syscalls, proc['child_processes'])

class WinelyzeContainer(BaseContainer):

    def __init__(self, name, logger=None):
        super().__init__('minke-winelyze', name, network=True, logger=logger)
        self._syscall_map = {}
        self._string_map = {}

        my_dir = os.path.dirname(os.path.realpath(__file__))
        data_path = os.path.join(my_dir, "..", "data", "interesting_syscalls.txt")
        self._syscall_map = load_syscall_map(data_path)

    def _extract_files(self, proc_data, job_obj : MinkeJob):
        for extract_file in proc_data['files_to_extract']:
            self._logger.info("Found written file %s", extract_file)
            name = self.vars['USER']
            drive_split = extract_file.split(":")
            convert_path = extract_file
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

        for child_proc in proc_data['child_processes']:
            self._extract_files(child_proc, job_obj)

    def process(self, job_obj : MinkeJob):

        username = self.vars['USER']
        execsample = self.vars['SAMPLENAME']
        screenshot_dir = self.vars['SCREENSHOT']
        log_file = self.vars['LOG']

        self.extract(f'/tmp/{log_file}', job_obj.base_dir)
        self.extract(f'/tmp/{screenshot_dir}', job_obj.base_dir)

        self._logger.info("Converting screenshots...")
        screenshot_raws = os.listdir(f"{job_obj.base_dir}/{screenshot_dir}")
        for item in screenshot_raws:
            new_name = item.replace("xscr", "png")
            subprocess.check_output(["/usr/bin/convert", f"xwd:{job_obj.base_dir}/{screenshot_dir}/{item}", f"{job_obj.base_dir}/{screenshot_dir}/{new_name}"])
            os.remove(f"{job_obj.base_dir}/{screenshot_dir}/{item}")

        self._logger.info("Removing extra screenshots...")
        screenshot_pngs = os.listdir(f"{job_obj.base_dir}/{screenshot_dir}")
        screenshot_pngs.sort()
        i = 0
        for i in range(len(screenshot_pngs)):
            if i < len(screenshot_pngs)-1:
                start_path = os.path.join(f"{job_obj.base_dir}/{screenshot_dir}", screenshot_pngs[i])
                if not images_are_same(
                    start_path, 
                    os.path.join(f"{job_obj.base_dir}/{screenshot_dir}", screenshot_pngs[i+1])
                ):
                    job_obj.add_screenshot(start_path)


        self._logger.info("Processing Wine dump...")
        proc_list = process_wine_calls(os.path.join(job_obj.base_dir, log_file))

        self._logger.info("Extracting files...")
        for proc in proc_list:
            self._extract_files(proc, job_obj)
        
        out_data = {
            "operating_system": "windows",
            "processes": proc_list
        }

        self._logger.info("Saving syscalls...")
        output_file = open(os.path.join(job_obj.base_dir, "syscalls_raw.json"), "w+")
        json.dump(out_data, output_file, indent="    ")
        output_file.close()

        self._logger.info("Flattening syscalls...")

        flatten_process_syscalls(self._syscall_map, out_data['processes'])

        output_file = open(os.path.join(job_obj.base_dir, "syscalls_flattened.json"), "w+")
        json.dump(out_data, output_file, indent="    ")
        output_file.close()


        return True

        

        

        
        



        

        