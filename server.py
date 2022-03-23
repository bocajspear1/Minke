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

from images.detect import DetectContainer
from images.config import get_config, set_config

from flask import Flask, g, jsonify, current_app, request, render_template, send_from_directory
from werkzeug.utils import secure_filename

VERSION = '0.0.1'

from flask.logging import default_handler

SAMPLE_DIR= "./samples/"

class SampleThread (threading.Thread):
    def __init__(self, queue):
        threading.Thread.__init__(self)
        self._queue = queue 
        self.daemon = True

    def run(self):
        while True:
            uuid = self._queue.get(block=True)
            print(uuid)
            job_dir = os.path.join(SAMPLE_DIR, uuid)
            die_cont = DetectContainer('die-' + uuid)
            to_exec = None
            config_data = get_config(job_dir)
            if config_data is not None and 'start-exec' in config_data:
                to_exec = config_data['start-exec']
            else:
                file_list = os.listdir(os.path.join(job_dir, "files"))
                to_exec = file_list[0]

            print(to_exec)

            die_cont.start(os.path.join(job_dir, "files"), {
                "EXECSAMPLE": to_exec
            })

            time.sleep(2)

            die_data = die_cont.process(job_dir)
            time.sleep(.5)

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ['FLASK_KEY']

    with app.app_context():

        app._queue = queue.Queue()
        app._sample_thread = SampleThread(app._queue)

        app.logger.setLevel(logging.INFO)

        app._sample_thread.start()
        
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