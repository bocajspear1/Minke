import shutil
import os

from colorama import Fore, Back, Style
import click

import random
import string
import subprocess

from minke.helper import load_config, get_containers, get_docker
from minke.vars import *


class ContextObj():

    def __init__(self):
        self.config = load_config("./config.json")

@click.group()
@click.pass_context
def main_cli(ctx):
    ctx.obj = ContextObj()


#
# run subcommand
#

@main_cli.group('run')
def run_group():
    pass

@run_group.command('web')
@click.option('--port', "-p", help="Port to bind to", default=8000)
@click.option('--addr', "-a", help="Set address to bind to", default="0.0.0.0")
@click.option("--debug", is_flag=True, help="Run in debug mode")
@click.pass_obj
def web_cmd(ctx, port, addr, debug):
    if debug is True:
        ctx.config['loglevel'] = 'debug'
    try:
        import uvicorn
        from minke.main import app
        uvicorn.run(app, host=addr, port=port)
    except KeyboardInterrupt:
        print("Stopping...")


@run_group.command('install')
@click.pass_obj
def install_cmd(ctx):
    if os.geteuid() != 0:
        print(f"{Fore.RED}Run install command as root{Style.RESET_ALL}")
        return 1
    
    minke_user = input("What user will Minke run as?> ")
    
    print(f"{Fore.BLUE}Setting up scripts{Style.RESET_ALL}")
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    if not os.path.exists("/usr/local/bin/minke-create-bridge"):
        print(f"{Fore.BLUE}Installing minke-create-bridge{Style.RESET_ALL}")
        shutil.copy(os.path.join(data_dir, "minke-create-bridge"), "/usr/local/bin/minke-create-bridge")
        os.chmod("/usr/local/bin/minke-create-bridge", 0o554)
    else:
        print(f"{Fore.GREEN}minke-create-bridge already exists{Style.RESET_ALL}")

    if not os.path.exists("/usr/local/bin/minke-remove-bridge"):
        print(f"{Fore.BLUE}Installing minke-remove-bridge{Style.RESET_ALL}")
        shutil.copy(os.path.join(data_dir, "minke-remove-bridge"), "/usr/local/bin/minke-remove-bridge")
        os.chmod("/usr/local/bin/minke-remove-bridge", 0o554)
    else:
        print(f"{Fore.GREEN}minke-remove-bridge already exists{Style.RESET_ALL}")

    if not os.path.exists("/etc/sudoers.d/minke-sudoers"):
        print(f"{Fore.BLUE}Installing sudoers file{Style.RESET_ALL}")
        with open(os.path.join(data_dir, "minke-sudoers"), "r") as sudoers_file:
            sudoers_data = sudoers_file.read()
            sudoers_data = sudoers_data.replace("minke ", f"{minke_user} ")
            with open("/etc/sudoers.d/minke-sudoers", "w+") as out_file:
                out_file.write(sudoers_data)
                out_file.write("\n")
        os.chmod("/etc/sudoers.d/minke-sudoers", 0o640)
    else:
        print(f"{Fore.GREEN}sudoers file already exists{Style.RESET_ALL}")

    print(f"{Fore.BLUE}Setting up tcpdump{Style.RESET_ALL}")
    subprocess.run("setcap cap_net_raw,cap_net_admin=eip /usr/sbin/tcpdump", shell=True)
    

@main_cli.group('submissions')
def submissions_group():
    pass

@submissions_group.command('clean')
@click.option("--force", is_flag=True, help="Force clean")
@click.pass_obj
def clean_cmd(ctx, force):
    if force is False:
        print(f"{Fore.RED}WARNING! This removes all data in Minke! Are you sure?{Style.RESET_ALL}")
        in_val = input("type 'yes'> ")
        if in_val != 'yes':
            print(f"{Fore.BLUE}Not doing anything, did not get 'yes'.{Style.RESET_ALL}")
            return
    
    shutil.rmtree(SAMPLE_DIR)
    print(f"{Fore.YELLOW}All data truncated!{Style.RESET_ALL}")


@main_cli.group('containers')
@click.pass_context
def containers_group(ctx):
    ctx.config = load_config("./config.json")

@containers_group.command('list')
@click.pass_obj
def list_cmd(ctx):
    docker_inst = get_docker(ctx.config)

    all_images = docker_inst.images.list()
    for image in all_images:
        for tag in image.tags:
            if tag.startswith("minke-"):
                print(tag)

@containers_group.command('build')
@click.pass_obj
def build_cmd(ctx):
    containers = get_containers()
    docker_inst = get_docker(ctx.config)

    username = ''.join(random.choice(string.ascii_lowercase) for i in range(6))

    all_images = docker_inst.images.list()
    image_check = []
    for image in all_images:
        for tag in image.tags:
            if tag.startswith("minke-"):
                image_check.append(tag.split(":")[0])
        

    for container in containers:
        
        image_name = f"minke-{container.DOCKERFILE_DIR}"
        if image_name in image_check:
            print(f"{Fore.GREEN}{image_name} already built{Style.RESET_ALL}")
            continue
        
        print(f"{Fore.BLUE}Building {container.DOCKERFILE_DIR} image...{Style.RESET_ALL}")
        dockerfile_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dockerfiles", container.DOCKERFILE_DIR)
        
        image, build_logs = docker_inst.images.build(path=dockerfile_path, tag=image_name, buildargs={
            "USERNAME": username
        })


@containers_group.command('rebuild')
@click.pass_obj
def rebuild_cmd(ctx):
    containers = get_containers()
    docker_inst = get_docker(ctx.config)

    username = ctx.config['username']
       

    for container in containers:
        
        image_name = f"minke-{container.DOCKERFILE_DIR}"
        
        print(f"{Fore.BLUE}Rebuilding {container.DOCKERFILE_DIR} image...{Style.RESET_ALL}")
        dockerfile_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dockerfiles", container.DOCKERFILE_DIR)
        
        docker_inst.images.build(path=dockerfile_path, tag=image_name, buildargs={
            "USERNAME": username
        })
