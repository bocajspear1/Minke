# Minke

![alt text](files/minke.png)


Minke is a platform for performing malware analysis in Docker containers, even for Windows.


# Installation

## Install External Dependencies

Install Docker according to the latest instructions: https://docs.docker.com/engine/install/ubuntu/

Install other dependencies:
```
sudo apt-get install -y openvswitch-switch imagemagick
```

Download the project [Ports4U](https://github.com/bocajspear1/ports4u). Build the container with:
```
make build
```

## Install Minke

Download the project. Then create virtual environment and install Python dependencies:
```
python3 -m venv ./venv
source ./venv/bin/activate
pip3 install -r requirements.txt
pip3 install -r requirements-dev.txt # Only if developing or testing
```

Then build the containers:
```
python3 minke/build.py
```

If no errors are shown, you're all set!

# Running

Use the start script:
```
./start_server.sh
```