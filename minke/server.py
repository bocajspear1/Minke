# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import sys 
import sqlite3
import sys
import logging
import platform
import os
import uuid
import threading
import queue
import time
import stat
import random
import string
import json
from functools import wraps

from minke.containers.winelyze import WinelyzeContainer
from minke.containers.extract import ExtractContainer
from minke.lib.job import MinkeJob

from flask import Flask, g, jsonify, current_app, request, render_template, send_from_directory, make_response, abort
from werkzeug.utils import secure_filename

VERSION = '0.1.1'

from flask.logging import default_handler

SAMPLE_DIR= "./samples/"
START_EXEC_KEY = 'start-exec'
API_TOKEN_HEADER = 'x-api-key'

class SampleThread (threading.Thread):
    def __init__(self, id, queue, config):
        threading.Thread.__init__(self)
        self._queue = queue 
        self._id = id
        self.daemon = True
        self._config = config

    def run(self):
        while True:
            job_obj : MinkeJob = self._queue.get(block=True)
            print(job_obj.uuid)
            # job_dir = os.path.join(SAMPLE_DIR, uuid)
            # file_dir = os.path.join(job_dir, "files")

            
            execname = job_obj.get_config_value(START_EXEC_KEY)
            if execname is None:
                app.logger.error("Got job with not exec-start")
                continue

            sample_files = job_obj.list_files()

            compressed = False

            for file_item in sample_files:
                if job_obj.get_file_type(file_item) in ('application/zip',):
                    compressed = True
                    app.logger.info("Detected compressed file %s, extracting...", file_item)
                    extract_cont = ExtractContainer("extract-" + job_obj.uuid)
                    extract_cont.start(job_obj.files_dir, {
                        "EXECSAMPLE": execname
                    })
                    time.sleep(3)
                    extract_cont.process(job_obj)

                
            if compressed is True:
                new_sample_files = job_obj.list_files()
                new_sample_files.remove(execname)

                if len(new_sample_files) > 1:
                    app.logger.error("Multiple files, but no execname set. Cannot continue")
                    continue
                elif len(new_sample_files) == 0:
                    app.logger.error("Failed to extract files. Cannot continue")
                    continue
                else:
                    execname = new_sample_files[0]
                job_obj.set_config_value(START_EXEC_KEY, execname)
                job_obj.save()


            exec_type = job_obj.get_file_type(execname)

            container = None
            container_name = ""

            if exec_type in ('application/x-dosexec',) :
                container_name = f"winelyze-{job_obj.uuid}"
                container = WinelyzeContainer(container_name, logger=app.logger)

                app.logger.info("Using Winelyze container for sample %s", execname)
                username = self._config['username']

                screenshot = ''.join(random.choice(string.ascii_lowercase) for i in range(6))
                log_file = ''.join(random.choice(string.ascii_lowercase) for i in range(8))
                app.logger.debug("exec: %s, user: %s", execname, username)

                ip_addr = container.start(job_obj.files_dir, {
                    "SAMPLENAME": execname,
                    "USER": username,
                    "SCREENSHOT": screenshot,
                    "LOG": log_file
                })

                job_obj.set_info('ip_addr', ip_addr)
                job_obj.save()

            if container is not None:
                main_logs, network_logs = container.wait_and_stop()
                if main_logs.strip() != "":
                    job_obj.write_log(f"{container_name}.log", main_logs)
                if network_logs.strip() != "":
                    job_obj.write_log(f"ports4u-container.log", network_logs)
                container.process(job_obj)
                container.process_network(job_obj)
                app.logger.info("Analysis %s completed", job_obj.uuid)
                job_obj.set_info('complete', True)
                job_obj.set_info('end_time', time.time())
                job_obj.save()
                del container
            else:
                app.logger.error("No analysis container found")

            time.sleep(.5)



