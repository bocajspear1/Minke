import os
import json

import pytest
from minke.containers.winelyze import process_wine_calls, flatten_process_syscalls, load_syscall_map
from minke.containers.qemu import process_strace_calls
from tests.helpers import any_thread_has_api_call, has_child_process, in_order, thread_has_api_call, dump_json



def test_winelyze_process_meterpreter():
    file_dir = os.path.abspath(os.path.dirname(__file__))
    
    syscalls_path = os.path.join(file_dir, "files/meterpreter.winedump")
    assert os.path.exists(syscalls_path)

    meterpreter_results = process_wine_calls(syscalls_path)

    assert in_order(meterpreter_results[0]) == True

    assert any_thread_has_api_call(meterpreter_results[0], "wininet.httpsendrequesta")
    assert any_thread_has_api_call(meterpreter_results[0], "wininet.httpopenrequesta", args=[
        "00000002","00000000",'"/Osbuoc2huAoDTwJNa8y2lQeMKMMXqgZgjZUbwE-w91C-pzT0kirshfRuzg7OBTXdzgB8BEA9j8VtYg1Cl2iVQZNP4LtPl0PVtXnQIFBT"',"00000000","00000000","00000000","*","00000000"
    ])
    assert any_thread_has_api_call(meterpreter_results[0], "wininet.internetconnecta", args=[
        "00000001",'"8.7.6.5"',"*","00000000","00000000","00000003","00000000","00000000"
    ])

    my_dir = os.path.dirname(os.path.realpath(__file__))
    data_path = os.path.join(my_dir, "..", "src", "minke", "data", "interesting_syscalls.txt")
    syscall_map = load_syscall_map(data_path)

    flatten_process_syscalls(syscall_map, meterpreter_results)

    assert any_thread_has_api_call(meterpreter_results[0], "wininet.httpsendrequesta", subcall=False)
    assert any_thread_has_api_call(meterpreter_results[0], "wininet.httpopenrequesta", args=[
        "00000002","00000000",'"/Osbuoc2huAoDTwJNa8y2lQeMKMMXqgZgjZUbwE-w91C-pzT0kirshfRuzg7OBTXdzgB8BEA9j8VtYg1Cl2iVQZNP4LtPl0PVtXnQIFBT"',"00000000","00000000","00000000","84280200","00000000"
    ], subcall=False)
    assert any_thread_has_api_call(meterpreter_results[0], "wininet.internetconnecta", args=[
        "00000001",'"8.7.6.5"',"*","00000000","00000000","00000003","00000000","00000000"
    ], subcall=False)

    # _dump_json(meterpreter_results, "test-dump.json")
    assert in_order(meterpreter_results[0]) == True
    
    # assert False == True

def test_winelyze_process_builder():
    file_dir = os.path.abspath(os.path.dirname(__file__))
    
    syscalls_path = os.path.join(file_dir, "files/builder.winedump")
    assert os.path.exists(syscalls_path)

    builder_results = process_wine_calls(syscalls_path)

    dump_json(builder_results, "builder.json")

    assert in_order(builder_results[0]) == True
    
    assert any_thread_has_api_call(builder_results[0], "ucrtbase.puts", args=['"Hello there from x86-64"'])
    assert any_thread_has_api_call(builder_results[0], "ws2_32.wsastartup")
    assert any_thread_has_api_call(builder_results[0], "ws2_32.getaddrinfo", subcall=False, args=['"192.168.122.198"','"8080"',"7ffffecdfcb0","7ffffecdfca8"])

    my_dir = os.path.dirname(os.path.realpath(__file__))
    data_path = os.path.join(my_dir, "..", "src", "minke", "data", "interesting_syscalls.txt")
    syscall_map = load_syscall_map(data_path)

    flatten_process_syscalls(syscall_map, builder_results)

    dump_json(builder_results, "builder-flat.json")

    assert any_thread_has_api_call(builder_results[0], "ucrtbase.puts", subcall=False, args=['"Hello there from x86-64"'])
    assert any_thread_has_api_call(builder_results[0], "ws2_32.wsastartup", subcall=False)
    assert any_thread_has_api_call(builder_results[0], "ws2_32.getaddrinfo", subcall=False, args=['"192.168.122.198"','"8080"',"7ffffecdfcb0","7ffffecdfca8"])
    assert any_thread_has_api_call(builder_results[0], "kernel32.createfilew", subcall=False, args=[
        '"C:\\test.txt"',
        "c0000000",
        "00000003",
        "*",
        "*",
        "*",
        "00000000"
    ])
    assert has_child_process(builder_results[0], "cmd.exe")
    assert has_child_process(builder_results[0], "notepad.exe")

    # assert False == True

def test_mipsel_strace():
    file_dir = os.path.abspath(os.path.dirname(__file__))
    
    syscalls_path = os.path.join(file_dir, "files/mipsel.strace")
    assert os.path.exists(syscalls_path)

    builder_results = process_strace_calls(syscalls_path)

    # assert in_order(builder_results[0]) == True

    dump_json(builder_results, "strace.json")
    
    # assert thread_has_api_call(244, builder_results[0], "advapi32.regopenkeyexa")
    # assert thread_has_api_call(256, builder_results[0], "advapi32.regopenkeyexa")

    # my_dir = os.path.dirname(os.path.realpath(__file__))
    # data_path = os.path.join(my_dir, "..", "minke", "data", "interesting_syscalls.txt")
    # syscall_map = load_syscall_map(data_path)

    # flatten_process_syscalls(syscall_map, builder_results)

    # assert thread_has_api_call("244", builder_results[0], "advapi32.regopenkeyexa")
    # assert thread_has_api_call("256", builder_results[0], "advapi32.regopenkeyexa")

    # assert False == True