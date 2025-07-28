import shutil
import os

from colorama import Fore, Back, Style
import click

import random
import string
import subprocess

from minke.helper import load_config, get_containers, get_docker, get_logging_config
from minke.vars import *

from docker.errors import BuildError


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
        ctx.config['log_level'] = 'debug'

    if not os.path.exists("./samples"):
        os.mkdir("./samples")

    if not os.path.exists("./logs"):
        os.mkdir("./logs")

    logging_config = get_logging_config(ctx.config)
    try:
        import uvicorn
        from minke.main import app
        uvicorn.run(app, host=addr, port=port, log_config=logging_config)
    except KeyboardInterrupt:
        print("Stopping...")
    

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

@containers_group.command('info')
@click.pass_obj
def info_cmd(ctx):
    docker_inst = get_docker(ctx.config)

    docker_info = docker_inst.info()
    from pprint import pprint
    pprint(docker_info)

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
@click.option("--force", is_flag=True, help="Force build")
@click.option("--images", multiple=True, help="Images to build", default=None)
@click.pass_obj
def build_cmd(ctx, force, images):
    print(images)
    containers = get_containers()
    docker_inst = get_docker(ctx.config)

    username = ctx.config['username']

    all_images = docker_inst.images.list()
    image_check = []
    for image in all_images:
        for tag in image.tags:
            if tag.startswith("minke-"):
                image_check.append(tag.split(":")[0])
        

    for container in containers:

        if images is not None and container.DOCKERFILE_DIR not in images:
            continue
        
        image_name = f"minke-{container.DOCKERFILE_DIR}"
        if image_name in image_check and force is not True:
            print(f"{Fore.GREEN}{image_name} already built{Style.RESET_ALL}")
            continue
        
        print(f"{Fore.BLUE}Building {container.DOCKERFILE_DIR} image...{Style.RESET_ALL}")
        dockerfile_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dockerfiles", container.DOCKERFILE_DIR)
        
        

        try:
            image, build_logs = docker_inst.images.build(path=dockerfile_path, tag=image_name, buildargs={
                "USERNAME": username
            })
        except BuildError as e:
            print("Build failed with:")
            print(e)
            for line in e.build_log:
                print(line)
            return 2


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
        
        try:
            docker_inst.images.build(path=dockerfile_path, tag=image_name, buildargs={
                "USERNAME": username
            })
        except BuildError as e:
            print("Build failed with:")
            print(e)
            for line in e.build_log:
                print(line)
            return 2
