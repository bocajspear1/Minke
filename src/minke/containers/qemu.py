from minke.containers.base import BaseContainer
from minke.job import MinkeJob
from minke.helper import images_are_same

import os
import json
import shlex
import stat
import re
import shlex
from csv import reader
import binascii

from pprint import pprint

IGNORE_SYSCALLS = (
    'mmap',
    "munmap",
    'futex',
    'arch_prctl',
    'brk',
    "wait4",
    "wait3"
)


def find_next(in_str, find):
    escaped = False
    for i in range(len(in_str)):
        char = in_str[i]

        if char == find and not escaped:
            return i
        
        if char == "\\" and not escaped:
            escaped = True
        else:
            escaped = False
        
        
def comma_split(in_str):
    char_hist = ""
    result_list = []
    last = 0
    for i in range(len(in_str)):
        
        char = in_str[i]

        if char == "," and char_hist == "":
            result_list.append(in_str[last:i].strip())
            last = i+1
        elif char == "'":
            if len(char_hist) > 0 and char_hist[-1] == "'":
                char_hist = char_hist[:-1]
            else:
                char_hist += char
        elif char == '"':
            if len(char_hist) > 0 and char_hist[-1] == '"':
                char_hist = char_hist[:-1]
            else:
                char_hist += char
        elif char in ("[", "(", "{"):
            char_hist += char
        elif char == "]":
            if len(char_hist) > 0 and char_hist[-1] == "[":
                char_hist = char_hist[:-1]
            else:
                raise ValueError("Missing start bracket in " + in_str)
        elif char == ")" :
            if len(char_hist) > 0 and char_hist[-1] == "(":
                char_hist = char_hist[:-1]
            else:
                raise ValueError("Missing start paren in " + in_str)
        elif char == "}" :
            if len(char_hist) > 0 and char_hist[-1] == "{":
                char_hist = char_hist[:-1]
            else:
                raise ValueError("Missing start curly in " + in_str)
    result_list.append(in_str[last:].strip())
    return result_list

def parse_objects(in_str, depth=0):
    if in_str.startswith("["):
        selection = in_str[1:-1]
        
        array_items = comma_split(selection)
        for i in range(len(array_items)):
            array_items[i] = parse_objects(array_items[i], depth=depth+1)
        return array_items
    elif in_str.startswith("{"):
        selection = in_str[1:-1]
        array_items = comma_split(selection)
        return_dict = {}
        for i in range(len(array_items)):
            name_split = array_items[i].split("=", maxsplit=1)
            return_dict[name_split[0]] = parse_objects(name_split[1], depth=depth+1)
        return return_dict
    elif in_str.startswith('"'):
        if in_str.endswith(".."):
            in_str = in_str[:-2]
        hex_data = in_str[1:-1]
        return f'"{convert_hex(hex_data)}"'
    else:
        return in_str


def get_exec_call(syscall_list):
    for syscall in reversed(syscall_list):
        if syscall['syscall'] in ('execve', 'execveat', 'fexecve'):
            return syscall
    return None

def convert_hex(hex_str):
    # print(hex_str)
    return binascii.unhexlify(hex_str.replace("\\x", "").replace('"', "")).decode("utf-8", errors="backslashreplace")

def get_children(start_proc, process_map):
    
    for syscall in start_proc['threads'][start_proc['pid']]:
        if syscall['syscall'] in ('fork', 'clone'):
            new_tid = int(syscall['return'])
            has_exec = get_exec_call(process_map[new_tid])
            
            if has_exec is None:
                start_proc['threads'][new_tid] = process_map[new_tid]
                del process_map[new_tid]
            else:
                # pprint(has_exec)
                exec_path = has_exec['args'][0]
                cmd_line_list = []
                for item in has_exec['args'][1]:
                    cmd_line_list.append(item)

                env_list = []
                for item in has_exec['args'][2]:
                    env_list.append(item)
                
                new_process = {
                    "pid": new_tid,
                    "path": exec_path[1:-1],
                    "command_line": shlex.join(cmd_line_list),
                    "env": env_list,
                    "libraries": [],
                    "threads": {
                        new_tid: process_map[new_tid]
                    },
                    "child_processes": [],
                    "files_to_extract": []
                }
                start_proc['child_processes'].append(new_process)
                get_children(new_process, process_map)

            
