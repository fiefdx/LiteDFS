#!/bin/bash
cmd_path=$(dirname $0)
cd $cmd_path

systemctl disable litedfs-data
rm /lib/systemd/system/litedfs-data.service
systemctl daemon-reload
echo "disable & remove litedata systemd service"
