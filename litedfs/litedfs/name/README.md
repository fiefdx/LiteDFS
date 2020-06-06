# Name

LiteDFS Name Service

# Run

```bash
# generate configuration file & scripts
mkdir ./litedfs_name
cd ./litedfs_name
# this will generate configuration.yml and other scripts
ldfsname -g ./

# run manually
ldfsname -c ./configuration.yml or nohup ldfsname -c ./configuration.yml > /dev/null 2>&1 &

# install systemd service, user and group set to use which user and group to run ldfsname
sudo ./install_systemd_service.sh user group

# start
systemctl start litedfs-name

# stop
systemctl stop litedfs-name

# uninstall systemd service
sudo ./uninstall_systemd_service.sh
```
