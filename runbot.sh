#!/bin/bash

#set -x

DIR="/home/charlie/Documents/Repos/xfinity-twitter-bot"
cd ${DIR}
if [[ $? -ne 0 ]]; then
  /bin/echo "There was a problem navigating to the directory!"
  exit 1
fi
if [[ $(basename $(pwd)) -ne "xfinity-twitter-bot" ]]; then
  /bin/echo "Not in the expected directory.  (Wanted: /home/charlie/Documents/Repos/xfinity-twitter-bot, Got: $(pwd)"
  exit 1
fi
echo -n "Activating virtual environment..."
source ./.venv/bin/activate
echo "done."
./.venv/bin/python3 ./speedbot.py --config config.json --speedtest /bin/speedtest
deactivate

#set +x
