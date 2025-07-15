import os
import queue
import json
import logging
import uuid
import shutil
import time

from typing import Union, List

from fastapi import File, Form, UploadFile, HTTPException, Request, Depends, Security, APIRouter
from fastapi.security import APIKeyHeader
from fastapi.responses import PlainTextResponse, FileResponse
from typing_extensions import Annotated



from minke.job import MinkeJob
from minke.helper import filepath_clean
from minke.vars import *

v1_router = APIRouter()


@v1_router.get('/version')
def version():
    """
    Returns the version of the Minke server
    """
    return {
        "ok": True,
        "result": {
            "version": VERSION
        }
    }


@v1_router.get('/jobs')
def get_job_list():
    """
    Gets list of job UUIDs
    """
    sample_list_raw = os.listdir(SAMPLE_DIR)

    sample_list = []
    for item in sample_list_raw:
        if item != ".." or item != ".":
            sample_list.append(item)

    return {
        "ok": True,
        "result": {
            "jobs": sample_list
        }
    }

@v1_router.get('/jobs/count')
def sample_count():
    """
    Get count of samples run by this Minke server
    """

    sample_count = 0
    if os.path.exists(SAMPLE_DIR):
        sample_count = len(os.listdir(SAMPLE_DIR))

    return {
        "ok": True,
        "result": {
            "count": sample_count
        }
    }

@v1_router.get("/job/{job_uuid}")
def get_job(job_uuid : str):
    """
    Gets information about the job specified by UUID. Data is under the "result" key, with two keys
    "info" and "config" which gives information about the job (start time, files, written/dumped files, system IP address, etc)
    and the job's configuration (the main execution file and other options) respectively.
    """
    new_uuid = ""
    try:
        new_uuid = str(uuid.UUID(job_uuid))
    except:
        raise HTTPException(400, detail="Invalid UUID")

    job_obj = MinkeJob(SAMPLE_DIR, new_uuid)
    if not job_obj.exists():
        raise HTTPException(404, detail="Job does not exist")
    else:
        job_obj.load()
        return {
            "ok": True,
            "result": {
                "info": job_obj.get_info(),
                "config": job_obj.get_config()
            }
        }

@v1_router.post("/samples/submit")
def submit_file(
    request: Request,
    sample: Union[None, UploadFile] = None,
    samples: Union[None, List[UploadFile]] = None,
    arguments: Annotated[str, Form()] = None,
    exec: Annotated[str, Form()] = None,
):
    if sample is None and samples is None:  
        raise HTTPException(400, detail="No sample submitted in 'sample' or 'samples' parameters")

    if sample is not None and samples is None:
        samples = [sample]

    new_job = MinkeJob.new(SAMPLE_DIR)
    new_job.load()

    if len(samples) > 1:
        if exec is None:
            HTTPException(400, detail="Multiple files submitted, but no start executable set with 'exec'")
    
        exec_name = filepath_clean(exec)
        new_job.set_config_value(START_EXEC_KEY, exec_name)
    else:
        exec_name = filepath_clean(samples[0].filename)
        new_job.set_config_value(START_EXEC_KEY, exec_name)

    print(arguments)
    if arguments is not None:
        print("Got args")
        new_job.set_config_value(ARGUMENTS_KEY, arguments)

    for sample_item in samples:
        filename = filepath_clean(sample_item.filename)
        new_path = new_job.add_file(filename)
        with open(new_path, "wb") as job_file:
            shutil.copyfileobj(sample_item.file, job_file)
        new_job.setup_file(filename)

    new_job.set_info('start_time', time.time())
    new_job.set_info('complete', False)
    new_job.save()

    request.app._queue.put(new_job)

    return {
        "ok": True,
        "result": {
            "job_id": new_job.uuid
        }
    }


@v1_router.get("/jobs/{job_uuid}/info")
def get_job_info(job_uuid : str):
    new_uuid = ""
    try:
        new_uuid = str(uuid.UUID(job_uuid))
    except:
        raise HTTPException(400, detail="Invalid UUID")

    job_obj = MinkeJob(SAMPLE_DIR, new_uuid)
    if not job_obj.exists():
        raise HTTPException(404, detail="Job does not exist")
    else:
        job_obj.load()
        return {
            "ok": True,
            "result": {
                "info": job_obj.get_info(),
                "config": job_obj.get_config()
            }
        }
    
@v1_router.get("/jobs/{job_uuid}/syscalls")
def get_job_syscalls(job_uuid : str):
    new_uuid = ""
    try:
        new_uuid = str(uuid.UUID(job_uuid))
    except:
        raise HTTPException(400, detail="Invalid UUID")

    job_obj = MinkeJob(SAMPLE_DIR, new_uuid)
    if not job_obj.exists():
        raise HTTPException(404, detail="Job does not exist")
    else:
        syscall_data = job_obj.get_flattened_syscalls()
        return {
            "ok": True,
            "result": syscall_data
        }


