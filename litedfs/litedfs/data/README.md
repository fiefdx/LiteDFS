# Node

LiteDFS Data Service

# Run

```bash
# generate configuration file & scripts
mkdir ./litedata
cd ./litedata
# this will generate configuration.yml and other scripts
litedata -g ./

# run manually
litedata -c ./configuration.yml or nohup litedata -c ./configuration.yml > /dev/null 2>&1 &

# install systemd service, user and group set to use which user and group to run litedata
sudo ./install_systemd_service.sh user group

# start
systemctl start litedfs-data

# stop
systemctl stop litedfs-data

# uninstall systemd service
sudo ./uninstall_systemd_service.sh
```
