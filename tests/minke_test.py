import shutil
import os
import time

import pytest
import minke.main
from tests.helpers import any_thread_has_api_call, has_child_process, dump_json

from fastapi.testclient import TestClient

@pytest.fixture()
def app():
    app = minke.main.app

    # other setup can go here
    if os.path.exists("./samples"):
        shutil.move("./samples", "./samples-backup")
        os.mkdir("./samples")

    yield app

    if os.path.exists("./samples-backup"):
        if os.path.exists("./samples-last"):
            shutil.rmtree("./samples-last")
        shutil.move("./samples", "./samples-last")
        shutil.move("./samples-backup", "./samples")

    # clean up / reset resources here

@pytest.fixture()
def client(app):
    client = TestClient(app)
    client.submission_count = 0
    return client

# @pytest.fixture()
# def runner(app):
#     return app.test_cli_runner()

def test_api_version(client):
    response = client.get("/api/v1/version")
    assert response.json()['ok'] == True, response.json()
    assert response.json()['result']['version'] is not None, response.json()

def test_api_jobs_count_empty(client):
    response = client.get("/api/v1/jobs/count")
    assert response.json()['ok'] == True, response.json()
    assert response.json()['result']['count'] == 0, response.json()

def test_api_jobs_list_empty(client):
    response = client.get("/api/v1/jobs")
    assert response.json()['ok'] == True, response.json()
    assert len(response.json()['result']['jobs']) == 0, response.json()

def test_api_job_info_invalid(client):
    response = client.get("/api/v1/jobs/notuuid/info")
    assert response.status_code == 400
    assert response.json()['detail'] == "Invalid UUID", response.json()

    response = client.get("/api/v1/jobs/635b4bba-8f1a-4bcb-9296-decfe02c60d1/info")
    assert response.status_code == 404
    assert response.json()['detail'] == "Job does not exist", response.json()

def test_api_job_syscalls_invalid(client):
    response = client.get("/api/v1/jobs/notuuid/syscalls")
    assert response.status_code == 400
    assert response.json()['detail'] == "Invalid UUID"

    response = client.get("/api/v1/jobs/635b4bba-8f1a-4bcb-9296-decfe02c60d1/syscalls")
    assert response.status_code == 404
    assert response.json()['detail'] == "Job does not exist"

def test_api_job_logs_invalid(client):
    response = client.get("/api/v1/jobs/cheese/logs")
    assert response.status_code == 400
    assert response.json()['detail'] == "Invalid UUID"

    response = client.get("/api/v1/jobs/635b4bba-8f1a-4bcb-9296-decfe02c60d1/logs")
    assert response.status_code == 404
    assert response.json()['detail'] == "Job does not exist"

def test_api_job_networking_invalid(client):
    response = client.get("/api/v1/jobs/':asfsd'/logs")
    assert response.status_code == 400
    assert response.json()['detail'] == "Invalid UUID"

    response = client.get("/api/v1/jobs/635b4bba-8f1a-4bcb-9296-decfe02c60d1/logs")
    assert response.status_code == 404
    assert response.json()['detail'] == "Job does not exist"

