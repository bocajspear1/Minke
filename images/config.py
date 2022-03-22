import json
import os

def get_config(job_dir):
    config_path = os.path.join(job_dir, "config.json")
    if not os.path.exists(config_path):
        return None 

    config_file = open(config_path, "r")
    config_data = json.load(config_file)
    config_file.close()

    return config_data

def set_config(job_dir, data):
    old_config = get_config(job_dir)
    for item in data:
        old_config['item'] = data[item]

    config_path = os.path.join(job_dir, "config.json")

    config_file = open(config_path, "w+")
    json.dump(old_config)
    config_file.close()