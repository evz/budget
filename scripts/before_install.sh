#!/bin/bash
set -euo pipefail

# Make directory for project
mkdir -p /home/evz/budget

DEPLOYMENT_DIR=/opt/codedeploy-agent/deployment-root/$DEPLOYMENT_GROUP_ID/$DEPLOYMENT_ID/deployment-archive/
chown -R evz.evz $DEPLOYMENT_DIR
sudo -H -u evz gpg -d $DEPLOYMENT_DIR/configs/app_config.py.gpg > $DEPLOYMENT_DIR/configs/app_config.py
sudo -H -u evz gpg -d $DEPLOYMENT_DIR/configs/nginx_template.conf.gpg > $DEPLOYMENT_DIR/configs/nginx_template.conf
sudo -H -u evz gpg -d $DEPLOYMENT_DIR/configs/supervisor_template.conf.gpg > $DEPLOYMENT_DIR/configs/supervisor_template.conf
sudo -H -u evz gpg -d $DEPLOYMENT_DIR/configs/alembic.ini.gpg > $DEPLOYMENT_DIR/alembic.ini
sudo -H -u evz gpg -d $DEPLOYMENT_DIR/scripts/after_install.sh.gpg > $DEPLOYMENT_DIR/scripts/after_install.sh
sudo -H -u evz gpg -d $DEPLOYMENT_DIR/scripts/app_start.sh.gpg > $DEPLOYMENT_DIR/scripts/app_start.sh
