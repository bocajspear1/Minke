# Installation

A Minke installation consists of two systems, the Minke host and the Container host.


## Container Host

The Container Host runs the actual containers for the analysis, instrumented by the Minke Host. This allows the Container Host to be isolated during use to provide separation.

### Install Dependencies

#### Ubuntu

Install Docker according to the latest instructions here: https://docs.docker.com/engine/install/ubuntu/


Ensure the Docker service is set to start on boot and running:

```
systemctl enable docker
systemctl start docker
```

#### Alpine Linux

Enable the community repositories, then install the necessary packages:

```
apk add -U docker docker-compose docker-openrc shadow shadow-subids iptables docker-bash-complete bash
```

Ensure the Docker service is set to start on boot and running:

```
rc-update add docker
rc-service docker start
```

### Configure Docker

We need to configure Docker to run in user namespace mode to limit containers to different uids/gids (Minke will detect if this is on or not and won't start if its not enabled). We also need to disable `iptables` usage on Docker, as this conflicts with the analysis. In the `/etc/docker/daemon.json` put:

```
{
  "userns-remap": "default",
  "iptables": false
}
```

### Setup Analysis User

Create a user and put it in the `docker` group to allow Docker usage.

### Reboot

To ensure the Docker `iptables` are cleared and user groups are in effect, reboot the Container Host.

### Setup Manual NAT

Since we told Docker itself to not insert any `iptables` rules, we need to create the masquerade/NAT rule for the building process, so run:

```
iptables -t nat -A POSTROUTING -o <EXTERNAL_IFACE> -j MASQUERADE
```

### Setup Remote Docker

The safest way is to use SSH. All you need to do this is have the SSH server running on the server.

!!! info

    You could use remote Docker via TCP or TLS on a port, but I won't go over setting that up here.


## Minke Host

This host holds the web API and instruments the analysis. It connects to the Container host and utilizes the Docker API to run the analysis containers. This allows the dynamic analysis to be isolated on a separate system

### Install Other Dependencies

Install other dependencies:

#### Ubuntu

```shell
sudo apt-get install -y git make imagemagick
```

On more recent Ubuntu versions, you will need to replace `imagemagick` with `graphicsmagick-imagemagick-compat`

```shell
sudo apt-get install -y git make graphicsmagick-imagemagick-compat
```

### Setup Remote Docker

Here, since we're using SSH remote Docker, we should install an SSH key to access the Container Host.

!!! info

    Remember we're using SSH programmatically, ensure you don't need to fill in a decryption key, either by not having one or using `ssh-agent`.

```
ssh-copy-id <USER>@<CONTAINER_HOST>
```

### Install Minke

#### Source Code Install

Download the project. Then create virtual environment and install Python dependencies:

```shell
git clone https://github.com/bocajspear1/Minke.git
cd Minke
python3 -m venv ./venv
pip3 install pdm
pdm install
```

### Setup Ports4U

This will build the `ports4u` container, which is needed for network analysis. 

Clone the project [Ports4U](https://github.com/bocajspear1/ports4u). Build the container with:

```shell
git clone https://github.com/bocajspear1/ports4u.git
cd ports4u
DOCKER_HOST=ssh://<USER>@<CONTAINER_HOST> make build
```

### Configure Minke

Using the configuration template in `config-example.json`, create the configuration file `config.json`. 

Edit `docker_url` to point to the Container Host, for example:

```
"docker_url": "ssh://<USER>@<CONTAINER_HOST>
```

Be sure to configure `access_key` to something secure too.

### Build Containers

To build containers on the Container Host, ensure the Container Host is connected to the internet and run the following command:

```
minke containers build
```

## Isolate Container Host

!!! danger "Isolate Your Minke!"

    Remember that containers should not be considered isolated enough to perform analysis on an internet-connected or general-use system! Container escapes do exist!

Once the containers are built, you should isolate the Container Host on a private network only shared by the Minke Host and Container Host.

Be sure to update the `docker_host` configuration in `config.json` to match the new IP address.

## Running the Server

Run the server with the command:

```
minke run web
```





