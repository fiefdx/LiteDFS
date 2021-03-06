#!/bin/bash
cmd_path=$(dirname $0)
cd $cmd_path

cmd_path_abs=$(realpath .)
echo $cmd_path_abs

user_name=$1
group_name=$2
if [ -z "$user_name" ]
then
      user_name="root"
fi
if [ -z "$group_name" ]
then
      group_name="root"
fi
echo "run litename with user: $user_name, group: $group_name"

sed "s#user_name#$user_name#g; s#group_name#$group_name#g; s#script_path#$cmd_path_abs#g" ./litedfs-name.service.temp > ./litedfs-name.service

cp ./litedfs-name.service /lib/systemd/system/

systemctl enable litedfs-name
systemctl daemon-reload
