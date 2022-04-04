#!/bin/sh

EXTRA_ARGS=""

mkdir /tmp/out

if [[ ${EXECSAMPLE} == *zip ]]; then
    if 7z l -slt ${TMPDIR}/${EXECSAMPLE} | grep -v "Encrypted = +"; then
        EXTRA_ARGS='-pinfected '
    fi
    7za x ${TMPDIR}/${EXECSAMPLE} -tzip ${EXTRA_ARGS} -o/tmp/out
fi

chmod -R 444 /tmp/out/*

ls -la /tmp/out/*