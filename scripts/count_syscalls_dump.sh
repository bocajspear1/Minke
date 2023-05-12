#!/bin/bash

cut -d" " -f 2 $1 | cut -d"(" -f 1 | sort  | uniq -c | sort -nr