def get_process_files(process_dict, pwd=None):
    fd_map = {}
    for tid in process_dict["threads"]:
        for syscall in process_dict["threads"][tid]:
            sysname = syscall['syscall']
            args = syscall.get('args', [])
            retval = syscall['return']
            # We need to track our PWD for certain file calls
            if sysname in ('execve', 'execveat', 'fexecve'):
                envp = None
                if syscall['syscall'] == 'execveat':
                    envp = args[-2]
                else:
                    envp = args[-1]
                for env_item in envp:
                    env_split = env_item[1:-1].split("=")
                    if env_split[0] == "PWD" and pwd is None:
                        pwd = env_split[1]
            elif sysname in ("chdir",):
                pwd = args[0][1:-1]
            elif sysname in ('open', 'creat', 'openat', 'openat2'):
                full_path = ""

                if sysname in ("creat", "open"):
                    full_path = args[0][1:-1]
                elif sysname in ("openat", "openat2"):
                    arg_path = args[1][1:-1]
                    if arg_path.startswith("/"):
                        full_path = arg_path
                    else:
                        if args[0] == "AT_FDCWD":
                            full_path = os.path.join(pwd, arg_path)
                        else:
                            full_path = os.path.join(fd_map[0], arg_path)

                if sysname in ('open', 'openat'):
                    if not "O_CREAT" in args[-2]:
                        if " " in retval:
                            fd_map[int(retval.split(" ")[0])] = full_path
                        else:
                            fd_map[int(retval)] = full_path
                        continue
                elif sysname == "openat2":
                    if " " in retval:
                        fd_map[int(retval.split(" ")[0])] = full_path
                    else:
                        fd_map[int(retval)] = full_path
                    pass # TODO
            
                process_dict['files_to_extract'].append(full_path)

    for child_proc in process_dict['child_processes']:
        get_process_files(child_proc, pwd)



