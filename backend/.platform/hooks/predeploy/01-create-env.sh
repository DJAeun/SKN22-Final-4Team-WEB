#!/bin/bash
/opt/elasticbeanstalk/bin/get-config environment | python3 -c "
import sys, json
env = json.load(sys.stdin)
with open('/var/app/staging/.env', 'w') as f:
    for k, v in env.items():
        f.write(f'{k}={v}\n')
"
