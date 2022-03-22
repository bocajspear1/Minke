import argparse 
import docker
import random
import string
import os
import shutil 
import time
import subprocess 
import tarfile


def main():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--file', help='Sample to test')

    args = parser.parse_args()

    if not os.path.exists(args.file):
        print("Invalid path to file")
        return 1

    
    client = docker.from_env()

    try:
        container = client.containers.get('qemu-docker-mipsel-1')
        container.remove()
    except docker.errors.NotFound:
        pass
    except docker.errors.APIError:
        pass

    tmp_dir = ''.join(random.choice(string.ascii_lowercase) for i in range(8))
    test_name = ''.join(random.choice(string.ascii_lowercase) for i in range(5))
    username = ''.join(random.choice(string.ascii_lowercase) for i in range(5))
    log_file = ''.join(random.choice(string.ascii_lowercase) for i in range(8))
    sample_name =  f"{test_name}"

    print(f"Temp Dir: {tmp_dir}")
    print(f"New Sample Name: {sample_name}")

    if not os.path.exists("./share"):
        os.mkdir("./share")

    share_dir = os.path.abspath(f"./share/{tmp_dir}")
    os.mkdir(share_dir)

    shutil.copy(args.file, f"{share_dir}/{test_name}")

    vols = {
        share_dir: {"bind": f"/tmp/{tmp_dir}/", 'mode': 'ro'}
    }

    environment = {
        "TMPDIR": tmp_dir,
        "SAMPLENAME": sample_name,
        "USER": username,
        "LOG": log_file
    }

    cont_name = "qemu-docker-mipsel-1"
    container = client.containers.create('qemu-docker-mipsel', volumes=vols, environment=environment, detach=True, name=cont_name, network_mode="none", dns=["172.16.3.1"])
    container.start()

    try:
        subprocess.check_output(["/usr/bin/sudo", "/usr/bin/ovs-docker", "del-ports", "vmbr0", cont_name])
    except:
        pass

    subprocess.check_output(["/usr/bin/sudo", "/usr/bin/ovs-docker", "add-port", "vmbr0", "eth0", cont_name, "--ipaddress={}".format('172.16.3.4/24'), "--gateway={}".format('172.16.3.1')])

    print("Waiting for timeout or completion...")
    i = 0
    done = False
    while i < 6 and not done:
        time.sleep(30)
        container = client.containers.get(cont_name)
        print(container.status)
        if container.status != "running":
            done = True
        else:
            i += 1
    
    print("Stopping container...")
    container = client.containers.get(cont_name)
    container.stop()

    print("Getting test log...")
    strm, stat = container.get_archive(f'/tmp/{log_file}')
    results = open("log.tar", "wb")
    for chunk in strm:
        results.write(chunk)
    results.close()

    results_tar = tarfile.open("log.tar", "r")
    log_file_data = results_tar.extractfile(log_file)
    log_file_out = open(f"{share_dir}/test.log", "wb")
    for chunk in log_file_data:
        log_file_out.write(chunk)
    log_file_out.close()
    results_tar.close()

    os.remove("log.tar")

main()