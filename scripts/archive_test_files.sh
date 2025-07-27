#!/bin/bash

for i in ./tests/files/*.winedump; do
    gzip -c $i > ${i}.gz
done

for i in ./tests/files/*.strace; do
    gzip -c $i > ${i}.gz
done

for i in ./tests/files/*.elf; do
    gzip -c $i > ${i}.gz
done

for i in ./tests/files/*.exe; do
    gzip -c $i > ${i}.gz
done