# Viewer

LiteDFS Viewer Service

# Run

```bash
# generate configuration file & scripts
mkdir ./litedfs_viewer
cd ./litedfs_viewer
# this will generate configuration.yml and other scripts
ldfsviewer -g ./

# run manually
ldfsviewer -c ./configuration.yml or nohup ldfsviewer -c ./configuration.yml > /dev/null 2>&1 &

# install systemd service, user and group set to use which user and group to run ldfsviewer
sudo ./install_systemd_service.sh user group

# start
systemctl start litedfs-viewer

# stop
systemctl stop litedfs-viewer

# uninstall systemd service
sudo ./uninstall_systemd_service.sh
```
