#!/usr/bin/env bash
set -euo pipefail
fio --name=nvme_seq_read --directory=/srv/tesis/workspace --rw=read --bs=1M --size=256M --runtime=30 --time_based
