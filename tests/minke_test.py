import shutil
import os
import time

import pytest
import minke.server
from tests.helpers import any_thread_has_api_call, has_child_process

@pytest.fixture()
def app():
    app = minke.server.app
    app.config.update({
        "TESTING": True,
    })

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
    return app.test_client()

# @pytest.fixture()
# def runner(app):
#     return app.test_cli_runner()

def test_index(client):
    response = client.get("/")
    assert b"<h2>Welcome to Minke Framework!</h2>" in response.data

def test_version(client):
    response = client.get("/api/v1/version")
    assert response.json['ok'] == True
    assert response.json['result']['version'] is not None

def test_jobs_count_empty(client):
    response = client.get("/api/v1/jobs/count")
    assert response.json['ok'] == True
    assert response.json['result']['count'] == 0

def test_jobs_list_empty(client):
    response = client.get("/api/v1/jobs")
    assert response.json['ok'] == True
    assert len(response.json['result']['jobs']) == 0

def test_job_info_invalid(client):
    response = client.get("/api/v1/jobs/notuuid/info")
    assert response.json['ok'] == False
    assert response.json['error'] == "Invalid UUID"

    response = client.get("/api/v1/jobs/635b4bba-8f1a-4bcb-9296-decfe02c60d1/info")
    assert response.json['ok'] == False
    assert response.json['error'] == "Job not found"

def test_job_syscalls_invalid(client):
    response = client.get("/api/v1/jobs/notuuid/syscalls")
    assert response.json['ok'] == False
    assert response.json['error'] == "Invalid UUID"

    response = client.get("/api/v1/jobs/635b4bba-8f1a-4bcb-9296-decfe02c60d1/syscalls")
    assert response.json['ok'] == False
    assert response.json['error'] == "Job not found"

def test_job_logs_invalid(client):
    response = client.get("/api/v1/jobs/notuuid/logs")
    assert response.json['ok'] == False
    assert response.json['error'] == "Invalid UUID"

    response = client.get("/api/v1/jobs/635b4bba-8f1a-4bcb-9296-decfe02c60d1/logs")
    assert response.json['ok'] == False
    assert response.json['error'] == "Job not found"

def test_job_networking_invalid(client):
    response = client.get("/api/v1/jobs/notuuid/logs")
    assert response.json['ok'] == False
    assert response.json['error'] == "Invalid UUID"

    response = client.get("/api/v1/jobs/635b4bba-8f1a-4bcb-9296-decfe02c60d1/logs")
    assert response.json['ok'] == False
    assert response.json['error'] == "Job not found"

def test_submit_1(client):
    file_dir = os.path.abspath(os.path.dirname(__file__))
    
    sample_path = os.path.join(file_dir, "builder/out/test.x86-64.exe")
    assert os.path.exists(sample_path)

    postdata = {}
    postdata['sample'] = (open(sample_path, "rb"), 'test.x86-64.exe')
    response = client.post("/api/v1/samples/submit", data=postdata,
        content_type='multipart/form-data'
    )
    assert response.json['ok'] == True
    assert response.json['result']['job_id'] is not None

    job_uuid = response.json['result']['job_id']

    response = client.get("/api/v1/jobs/count")
    assert response.json['ok'] == True
    assert response.json['result']['count'] == 1

    response = client.get(f"/api/v1/jobs/{job_uuid}/info")
    assert response.json['ok'] == True
    assert response.json['result']['info']['complete'] == False
    assert response.json['result']['config'] is not None
    
    time.sleep(6 * 60)

    response = client.get(f"/api/v1/jobs/{job_uuid}/info")
    assert response.json['ok'] == True
    assert response.json['result']['info']['complete'] == True
    assert response.json['result']['config'] is not None

    response = client.get(f"/api/v1/jobs/{job_uuid}/networking")
    assert response.json['ok'] == True

    response = client.get(f"/api/v1/jobs/{job_uuid}/logs")
    assert response.json['ok'] == True
    assert len(response.json['result']['logs']) > 0

    response = client.get(f"/api/v1/jobs/{job_uuid}/syscalls")
    assert response.json['ok'] == True
    processes = response.json['result']['processes']

    assert any_thread_has_api_call(processes[0], "msvcrt.puts", subcall=False, args=['"Hello there from x86-64"'])
    assert any_thread_has_api_call(processes[0], "ws2_32.wsastartup", subcall=False)
    assert any_thread_has_api_call(processes[0], "ws2_32.getaddrinfo", subcall=False)
    assert any_thread_has_api_call(processes[0], "kernel32.createfilew", subcall=False)
    assert has_child_process(processes[0], "cmd.exe")
    assert has_child_process(processes[0], "notepad.exe")

    response = client.get(f"/api/v1/jobs/{job_uuid}/networking")
    assert response.json['ok'] == True
    assert "192.168.122.198" in response.json['result']['ip_list']
    assert "tcp|192.168.122.198|8080" in response.json['result']['connections']

    response = client.get(f"/api/v1/jobs/{job_uuid}/logs")
    assert response.json['ok'] == True
    assert "ports4u-container.log" in response.json['result']['logs']

