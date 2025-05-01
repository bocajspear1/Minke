import shutil
import os

from colorama import Fore, Back, Style
import click
import docker
import random
import string

from minke.helper import load_config, get_containers
from minke.vars import *

class ContextObj():

    def __init__(self):
        pass

@click.group()
@click.pass_context
def main_cli(ctx):
    ctx.obj = ContextObj()
    ctx.config = load_config("./config.json")


#
# run subcommand
#

@main_cli.group('run')
def run_group():
    pass

@run_group.command('web')
@click.option('--port', "-p", help="Port to bind to", default=4000)
@click.option('--addr', "-a", help="Set address to bind to", default="0.0.0.0")
@click.option("--debug", is_flag=True, help="Run in debug mode")
@click.pass_obj
def web_cmd(ctx, port, addr, debug, noworkers, waitress):
    if debug is True:
        ctx.config['loglevel'] = 'debug'
    try:
        if not waitress:
            from backend.run import run_gunicorn
            run_gunicorn(ctx.config, ctx.workers, addr, int(port))
        else:
            from backend.run import run_waitress
            run_waitress(ctx.config, ctx.workers, addr, int(port))
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
def containers_group():
    pass


@containers_group.command('build')
@click.pass_obj
def build_cmd(ctx):
    containers = get_containers()
    docker_inst = docker.from_env()

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
        
        docker_inst.images.build(path=dockerfile_path, tag=image_name, buildargs={
            "USERNAME": username
        })
