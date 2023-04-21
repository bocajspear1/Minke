import docker
import random
import string
import json
import os

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "..", "config.json")

    if not os.path.exists(config_path):
        print("Please set up config.json before running build")
        return 1

    docker_inst = docker.from_env()
    print("Building extract image...")
    docker_inst.images.build(path="./dockerfiles/extract/", tag="minke-extract")

    username = ''.join(random.choice(string.ascii_lowercase) for i in range(6))
    print("Building winelyze image...")
    docker_inst.images.build(path="./dockerfiles/winelyze/", tag="minke-winelyze", buildargs={
        "USERNAME": username
    })

    config_file = open(config_path, "r+")
    config_data = json.loads(config_file.read())
    
    config_data['username'] = username

    config_file.seek(0)
    config_file.truncate(0)
    config_file.write(json.dumps(config_data, indent=4))

    config_file.close()




main()