def token_auth(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        token = None

        if request.remote_addr == "127.0.0.1":
            return f(*args, **kwargs)
        
        if API_TOKEN_HEADER in request.headers:
            token = request.headers[API_TOKEN_HEADER]
            if token != app.api_key:
                return jsonify({
                    "ok": False,
                    "error": "Invalid API key"
                })
        else:
            return jsonify({
                "ok": False,
                "error": "API key not set"
            })
        
        return f(*args, **kwargs)
    return decorator

def create_app():

    config_path = "./config.json"
    if 'MINKE_CONFIG_PATH' in os.environ:
        config_path = os.environ['MINKE_CONFIG_PATH']

    config_file = open(config_path, "r")
    config_data = json.loads(config_file.read())
    config_file.close()

    if 'flask_key' not in config_data:
        print("Flask key not set")
        return

    app = Flask(__name__)
    app.secret_key = config_data['flask_key']
    app.api_key = config_data['access_key']

    with app.app_context():

        app._queue = queue.Queue()
        
        THREAD_COUNT = 4
        app._sample_threads = []
        for i in range(THREAD_COUNT):
            app._sample_threads.append(SampleThread(i, app._queue, config_data))

        if os.getenv("MINKE_DEBUG") is not None:
            app.logger.setLevel(logging.DEBUG)
            app.logger.debug("Debugging is on!")
        else:
            app.logger.setLevel(logging.INFO)

        for i in range(THREAD_COUNT):
            app._sample_threads[i].start()
        
        app.logger.info("Server %s started", VERSION)

    return app
       
app = create_app()

@app.route('/', methods = ['GET'])
def index():
    return render_template("index.html")

@app.route('/api/v1/jobs/count', methods = ['GET'])
@token_auth
def sample_count():

    sample_count = 0
    if os.path.exists(SAMPLE_DIR):
        sample_count = len(os.listdir(SAMPLE_DIR))

    return jsonify({
        "ok": True,
        "result": {
            "count": sample_count
        }
    }) 

@app.route('/api/v1/version')
def version():
    return jsonify({
        "ok": True,
        "result": {
            "version": VERSION
        }
    })

@app.route('/api/v1/jobs', methods=['GET'])
@token_auth
def get_job_list():
    sample_list_raw = os.listdir(SAMPLE_DIR)

    sample_list = []
    for item in sample_list_raw:
        if item != ".." or item != ".":
            sample_list.append(item)

    return jsonify({
        "ok": True,
        "result": {
            "jobs": sample_list
        }
    })

@app.route('/api/v1/samples/submit', methods=['POST'])
@token_auth
def sumbit_sample():

    print(request.files)
    if 'sample' not in request.files and 'samples' not in request.files:   
        return jsonify({
            "ok": False,
            "error": "No sample submitted in 'sample' parameter"
        })

    multiple = False

    file_list = request.files.getlist("samples")

    if file_list is not None and len(file_list) > 0:
        app.logger.info("Got multiple files")
        multiple = True
    else:
        app.logger.info("Got single file")
        single_sample = request.files['sample']

        if single_sample.filename == '':
            return jsonify({
                "ok": False,
                "error": "No sample submitted in 'sample' parameter. Name was blank."
            })
        file_list = [single_sample]

    if multiple and 'exec' not in request.form:
        return jsonify({
            "ok": False,
            "error": "Multiple files submitted, but not start executable set with 'exec'"
        })
    

    new_job = MinkeJob.new(SAMPLE_DIR)
    new_job.load()

    if multiple:
        execname = secure_filename(request.form['exec'])
        new_job.set_config_value(START_EXEC_KEY, execname)
    else:
        execname = secure_filename(file_list[0].filename)
        new_job.set_config_value(START_EXEC_KEY, execname)

    for file in file_list:
        filename = secure_filename(file.filename)
        new_path = new_job.add_file(filename)
        file.save(new_path)
        new_job.setup_file(filename)

    new_job.set_info('start_time', time.time())
    new_job.set_info('complete', False)
    new_job.save()

    app._queue.put(new_job)

    return jsonify({
        "ok": True,
        "result": {
            "job_id": new_job.uuid
        }
    })

@app.route('/api/v1/jobs/<uuid_str>/info', methods=['GET'])
@token_auth
def get_job_info(uuid_str):
    new_uuid = ""
    try:
        new_uuid = str(uuid.UUID(uuid_str))
    except:
        return jsonify({
            "ok": False,
            "error": "Invalid UUID"
        })

    job_obj = MinkeJob(SAMPLE_DIR, new_uuid)
    if not job_obj.exists():
        return jsonify({
            "ok": False,
            "error": "Job not found"
        })
    else:
        job_obj.load()
        return jsonify({
            "ok": True,
            "result": {
                "info": job_obj.get_info(),
                "config": job_obj.get_config()
            }
        })

@app.route('/api/v1/jobs/<uuid_str>/syscalls', methods=['GET'])
@token_auth
def get_job_syscalls(uuid_str):
    new_uuid = ""
    try:
        new_uuid = str(uuid.UUID(uuid_str))
    except:
        return jsonify({
            "ok": False,
            "error": "Invalid UUID"
        })

    job_obj = MinkeJob(SAMPLE_DIR, new_uuid)
    if not job_obj.exists():
        return jsonify({
            "ok": False,
            "error": "Job not found"
        })
    else:
        syscall_data = job_obj.get_flattened_syscalls()
        return jsonify({
            "ok": True,
            "result": syscall_data
        })


@app.route('/api/v1/jobs/<uuid_str>/logs', methods=['GET'])
@token_auth
def get_job_logs(uuid_str):
    new_uuid = ""
    try:
        new_uuid = str(uuid.UUID(uuid_str))
    except:
        return jsonify({
            "ok": False,
            "error": "Invalid UUID"
        })

    job_obj = MinkeJob(SAMPLE_DIR, new_uuid)
    if not job_obj.exists():
        return jsonify({
            "ok": False,
            "error": "Job not found"
        })
    else:
        
        return jsonify({
            "ok": True,
            "result": {
                "logs": job_obj.list_logs()
            }
        })

@app.route('/api/v1/jobs/<uuid_str>/logs/<log_name>', methods=['GET'])
@token_auth
def get_job_log_data(uuid_str, log_name):
    new_uuid = ""
    try:
        new_uuid = str(uuid.UUID(uuid_str))
    except:
        return "400: Invalid UUID", 400

    job_obj = MinkeJob(SAMPLE_DIR, new_uuid)
    if not job_obj.exists():
        return "404: Job does not exist", 404
    else:
        log_data = job_obj.get_log(log_name)
        if log_data is None:
            return "404: Log does not exist", 404
        else:
            response = make_response(log_data, 200)
            response.mimetype = "text/plain"
            return response

@app.route('/api/v1/jobs/<uuid_str>/networking', methods=['GET'])
@token_auth
def get_job_networking(uuid_str):
    new_uuid = ""
    try:
        new_uuid = str(uuid.UUID(uuid_str))
    except:
        return jsonify({
            "ok": False,
            "error": "Invalid UUID"
        })

    job_obj = MinkeJob(SAMPLE_DIR, new_uuid)
    if not job_obj.exists():
        return jsonify({
            "ok": False,
            "error": "Job not found"
        })
    else:
        job_obj.load()
        return jsonify({
            "ok": True,
            "result": {
                "connections": job_obj.get_network_connections(),
                "ip_list": job_obj.get_ip_list(),
                "domains": job_obj.get_domains(),
                "net_data": job_obj.get_network_data()
            }
        })

@app.route('/api/v1/jobs/<uuid_str>/screenshots', methods=['GET'])
@token_auth
def get_job_screenshots(uuid_str):
    new_uuid = ""
    try:
        new_uuid = str(uuid.UUID(uuid_str))
    except:
        return jsonify({
            "ok": False,
            "error": "Invalid UUID"
        })

    job_obj = MinkeJob(SAMPLE_DIR, new_uuid)
    if not job_obj.exists():
        return jsonify({
            "ok": False,
            "error": "Job not found"
        })
    else:
        job_obj.load()
        screenshot_list = os.listdir(job_obj.screenshot_dir)
        screenshot_list.sort()
        return jsonify({
            "ok": True,
            "result": {
                "screenshots": screenshot_list
            }
        })

@app.route('/api/v1/jobs/<uuid_str>/screenshots/<screenshot>', methods=['GET'])
@token_auth
def get_job_screenshot_image(uuid_str, screenshot):
    new_uuid = ""
    try:
        new_uuid = str(uuid.UUID(uuid_str))
    except:
        return jsonify({
            "ok": False,
            "error": "Invalid UUID"
        })

    job_obj = MinkeJob(SAMPLE_DIR, new_uuid)
    if not job_obj.exists():
        return jsonify({
            "ok": False,
            "error": "Job not found"
        })
    else:
        job_obj.load()
        screenshot_type, screenshot_data = job_obj.get_screenshot(screenshot)
        if screenshot_data is None:
            return "404: Screenshot does not exist", 404
        else:
            response = make_response(screenshot_data, 200)
            response.mimetype = screenshot_type
            return response
                

if __name__== '__main__':
    
    app.run()