def process_strace_calls(strace_file):
    dump_file = open(strace_file)
    dump_data = dump_file.read()
    dump_file.close()

    lines = dump_data.split("\n")


    split_lines = []
    for line in lines:
        if line.strip() == "":
            continue
        split_line = re.sub(r"[ ]{2,}", " ", line).split(" ", maxsplit=2)

        line_data = {
            "tid": int(split_line[0]),
            "time": split_line[1],
        }

        info_data = split_line[2]

        if ") = " in info_data:
            ret_split = info_data.split(") = ")
            line_data['return'] = ret_split[1]
            info_data = ret_split[0]

        if "(" in info_data and " resumed>" not in info_data and not info_data.startswith("+++"):
            info_split = info_data.split("(", maxsplit=1)
            if info_split[0] in IGNORE_SYSCALLS:
                continue
            line_data['syscall'] = info_split[0]
            info_data = info_split[1]

        line_data['raw_info'] = info_data
        split_lines.append(line_data)

    rebuilt_lines = []
    for i in range(len(split_lines)):
        line_split = split_lines[i]
        # print(line_split)

        if line_split['raw_info'].startswith("<... "):
            continue


        # Reconstruct lines that are <unfinished ...> due to thread switching etc.
        ignore = False
        if '<unfinished ...>' in line_split['raw_info']:
            done = False
            
            j = 1
            while j < (len(split_lines)-i)-1 and not done:
                next_line_split = split_lines[i+j]
                if next_line_split['tid'] == line_split['tid']:
                    if next_line_split['raw_info'].startswith("<... "):
                        
                        resume_split = next_line_split['raw_info'].split(" ", maxsplit=2)
                        
                        resumed_syscall = resume_split[1]
                        if resumed_syscall == line_split['syscall']:
                            line_split['return'] = next_line_split['return']
                            line_split['raw_info'] = line_split['raw_info'].replace("<unfinished ...>", "")
                            # If the matching resumed syscall has "unfinished" in it, we ignore the whole syscall since
                            # we're missing stuff.
                            if "<unfinished ...>" in resume_split[2]:
                                ignore = True
                            else:
                                line_split['raw_info'] += resume_split[2][len("resumed>"):].replace("<unfinished ...>", "")
                            done = True
                j+=1
        if not ignore:
            rebuilt_lines.append(line_split)

    # Parse objects and split up arguments
    for i in range(len(rebuilt_lines)):
        if rebuilt_lines[i]['raw_info'].startswith("+++ exited"):
            exit_split = rebuilt_lines[i]['raw_info'].split(" ")
            exit_code = exit_split[3]
            rebuilt_lines[i]['return'] = exit_code
            rebuilt_lines[i]['syscall'] = "process:exit"
        elif rebuilt_lines[i]['raw_info'].startswith("+++ killed"):
            exit_split = rebuilt_lines[i]['raw_info'].split(" ")
            exit_code = exit_split[3]
            rebuilt_lines[i]['return'] = exit_code
            rebuilt_lines[i]['syscall'] = "process:fault"
        elif rebuilt_lines[i]['raw_info'].startswith("---"):
            sig_split = rebuilt_lines[i]['raw_info'].split(" ", maxsplit=2)
            signal = sig_split[1]
            rebuilt_lines[i]['return'] = None
            rebuilt_lines[i]['args'] = parse_objects(sig_split[2][:-3].strip())
            rebuilt_lines[i]['syscall'] = "signal:" + signal
        else:
            # Start by breaking up raw info into different args.
            arg_list = comma_split(rebuilt_lines[i]['raw_info'])

            for j in range(len(arg_list)):
                arg_list[j] = parse_objects(arg_list[j])

            rebuilt_lines[i]['args'] = arg_list
        del rebuilt_lines[i]['raw_info']
    
    # Build process tree

    process_map = {}
    process_list = []
    seen_list = []

    for line in rebuilt_lines:
        if line['tid'] not in process_map:
            process_map[line['tid']] = []
            seen_list.append(line['tid'])
        process_map[line['tid']].append(line)

    first_pid = seen_list[0]
    first_proc = {
        "pid": first_pid,
        "path": "",
        "libraries": [],
        "threads": {
            first_pid: process_map[first_pid]
        },
        "child_processes": [],
        "files_to_extract": []
    }

    exec_call = get_exec_call(process_map[first_pid])
    # print(exec_call)
    first_proc['path'] = exec_call['args'][0][1:-1]
    del process_map[first_pid]

    get_children(first_proc, process_map)

    # Process each file for written files

    get_process_files(first_proc)
    
    return [first_proc]


