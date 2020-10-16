#!/usr/bin/env bash
# Don't scale up the search service, it could lead to duplicates
docker-compose up -d --scale upload=4 --scale filter=2 --scale reply=2