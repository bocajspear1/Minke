#!/bin/sh

file ${TMPDIR}/${EXECSAMPLE} > /tmp/file-out.txt

objdump -x ${TMPDIR}/${EXECSAMPLE} > /tmp/objdump-out.txt

readelf -W -h ${TMPDIR}/${EXECSAMPLE} > /tmp/readelf-out.txt || true
readpe -h coff -h optional --format json ${TMPDIR}/${EXECSAMPLE} > /tmp/readpe-out.json || true

diec --json ${TMPDIR}/${EXECSAMPLE} > /tmp/die-out.json

md5sum ${TMPDIR}/${EXECSAMPLE} >> /tmp/hashes
sha1sum ${TMPDIR}/${EXECSAMPLE} >> /tmp/hashes
sha256sum ${TMPDIR}/${EXECSAMPLE} >> /tmp/hashes