class QEMUBase(BaseContainer):

    def __init__(self, client, container_name, name, network=True, logger=None):
        super().__init__(client, container_name, name, network=network, logger=logger)
        self._syscall_map = {}
        self._string_map = {}

        # my_dir = os.path.dirname(os.path.realpath(__file__))
        # data_path = os.path.join(my_dir, "..", "data", "interesting_syscalls.txt")
        # self._syscall_map = load_syscall_map(data_path)

    def _extract_files(self, proc_data, job_obj : MinkeJob):
        for extract_file in proc_data['files_to_extract']:
            self._logger.info("Found written file %s", extract_file)

            extract_path = f"{extract_file}"

          
                
            filename = os.path.basename(extract_path)
            self.extract(extract_path, job_obj.dropped_dir)
            new_filename = f"{job_obj.dropped_dir}/{filename}"
            if os.path.exists(new_filename):
                os.chmod(new_filename, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
                job_obj.add_info('written_files', filename)
            job_obj.save()

        # Extract files from child processes
        for child_proc in proc_data['child_processes']:
            self._extract_files(child_proc, job_obj)

    def process(self, job_obj : MinkeJob):

        username = self.vars['USER']
        execsample = self.vars['SAMPLENAME']
        
        log_file = self.vars['LOG']

        self.extract(f'/tmp/{log_file}', job_obj.base_dir)

        self._logger.info("Processing QEMU dump...")
        proc_list = process_strace_calls(os.path.join(job_obj.base_dir, log_file))

        self._logger.info("Extracting files...")
        for proc in proc_list:
            self._extract_files(proc, job_obj)
        
        out_data = {
            "operating_system": "linux",
            "processes": proc_list
        }

        self._logger.info("Saving syscalls...")

        output_file = open(os.path.join(job_obj.base_dir, "syscalls_flattened.json"), "w+")
        json.dump(out_data, output_file, indent="    ")
        output_file.close()


        return True
    
class QEMUMIPSELContainer(QEMUBase):

    DOCKERFILE_DIR = "qemu-mipsel"

    def __init__(self, client, name, logger=None):
        super().__init__(client, 'minke-qemu-mipsel', name, network=True, logger=logger)

    def can_process(self, mimetype, file_id, filename):
        if mimetype in ('application/x-executable',) and "lsb executable" in file_id and ("mips32" in file_id or ("32-bit" in file_id and "mips" in file_id)):
            return True
        else:
            return False
    
class QEMUARMContainer(QEMUBase):

    DOCKERFILE_DIR = "qemu-arm"

    def __init__(self, client, name, logger=None):
        super().__init__(client, 'minke-qemu-arm', name, network=True, logger=logger)

    def can_process(self, mimetype, file_id, filename):
        if mimetype in ('application/x-executable',) and "lsb executable" in file_id and "arm" in file_id and "32-bit" in file_id:
            return True
        else:
            return False

    
class QEMUAARCH64Container(QEMUBase):

    DOCKERFILE_DIR = "qemu-aarch64"

    def __init__(self, client, name, logger=None):
        super().__init__(client, 'minke-qemu-aarch64', name, network=True, logger=logger)

    def can_process(self, mimetype, file_id, filename):
        if mimetype in ('application/x-executable',) and "lsb executable" in file_id and "aarch64" in file_id and "64-bit" in file_id:
            return True
        else:
            return False

    
class QEMUPowerPCContainer(QEMUBase):

    DOCKERFILE_DIR = "qemu-powerpc"

    def __init__(self, client, name, logger=None):
        super().__init__(client, 'minke-qemu-powerpc', name, network=True, logger=logger)

    def can_process(self, mimetype, file_id, filename):
        if mimetype in ('application/x-executable',) and "msb executable" in file_id and "powerpc" in file_id and "32-bit" in file_id:
            return True
        else:
            return False
    
class QEMUSPARCContainer(QEMUBase):

    DOCKERFILE_DIR = "qemu-sparc"

    def __init__(self, client, name, logger=None):
        super().__init__(client, 'minke-qemu-sparc', name, network=True, logger=logger)

    def can_process(self, mimetype, file_id, filename):
        if mimetype in ('application/x-executable',) and "msb executable" in file_id and "sparc" in file_id and "32-bit" in file_id:
            return True
        else:
            return False
    
class QEMUSH4Container(QEMUBase):

    DOCKERFILE_DIR = "qemu-sh4"

    def __init__(self, client, name, logger=None):
        super().__init__(client, 'minke-qemu-sh4', name, network=True, logger=logger)

    def can_process(self, mimetype, file_id, filename):
        if mimetype in ('application/x-executable',) and "lsb executable" in file_id and "renesas sh" in file_id and "32-bit" in file_id:
            return True
        else:
            return False

class QEMUi386Container(QEMUBase):

    DOCKERFILE_DIR = "qemu-i386"

    def __init__(self, client, name, logger=None):
        super().__init__(client, 'minke-qemu-i386', name, network=True, logger=logger)

    def can_process(self, mimetype, file_id, filename):
        if mimetype in ('application/x-executable',) and "lsb executable" in file_id and "intel" in file_id and "32-bit" in file_id:
            return True
        else:
            return False

class QEMUx8664Container(QEMUBase):

    DOCKERFILE_DIR = "qemu-x86_64"

    def __init__(self, client, name, logger=None):
        super().__init__(client, 'minke-qemu-x86_64', name, network=True, logger=logger)

    def can_process(self, mimetype, file_id, filename):
        if mimetype in ('application/x-executable',) and "lsb" in file_id and "x86-64" in file_id and "64-bit" in file_id:
            return True
        else:
            return False
        
class QEMUs390xContainer(QEMUBase):

    DOCKERFILE_DIR = "qemu-s390x"

    def __init__(self, client, name, logger=None):
        super().__init__(client, 'minke-qemu-s390x', name, network=True, logger=logger)

    def can_process(self, mimetype, file_id, filename):
        if mimetype in ('application/x-executable',) and "msb" in file_id and "ibm s/390" in file_id and "64-bit" in file_id:
            return True
        else:
            return False