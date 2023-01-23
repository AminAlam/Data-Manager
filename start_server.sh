# !/bin/bash
bash sync_files.sh
ssh -f -g -R 8080:localhost:8080 -N amin@aminalam.info
./venv/bin/python3 -m pip install -r requirements.txt
./venv/bin/python3 ./src/main.py
