#!/bin/bash
cmd_path=$(dirname $0)
cd $cmd_path

systemctl disable litedfs-viewer
rm /lib/systemd/system/litedfs-viewer.service
systemctl daemon-reload
echo "disable & remove litedfs-viewer systemd service"
