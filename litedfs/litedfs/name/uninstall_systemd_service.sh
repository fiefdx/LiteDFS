#!/bin/bash
cmd_path=$(dirname $0)
cd $cmd_path

systemctl disable litedfs-name
rm /lib/systemd/system/litedfs-name.service
systemctl daemon-reload
echo "disable & remove litenode systemd service"
