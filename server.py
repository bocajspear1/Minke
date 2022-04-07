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

from images.detect import DetectContainer
from images.winelyze import WinelyzeContainer
from images.extract import ExtractContainer
from images.config import get_config, set_config

from flask import Flask, g, jsonify, current_app, request, render_template, send_from_directory
from werkzeug.utils import secure_filename

VERSION = '0.0.1'

from flask.logging import default_handler

SAMPLE_DIR= "./samples/"

class SampleThread (threading.Thread):
    def __init__(self, id, queue):
        threading.Thread.__init__(self)
        self._queue = queue 
        self._id = id
        self.daemon = True

    def run(self):
        while True:
            uuid = self._queue.get(block=True)
            print(uuid)
            job_dir = os.path.join(SAMPLE_DIR, uuid)
            file_dir = os.path.join(job_dir, "files")

            config = get_config(job_dir)
            execname = config['start-exec'] 

            sample_files = os.listdir(file_dir)

            for file_item in sample_files:
                if file_item.endswith(".zip"):
                    app.logger.info("Detected compressed file %s, extracting...", file_item)
                    extract_cont = ExtractContainer("extract-" + uuid)
                    extract_cont.start(os.path.join(job_dir, "files"), {
                        "EXECSAMPLE": execname
                    })
                    time.sleep(3)
                    extract_cont.process(job_dir)

            if execname.endswith(".zip"):
                new_sample_files = os.listdir(file_dir)
                new_sample_files.remove(execname)

                if len(new_sample_files) > 1:
                    app.logger.error("Multiple files, but no execname set. Cannot continue")
                    continue
                elif len(new_sample_files) == 0:
                    app.logger.error("Failed to extract files. Cannot continue")
                    continue
                else:
                    execname = new_sample_files[0]


            die_cont = DetectContainer('die-' + uuid)

            print(execname)

            die_cont.start(os.path.join(job_dir, "files"), {
                "EXECSAMPLE": execname
            })

            time.sleep(4)

            die_data = die_cont.process(job_dir)

            

            container = None

            if die_data['format'] == 'pe':
                container = WinelyzeContainer(f"winelyze-{uuid}", logger=app.logger)

                app.logger.info("Using Winelyze container")
                username = ''.join(random.choice(string.ascii_lowercase) for i in range(5))
                screenshot = ''.join(random.choice(string.ascii_lowercase) for i in range(6))
                log_file = ''.join(random.choice(string.ascii_lowercase) for i in range(8))
                app.logger.debug("exec: %s, user: %s", execname, username)

                container.start(os.path.join(job_dir, "files"), {
                    "SAMPLENAME": execname,
                    "USER": username,
                    "SCREENSHOT": screenshot,
                    "LOG": log_file
                })

            if container is not None:
                container.wait_and_stop()
                container.process(job_dir)
                container.process_network(job_dir)
                app.logger.info("Analysis %s completed", uuid)
            else:
                app.logger.info("No analysis container found")

            time.sleep(.5)

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ['FLASK_KEY']

    with app.app_context():

        app._queue = queue.Queue()
        
        THREAD_COUNT = 4
        app._sample_threads = []
        for i in range(THREAD_COUNT):
            app._sample_threads.append(SampleThread(i, app._queue))

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

@app.route('/api/v1/samples/count', methods = ['GET'])
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

@app.route('/api/v1/_version')
def version():
    return jsonify({
        "ok": True,
        "result": {
            "version": VERSION
        }
    })

@app.route('/api/v1/samples/submit', methods=['POST'])
def sumbit_sample():

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

    new_uuid = uuid.uuid4()

    if multiple and 'exec' not in request.form:
        return jsonify({
            "ok": False,
            "error": "Multiple files submitted, but not start executable set with 'exec'"
        })
    


    

    if not os.path.exists(SAMPLE_DIR):
        os.mkdir(SAMPLE_DIR)

    job_dir = os.path.join(SAMPLE_DIR, str(new_uuid))
    os.mkdir(job_dir)

    sample_dir = os.path.join(job_dir, "files")
    os.mkdir(sample_dir)

    if multiple:
        execname = secure_filename(request.form['exec'])
        set_config(job_dir, {
            "start-exec": execname
        })
    else:
        execname = secure_filename(file_list[0].filename)
        set_config(job_dir, {
            "start-exec": execname
        })

    for file in file_list:
        filename = secure_filename(file.filename)
        file_path = os.path.join(sample_dir, filename)
        file.save(file_path)
        os.chmod(file_path, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)


    app._queue.put(str(new_uuid))

    return jsonify({
        "ok": True,
        "result": {
            "job_id": str(new_uuid)
        }
    })

@app.route('/api/v1/job/<uuid>/info', methods=['GET'])
def get_job_info(uuid):
    new_uuid = ""
    try:
        new_uuid = str(uuid.UUID(uuid))
    except:
        return jsonify({
            "ok": False,
            "error": "Invalid UUID"
        })
    job_dir = os.path.join(SAMPLE_DIR, str(new_uuid))
    if not os.path.exists(job_dir):
        return jsonify({
            "ok": False,
            "error": "Job not found"
        })

if __name__== '__main__':
    app.run()