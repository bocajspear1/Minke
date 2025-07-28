import unicodedata
import json
import os
import importlib
import inspect

from PIL import Image
from PIL import ImageChops


def load_config(config_path):
    config_file = open(config_path, "r")
    config_data = json.loads(config_file.read())
    config_file.close()
    return config_data

def save_config(config_path, config_data): 
    with open(config_path, "w") as config_out:
        config_out.write(json.dumps(config_data, indent=4))


def get_logging_config(config):

    log_level = config['log_level'].upper()
    format_str = "%(asctime)s | %(levelname)-8s | %(name)s - %(message)s"
    if log_level == "DEBUG":
        format_str = "%(asctime)s | %(levelname)-8s | %(name)s:%(module)s:%(funcName)s:%(lineno)d - %(message)s"
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "custom": {
                "format": format_str,
                "datefmt": "%Y-%m-%d %H:%M:%S",
                # "style": "{",
                "use_colors": True,
            },
            "custom-file": {
                "format": format_str,
                "datefmt": "%Y-%m-%d %H:%M:%S",
                # "style": "{",
                "use_colors": False,
            },
            'access': {
                '()': 'uvicorn.logging.AccessFormatter',
                'fmt': '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
                "use_colors": False,
            }
        },
        "handlers": {
            "console": {
                "level": log_level,
                "formatter": "custom",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",  # Default is stderr
            },
            "file": {
                "level": log_level,
                "formatter": "custom-file",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": os.path.join(config['log_dir'], "minke.log"), 
            },
            "file-access": {
                "level": log_level,
                "formatter": "access",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": os.path.join(config['log_dir'], "minke-access.log"), 
            },
        },
        "loggers": {
            "uvicorn": {
                "handlers": ["console", "file"],
                "level": log_level,
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["console", "file-access"],
                "level": log_level,
                "propagate": False,
            },
            "urllib3.connectionpool": { # Noisy, so we suppress
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
            "PIL.PngImagePlugin": { # Noisy, so we suppress
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
        },
        "root": {
            "handlers": ["console", "file"],
            "level": log_level,
            "propagate": False,
        }
    }


def filepath_clean(file_path):
    file_path = unicodedata.normalize("NFKD", file_path)
    file_path = file_path.encode("ascii", "ignore").decode("ascii")
    file_path = file_path.replace("\\", "")
    file_path = file_path.replace("/", "")
    while ".." in file_path:
        file_path = file_path.replace("..", "")
    return file_path

def images_are_same(path_1, path_2):
    image_one = Image.open(path_1)
    image_two = Image.open(path_2)

    diff = ImageChops.difference(image_one, image_two)

    if diff.getbbox():
        return False
    else:
        return True
    
def get_containers():

    container_list = []

    item_list = os.listdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "containers"))
    for item in item_list:
        if not item.endswith(".py"):
            continue

        tmp_mod = importlib.import_module("minke.containers." + item.replace(".py", ""))
        for import_item in dir(tmp_mod):
            if import_item.startswith("__"):
                continue

            import_obj = getattr(tmp_mod, import_item)

            if not inspect.isclass(import_obj):
                continue

            if "Base" in import_obj.__mro__[1].__name__ and "Base" not in import_obj.__name__:
                container_list.append(import_obj)
    
    return container_list

def get_docker(config):
    import docker

    ret_docker = None

    if 'docker_url' not in config:
        ret_docker = docker.from_env()
    else:
        docker_url = config['docker_url']
        if docker_url.startswith("ssh://"):
            ret_docker = docker.from_env(use_ssh_client=True, environment={
                "DOCKER_HOST": docker_url
            })
        else:
            ret_docker = docker.from_env(environment={
                "DOCKER_HOST": docker_url
            })

    docker_info = ret_docker.info()
    if "name=userns" not in docker_info['SecurityOptions']:
        raise ValueError("Minke will not run unless user namespaces are enabled!")

    return ret_docker