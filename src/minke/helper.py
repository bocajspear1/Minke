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

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "custom": {
            "()": "uvicorn.logging.DefaultFormatter",
            "format": "=>\t{levelprefix} {message} \t {filename}-{lineno}:[{asctime}]",
            "datefmt": "%d %H:%M:%S",
            "style": "{",
            "use_colors": True,
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "formatter": "custom",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",  # Default is stderr
        },
    },
    "loggers": {
        "logger": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
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

    if 'docker_url' not in config:
        return docker.from_env()

    docker_url = config['docker_url']
    if docker_url.startswith("ssh://"):
        return docker.from_env(use_ssh_client=True, environment={
            "DOCKER_HOST": docker_url
        })