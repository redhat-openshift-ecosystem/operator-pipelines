#!/bin/sh

max_retries=$1
shift

if [ -z "$1" ]; then
    echo "Usage: retry <max_retries> <command> [args...]" >&2
    exit 1
fi

attempt=1

until "$@"; do
    if [ "$attempt" -ge "$max_retries" ]; then
        echo "Command failed after $max_retries attempts" >&2
        exit 1
    fi
    attempt=$((attempt + 1))
    echo "Attempt $attempt failed. Retrying..." >&2

done
