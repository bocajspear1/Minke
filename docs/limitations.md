# Limitations

## Limitions with Wine

WINE is awesome, but currently Minke uses Wine's debugging output to get API calls. This makes it easy to get API calls without modifying Wine, but this means there are some limitations on certain API calls. Any calls that have interesting information behind pointers and structures is not visible with Wine's debug output, for example NtOpenFile (which puts the path into a OBJECT_ATTRIBUTES structure) or RegCreateKeyExA (which outputs the resulting handle to a pointer). This means you're not going to get as great information from proper hooking.

## Limitations with QEMU

Minke uses the userland emulation of QEMU to run applications of various architectures. Currently, only a basic `ptrace` patch is applied to hide the tracing. Not much else is currently done to hide QEMU.