@v1_router.get("/jobs/{job_uuid}/logs")
def get_job_logs(job_uuid : str):
    new_uuid = ""
    try:
        new_uuid = str(uuid.UUID(job_uuid))
    except:
        raise HTTPException(400, detail="Invalid UUID")

    job_obj = MinkeJob(SAMPLE_DIR, new_uuid)
    if not job_obj.exists():
        raise HTTPException(404, detail="Job does not exist")
    else:
        
        return {
            "ok": True,
            "result": {
                "logs": job_obj.list_logs()
            }
        }
    
@v1_router.get("/jobs/{job_uuid}/logs/{log_name}")
def get_job_log_data(job_uuid : str, log_name : str):
    new_uuid = ""
    try:
        new_uuid = str(uuid.UUID(job_uuid))
    except:
        raise HTTPException(400, detail="Invalid UUID")

    job_obj = MinkeJob(SAMPLE_DIR, new_uuid)
    if not job_obj.exists():
        raise HTTPException(404, detail="Job does not exist")
    else:
        log_data = job_obj.get_log(log_name)
        if log_data is None:
            raise HTTPException(404, detail="Log does not exist")
        else:
            return PlainTextResponse(log_data)

@v1_router.get("/jobs/{job_uuid}/pcap")
def get_job_pcap(job_uuid):
    new_uuid = ""
    try:
        new_uuid = str(uuid.UUID(job_uuid))
    except:
        raise HTTPException(400, detail="Invalid UUID")
    
    job_obj = MinkeJob(SAMPLE_DIR, new_uuid)
    if not job_obj.exists():
        raise HTTPException(404, detail="Job does not exist")
    else:
        job_obj.load()
        pcap_path = os.path.join(job_obj.base_dir, "traffic.pcap")
        if not os.path.exists(pcap_path):
            raise HTTPException(404, detail="PCAP does not exist")
        else:
            return FileResponse(pcap_path)

@v1_router.get("/jobs/{job_uuid}/networking")
def get_job_networking(job_uuid):
    new_uuid = ""
    try:
        new_uuid = str(uuid.UUID(job_uuid))
    except:
        raise HTTPException(400, detail="Invalid UUID")
    
    job_obj = MinkeJob(SAMPLE_DIR, new_uuid)
    if not job_obj.exists():
        raise HTTPException(404, detail="Job does not exist")
    else:
        job_obj.load()
        return {
            "ok": True,
            "result": {
                "connections": job_obj.get_network_connections(),
                "ip_list": job_obj.get_ip_list(),
                "domains": job_obj.get_domains(),
                "net_data": job_obj.get_network_data()
            }
        }

@v1_router.get("/jobs/{job_uuid}/screenshots")
def get_job_screenshots(job_uuid):
    new_uuid = ""
    try:
        new_uuid = str(uuid.UUID(job_uuid))
    except:
        raise HTTPException(400, detail="Invalid UUID")
    
    job_obj = MinkeJob(SAMPLE_DIR, new_uuid)
    if not job_obj.exists():
        raise HTTPException(404, detail="Job does not exist")
    else:
        job_obj.load()
        screenshot_list = os.listdir(job_obj.screenshot_dir)
        screenshot_list.sort()
        return {
            "ok": True,
            "result": {
                "screenshots": screenshot_list
            }
        }

@v1_router.get("/jobs/{job_uuid}/screenshots/{screenshot}")
def get_job_screenshot_image(uuid_str : str, screenshot : str):
    new_uuid = ""
    try:
        new_uuid = str(uuid.UUID(uuid_str))
    except:
        raise HTTPException(400, detail="Invalid UUID")
    
    job_obj = MinkeJob(SAMPLE_DIR, new_uuid)
    if not job_obj.exists():
        raise HTTPException(404, detail="Job does not exist")
    else:
        job_obj.load()
        screenshot_path = job_obj.get_screenshot_path(screenshot)
        if screenshot_path is None:
            raise HTTPException(404, detail="Screenshot does not exist")
        else:
            return FileResponse(screenshot_path)
        


@v1_router.get("/jobs/{job_uuid}/dropped")
def get_job_dropped(job_uuid : str):
    new_uuid = ""
    try:
        new_uuid = str(uuid.UUID(job_uuid))
    except:
        raise HTTPException(400, detail="Invalid UUID")

    job_obj = MinkeJob(SAMPLE_DIR, new_uuid)
    if not job_obj.exists():
        raise HTTPException(404, detail="Job does not exist")
    else:
        return {
            "ok": True,
            "result": {
                "logs": job_obj.list_dropped()
            }
        }
    
@v1_router.get("/jobs/{job_uuid}/dropped/{dropped_name}")
def get_job_dropped_file(job_uuid : str, dropped_name : str):
    new_uuid = ""
    try:
        new_uuid = str(uuid.UUID(job_uuid))
    except:
        raise HTTPException(400, detail="Invalid UUID")

    job_obj = MinkeJob(SAMPLE_DIR, new_uuid)
    if not job_obj.exists():
        raise HTTPException(404, detail="Job does not exist")
    else:
        dropped_path = job_obj.get_dropped_file_path(dropped_name)
        if dropped_path is None:
            raise HTTPException(404, detail="Log does not exist")
        else:
            return FileResponse(dropped_path)

