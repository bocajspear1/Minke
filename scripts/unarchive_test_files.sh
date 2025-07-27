#!/bin/bash

for i in ./tests/files/*.gz; do
    gunzip -c ${i} > $(echo $i | sed 's/.gz//g')
done