def test_api_submit_1(client):
    file_dir = os.path.abspath(os.path.dirname(__file__))
    
    sample_path = os.path.join(file_dir, "files", "test.x86-64.exe")
    assert os.path.exists(sample_path)

    postdata = {}
    files = {"sample": open(sample_path, "rb")}
    # postdata['sample'] = (open(sample_path, "rb"), 'test.x86-64.exe')
    response = client.post("/api/v1/samples/submit", data=postdata, files=files)
    assert response.json()['ok'] == True
    assert response.json()['result']['job_id'] is not None

    client.submission_count += 1

    job_uuid = response.json()['result']['job_id']

    response = client.get("/api/v1/jobs/count")
    assert response.json()['ok'] == True
    assert response.json()['result']['count'] == 1

    response = client.get(f"/api/v1/jobs/{job_uuid}/info")
    assert response.json()['ok'] == True
    assert response.json()['result']['info']['complete'] == False
    assert response.json()['result']['config'] is not None
    
    time.sleep(6 * 60)

    response = client.get(f"/api/v1/jobs/{job_uuid}/info")
    assert response.json()['ok'] == True
    assert response.json()['result']['info']['complete'] == True
    assert response.json()['result']['config'] is not None

    response = client.get(f"/api/v1/jobs/{job_uuid}/networking")
    assert response.json()['ok'] == True

    response = client.get(f"/api/v1/jobs/{job_uuid}/logs")
    assert response.json()['ok'] == True
    assert len(response.json()['result']['logs']) > 0

    response = client.get(f"/api/v1/jobs/{job_uuid}/syscalls")
    assert response.json()['ok'] == True
    processes = response.json()['result']['processes']

    assert any_thread_has_api_call(processes[0], "msvcrt.puts", subcall=False, args=['"Hello there from x86-64"'])
    assert any_thread_has_api_call(processes[0], "ws2_32.wsastartup", subcall=False)
    assert any_thread_has_api_call(processes[0], "ws2_32.getaddrinfo", subcall=False)
    assert any_thread_has_api_call(processes[0], "kernel32.createfilew", subcall=False)
    assert has_child_process(processes[0], "cmd.exe")
    assert has_child_process(processes[0], "notepad.exe")

    response = client.get(f"/api/v1/jobs/{job_uuid}/networking")
    assert response.json()['ok'] == True
    assert "192.168.122.198" in response.json()['result']['ip_list']
    assert "tcp|192.168.122.198|8080" in response.json()['result']['connections']

    response = client.get(f"/api/v1/jobs/{job_uuid}/pcap")
    assert response.status_code == 200

    response = client.get(f"/api/v1/jobs/{job_uuid}/logs")
    assert response.json()['ok'] == True
    assert "ports4u-container.log" in response.json()['result']['logs']


def test_api_submit_linux(client):
    file_dir = os.path.abspath(os.path.dirname(__file__))

    counter = 1

    for file_name in ("test.arm.elf", "test.powerpc.elf", "test.mipsel.elf"):
        
        sample_path = os.path.join(file_dir, "files", file_name)
        assert os.path.exists(sample_path)

        postdata = {}
        files = {"sample": open(sample_path, "rb")}
        
        response = client.post("/api/v1/samples/submit", data=postdata, files=files)
        assert response.json()['ok'] == True
        assert response.json()['result']['job_id'] is not None

        client.submission_count += 1

        job_uuid = response.json()['result']['job_id']

        response = client.get("/api/v1/jobs/count")
        assert response.json()['ok'] == True
        assert response.json()['result']['count'] == client.submission_count

        response = client.get(f"/api/v1/jobs/{job_uuid}/info")
        assert response.json()['ok'] == True
        assert response.json()['result']['info']['complete'] == False
        assert response.json()['result']['config'] is not None
        
        time.sleep(2.5 * 60)

        response = client.get(f"/api/v1/jobs/{job_uuid}/info")
        assert response.json()['ok'] == True
        assert response.json()['result']['info']['complete'] == True
        assert response.json()['result']['config'] is not None

        response = client.get(f"/api/v1/jobs/{job_uuid}/networking")
        assert response.json()['ok'] == True

        response = client.get(f"/api/v1/jobs/{job_uuid}/logs")
        assert response.json()['ok'] == True
        assert len(response.json()['result']['logs']) > 0

        response = client.get(f"/api/v1/jobs/{job_uuid}/syscalls")
        assert response.json()['ok'] == True
        processes = response.json()['result']['processes']

        dump_json(processes, "mipsle-processes.json")

        assert any_thread_has_api_call(processes[0], "openat", subcall=False, args=[
            "AT_FDCWD",
            "\"/tmp/nothinghere\"",
            "*",
            "*"
        ], name_key="syscall")
        assert any_thread_has_api_call(processes[0], "clone", subcall=False, name_key="syscall")
        assert any_thread_has_api_call(processes[0], "socket", subcall=False, args=[
            "AF_INET",
            "SOCK_STREAM",
            "IPPROTO_IP"
        ], name_key="syscall")
        assert any_thread_has_api_call(processes[0], "connect", subcall=False, name_key="syscall")
        assert has_child_process(processes[0], "touch")
        # assert has_child_process(processes[0], "notepad.exe")

        response = client.get(f"/api/v1/jobs/{job_uuid}/networking")
        assert response.json()['ok'] == True
        assert "192.168.122.95" in response.json()['result']['ip_list']
        assert "tcp|192.168.122.95|8080" in response.json()['result']['connections']

        response = client.get(f"/api/v1/jobs/{job_uuid}/logs")
        assert response.json()['ok'] == True
        assert "ports4u-container.log" in response.json()['result']['logs']

        response = client.get(f"/api/v1/jobs/{job_uuid}/pcap")
        assert response.status_code == 200, f"Got response '{response.text}'"
