#!/bin/bash
cd "$(dirname "$0")"
lsof -ti :8080 | xargs kill -9 2>/dev/null
python3 server.py
