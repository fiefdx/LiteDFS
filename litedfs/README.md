# LiteDFS

A distributed file system, based on Python3, tornado, inspired by HDFS.

It's for data processing cache, not for permanent storage!

All code based on Python3, do not use Python2!

It still under development, so, maybe have some bugs or not stable enough!

See more details at https://github.com/fiefdx/LiteDFS

# Features

1. per file replica settings, support dynamic replica change, no data resharding functions, currently

2. scalable with add / remove node

3. lightweight, pure python implementation

4. support command line interface

# Conceptions

1. name node(ldfsname): the central node of the cluster, manage all files & directories index.

2. data node(ldfsdata): the data node of the cluster, store real file's blocks data.

3. command line client(ldfs): the command line tool for communicate with the cluster.

4. graphic client(ldfsviewer): the graphic tool for communicate with the cluster.

# Deployment

## Install LiteDFS
```bash
# this will install 4 commands: ldfsname, ldfsdata, ldfs, ldfsviewer
$ pip3 install litedfs
```

## Run Name Node

### Configuration
```yaml
log_level: NOSET                        # NOSET, DEBUG, INFO, WARNING, ERROR, CRITICAL
log_path: /home/pi/litedfs_name/logs    # log file directory, can auto generate by ldfsname
http_host: 0.0.0.0                      # name node's http host
http_port: 9000                         # name node's http port
tcp_host: 0.0.0.0                       # name node's tcp host
tcp_port: 6061                          # name node's tcp port
block_size: 67108864                    # 67108864 = 64M, file block size
data_path: /home/pi/litedfs_name/data   # name node data store directory, can auto generate by ldfsname
```

### Run
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

# test
$ curl localhost:9000
{"message": "LiteDFS name service"}
```

## Run Node

### Configuration
```yaml
log_level: NOSET                        # NOSET, DEBUG, INFO, WARNING, ERROR, CRITICAL
log_path: /home/pi/litedfs_data/logs    # log file directory, can auto generate by ldfsdata
http_host: 0.0.0.0                      # data node's http host
http_port: 8002                         # data node's http port
name_http_host: 127.0.0.1               # name node's http host
name_http_port: 9000                    # name node's http port
name_tcp_host: 127.0.0.1                # name node's tcp host
name_tcp_port: 6061                     # name node's tcp port
heartbeat_interval: 1                   # heartbeat interval, 1 seconds
heartbeat_timeout: 30                   # heartbeat timeout, 30 seconds
retry_interval: 5                       # retry to connect name node interval, when lost connection, 5 seconds
data_path: /home/pi/litedfs_data/data   # data node data store directory, can auto generate by ldfsdata
```

### Run
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

# test
$ curl localhost:8002
{"message": "LiteDFS data service"}
```

## Run Viewer

This viewer must running on your local machine, it is not a public service, it is a graphic client based on web technique.

### Configuration
```yaml
log_level: NOSET                           # NOSET, DEBUG, INFO, WARNING, ERROR, CRITICAL
log_path: /home/pi/litedfs_viewer/logs     # log file directory, can auto generate by ldfsviewer
http_host: 0.0.0.0                         # viewer's http host
http_port: 8088                            # viewer's http port
name_http_host: 192.168.199.149            # name node's http host
name_http_port: 9000                       # name node's http port
data_path: /home/pi/litedfs_viewer/data    # viewer data store directory, can auto generate by ldfsviewer
```

### Run
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

# test
# use web browser open: http://localhost:8088
```

## Operate With LiteDFS Cluster
```bash
# list root directory
$ ldfs localhost:9000 directory list -r /
# | id | type | size | name

# create test directory
$ ldfs localhost:9000 directory create -r /test
create directory[/test] success

# list root directory again
$ ldfs localhost:9000 directory list -r /
# | id | type      | size | name
1 |    | directory | 0    | test

# create a file
$ ldfs localhost:9000 file create -r /test/test.tar.gz -l ./examples.tar.gz 
create file[/test/test.tar.gz] success

# list test directory
$ ldfs localhost:9000 directory list -r /test
# | id                                   | type | size      | name       
1 | 878b17d4-cc11-4bba-88b0-2186b77ef552 | file | 110237727 | test.tar.gz

# create test2 directory
$ ldfs localhost:9000 directory create -r /test2
create directory[/test2] success

# list root directory again
$ ldfs localhost:9000 directory list -r /
# | id | type      | size | name 
1 |    | directory | 0    | test 
2 |    | directory | 0    | test2

# move test.tar.gz into test2 directory
$ ldfs localhost:9000 file move -s /test/test.tar.gz -t /test2
move file[/test/test.tar.gz] to /test2 success

# list test directory again
$ ldfs localhost:9000 directory list -r /test
# | id | type | size | name

# list test2 directory again
$ ldfs localhost:9000 directory list -r /test2
# | id                                   | type | size      | name       
1 | 878b17d4-cc11-4bba-88b0-2186b77ef552 | file | 110237727 | test.tar.gz

# create file with replica 2
$ ldfs localhost:9000 file create -r /test/test.tar.gz -l ./examples.tar.gz -R 2
create file[/test/test.tar.gz] success

# update file replica 3
$ ldfs localhost:9000 file create -r /test/test.tar.gz -l ./examples.tar.gz -R 3
update file[/test/test.tar.gz] success

# download /test/test.tar.gz to local file ./test.tar.gz
$ ldfs localhost:9000 file download -r /test/test.tar.gz -l ./test.tar.gz
download file[/test/test.tar.gz => ./test.tar.gz] success
```
