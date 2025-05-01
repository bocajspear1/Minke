import logging
import json
import queue
import os


from fastapi_offline import FastAPIOffline
from fastapi import File, Form, UploadFile, HTTPException, Request, Depends, Security, APIRouter
from fastapi.security import APIKeyHeader
import docker

from minke.process import SampleThread
from minke.api import v1_router


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | "
                           "%(module)s:%(funcName)s:%(lineno)d - %(message)s")

from minke.vars import *

DESCRIPTION="""
Minke is a malware dynamic analysis engine using Docker containers. All it does is run samples and outputs the raw syscalls 
from execution. It also sets up Ports4U to capture and records PCAPs to allow network resources to be emulated.

Minke utilizes QEMU for Linux binaries on a variety of architectures and WINE for Windows binaries.
"""

api_key = APIKeyHeader(name=API_TOKEN_HEADER, auto_error=False)

async def handle_api_key(req: Request, key: str = Security(api_key)):
    if req.app.api_key != key and req.client.host not in ("127.0.0.1", ):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid API key"
        )
    yield key

def create_app():

    config_path = "./config.json"
    if 'MINKE_CONFIG_PATH' in os.environ:
        config_path = os.environ['MINKE_CONFIG_PATH']

    config_file = open(config_path, "r")
    config_data = json.loads(config_file.read())
    config_file.close()

    app = FastAPIOffline(
        title="Minke Malware Dynamic Analysis Server",
        version=VERSION,
        description=DESCRIPTION
    )
    app.api_key = config_data['access_key']

    app.logger = logging.getLogger("server")

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

    client = docker.from_env()

    app.logger.info("Found Docker version %s", client.info()['ServerVersion'])
    
    app.logger.info("Server %s started", VERSION)

    return app


app = create_app()


app.include_router(
    v1_router,
    prefix="/api/v1",
    dependencies=[
        Depends(handle_api_key),
    ]
)
