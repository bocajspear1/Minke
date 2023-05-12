import os
import json

import pytest
from minke.containers.winelyze import process_wine_calls, flatten_process_syscalls, load_syscall_map
from tests.helpers import any_thread_has_api_call, has_child_process


def _dump_json(data, name):
    file_dir = os.path.abspath(os.path.dirname(__file__))
    output_file = open(os.path.join(file_dir, name), "w+")
    json.dump(data, output_file, indent="    ")
    output_file.close()

def test_winelyze_process():
    file_dir = os.path.abspath(os.path.dirname(__file__))
    
    syscalls_path = os.path.join(file_dir, "files/meterpreter.winedump")
    assert os.path.exists(syscalls_path)

    meterpreter_results = process_wine_calls(syscalls_path)
    assert any_thread_has_api_call(meterpreter_results[0], "wininet.httpsendrequesta")
    assert any_thread_has_api_call(meterpreter_results[0], "wininet.httpopenrequesta", args=[
        "00000002","00000000",'"/y4l0dLhR98fynPOelrQmgwEJPwUEc3clB9g6"',"00000000","00000000","00000000","84280200","00000000"
    ])
    assert any_thread_has_api_call(meterpreter_results[0], "wininet.internetconnecta", args=[
        "00000001",'"10.10.10.3"',"00000050","00000000","00000000","00000003","00000000","00000000"
    ])

    my_dir = os.path.dirname(os.path.realpath(__file__))
    data_path = os.path.join(my_dir, "..", "minke", "data", "interesting_syscalls.txt")
    syscall_map = load_syscall_map(data_path)

    flatten_process_syscalls(syscall_map, meterpreter_results)

    assert any_thread_has_api_call(meterpreter_results[0], "wininet.httpsendrequesta", subcall=False)
    assert any_thread_has_api_call(meterpreter_results[0], "wininet.httpopenrequesta", args=[
        "00000002","00000000",'"/y4l0dLhR98fynPOelrQmgwEJPwUEc3clB9g6"',"00000000","00000000","00000000","84280200","00000000"
    ], subcall=False)
    assert any_thread_has_api_call(meterpreter_results[0], "wininet.internetconnecta", args=[
        "00000001",'"10.10.10.3"',"00000050","00000000","00000000","00000003","00000000","00000000"
    ], subcall=False)

    # assert False == True

def test_winelyze_process_builder():
    file_dir = os.path.abspath(os.path.dirname(__file__))
    
    syscalls_path = os.path.join(file_dir, "files/builder.winedump")
    assert os.path.exists(syscalls_path)

    builder_results = process_wine_calls(syscalls_path)
    
    assert any_thread_has_api_call(builder_results[0], "msvcrt.puts", args=['"Hello there from x86-64"'])
    assert any_thread_has_api_call(builder_results[0], "ws2_32.wsastartup")
    assert any_thread_has_api_call(builder_results[0], "ws2_32.getaddrinfo", subcall=False, args=['"192.168.122.198"','"8080"',"0065f600","0065f5f8"])

    my_dir = os.path.dirname(os.path.realpath(__file__))
    data_path = os.path.join(my_dir, "..", "minke", "data", "interesting_syscalls.txt")
    syscall_map = load_syscall_map(data_path)

    flatten_process_syscalls(syscall_map, builder_results)

    assert any_thread_has_api_call(builder_results[0], "msvcrt.puts", subcall=False, args=['"Hello there from x86-64"'])
    assert any_thread_has_api_call(builder_results[0], "ws2_32.wsastartup", subcall=False)
    assert any_thread_has_api_call(builder_results[0], "ws2_32.getaddrinfo", subcall=False, args=['"192.168.122.198"','"8080"',"0065f600","0065f5f8"])
    assert any_thread_has_api_call(builder_results[0], "kernel32.createfilew", subcall=False, args=[
        '"C:\\test.txt"',
        "c0000000",
        "00000003",
        "0065f300",
        "00000002",
        "00000080",
        "00000000"
    ])
    assert has_child_process(builder_results[0], "cmd.exe")
    assert has_child_process(builder_results[0], "notepad.exe")

    # assert False == True