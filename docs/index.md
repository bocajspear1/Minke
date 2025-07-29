# Welcome to Minke

Minke is a Python and Docker application for performing dynamic analysis on malware for Windows (with WINE) and various architectures of Linux (with QEMU, supports x86, ARM, MIPS, PowerPC, and more). The goal is create a very lightweight and scalable platform (though with with some [limitations](limitations.md)) to analyze malware. Containers take up less space and allow concurrent analyses on a single system.

!!! info

    Note that Minke only provides the base functionality to execute and gather syscalls on malware, and not much more. For a proper malware analysis platform, use [Kogia](https://github.com/bocajspear1/Kogia), which Minke is mainly developed to integrate with. 

## Getting Started

!!! danger "Isolate Your Minke!"

    Containers should not be considered isolated enough to perform analysis on an internet-connected or general-use system! Container escapes do exist! Always use Minke with an isolated container system and run the web UI on a separate system.

Get started with [installation](installation.md).