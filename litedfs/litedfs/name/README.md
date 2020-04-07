# Name

LiteDFS Name Service

# Run

```bash
# generate configuration file & scripts
mkdir ./litename
cd ./litename
# this will generate configuration.yml and other scripts
litename -g ./

# run manually
litename -c ./configuration.yml or nohup litename -c ./configuration.yml > /dev/null 2>&1 &

# install systemd service, user and group set to use which user and group to run litename
sudo ./install_systemd_service.sh user group

# start
systemctl start litedfs-name

# stop
systemctl stop litedfs-name

# uninstall systemd service
sudo ./uninstall_systemd_service.sh
```
