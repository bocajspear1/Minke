#!/bin/sh

diec --json ${TMPDIR}/${EXECSAMPLE} > /tmp/output.json

md5sum ${TMPDIR}/${EXECSAMPLE} >> /tmp/hashes
sha1sum ${TMPDIR}/${EXECSAMPLE} >> /tmp/hashes
sha256sum ${TMPDIR}/${EXECSAMPLE} >> /tmp/hashes