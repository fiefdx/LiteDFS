# Node

LiteDFS Data Service

# Run

```bash
# generate configuration file & scripts
mkdir ./litedfs_data
cd ./litedfs_data
# this will generate configuration.yml and other scripts
ldfsdata -g ./

# run manually
ldfsdata -c ./configuration.yml or nohup ldfsdata -c ./configuration.yml > /dev/null 2>&1 &

# install systemd service, user and group set to use which user and group to run ldfsdata
sudo ./install_systemd_service.sh user group

# start
systemctl start litedfs-data

# stop
systemctl stop litedfs-data

# uninstall systemd service
sudo ./uninstall_systemd_service.sh
```
