#!/bin/bash
set -euo pipefail

# Make directory for project
mkdir -p /home/evz/budget

cd /opt/codedeploy-agent/deployment-root/$DEPLOYMENT_GROUP_ID/$DEPLOYMENT_ID/deployment-archive/ && chown -R evz.evz . && sudo -H -u evz blackbox_postdeploy
