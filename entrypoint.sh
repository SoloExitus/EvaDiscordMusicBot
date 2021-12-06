#!/bin/bash

set -e

host="lavalink"
port="2333"
cmd="$@"

>&2 echo "Check lavalink for available..."

until curl http://"$host":"$port"; do
  >&2 echo "Lavalink is unavailable - sleeping"
  sleep 5
done

>&2 echo "Lavalink is up. Starting EvaBOt."

exec $cmd
