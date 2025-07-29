# Minke

![alt text](files/minke.png)


![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/bocajspear1/Minke/run_tests.yml)
![GitHub License](https://img.shields.io/github/license/bocajspear1/Minke)
![GitHub top language](https://img.shields.io/github/languages/top/bocajspear1/Minke)

Minke is a platform for performing malware analysis in Docker containers, even for Windows. Using WINE and QEMU, Minke allows for scalable and concurrent dynamic sample monitoring from a robust HTTP API.

# What's Minke for?

Minke is intended to be a dynamic malware analysis component. It simply executes and monitors samples and outputs executed syscalls/APIs, network traffic, screenshots, dropped files, and PCAPs. It utilizes [Ports4U](https://github.com/bocajspear1/ports4u) to spoof DNS and dynamically detect and start network services to provide a more thorough network analysis.

> Minke doesn't match any signatures against activity, it just collects the activity for somebody else to use, such as [Kogia](https://github.com/bocajspear1/Kogia).

Containers allows Kogia to process multiple samples at a time on a single system, even of different architectures and operating systems.

| Operating System | Architectures |
| ---------------- | ------------- |
| Windows          | x86, x86_64   |
| Linux            | x86, x86_64, ARM, AARCH64/ARM64, MIPS, MIPSEL, PowerPC, s390x, SH4, SPARC  |

With the tradeoff off certain [limitations](https://minkeanalyze.readthedocs.io/en/latest/limitations/), Minke allows analysis to scale to meet larger throughput demands.

# Installation

See instructions [here](https://minkeanalyze.readthedocs.io/en/latest/installation/)

# Usage

Minke is primarily used through an API. You can see its live Swagger documentation at `http://<MINKE_HOST>:8000/docs`.