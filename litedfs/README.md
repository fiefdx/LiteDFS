# LiteDFS

A distributed file system, based on Python3, tornado, inspired by HDFS.

It's for data processing cache, not for permanent storage!

All code based on Python3, do not use Python2!

It still under development, so, maybe have some bugs or not stable enough!

See more details at https://github.com/fiefdx/LiteDFS

# Features

1. per file replica settings, support dynamic replica change, not data resharding functions, currently

2. scalable with add / remove node

3. lightweight, pure python implementation

4. support command line interface

# Conceptions

1. name node(litename): the central node of the cluster, manage all files & directories index.

2. data node(litedata): the data node of the cluster, store real file's blocks data.

3. command line client(litedfs): the command line tool for communicate with the cluster.

# Deployment

## Install LiteDFS
```bash
# this will install 3 commands: litename, litedata, litedfs
$ pip3 install litedfs
```

## Run Name Node

### Configuration
```yaml
log_level: NOSET                        # NOSET, DEBUG, INFO, WARNING, ERROR, CRITICAL
log_path: /home/pi/litename_data/logs   # log file directory, can auto generate by litename
http_host: 0.0.0.0                      # name node's http host
http_port: 9000                         # name node's http port
tcp_host: 0.0.0.0                       # name node's tcp host
tcp_port: 6061                          # name node's tcp port
block_size: 67108864                    # 67108864 = 64M, file block size
data_path: /home/pi/litename_data/data  # name node data store directory, can auto generate by litename
```

### Run
```bash
# generate configuration file & scripts
mkdir ./litename_data
cd ./litename_data
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

# test
$ curl localhost:9000
{"message": "LiteDFS name service"}
```

## Run Node

### Configuration
```yaml
log_level: NOSET                        # NOSET, DEBUG, INFO, WARNING, ERROR, CRITICAL
log_path: /home/pi/litedata_data/logs   # log file directory, can auto generate by litedata
http_host: 0.0.0.0                      # data node's http host
http_port: 8002                         # data node's http port
manager_http_host: 127.0.0.1            # name node's http host
manager_http_port: 9000                 # name node's http port
manager_tcp_host: 127.0.0.1             # name node's tcp host
manager_tcp_port: 6061                  # name node's tcp port
heartbeat_interval: 1                   # heartbeat interval, 1 seconds
heartbeat_timeout: 30                   # heartbeat timeout, 30 seconds
retry_interval: 5                       # retry to connect name node interval, when lost connection, 5 seconds
data_path: /home/pi/litedata_data/data  # data node data store directory, can auto generate by litedata
```

### Run
```bash
# generate configuration file & scripts
mkdir ./litedata_data
cd ./litedata_data
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

# test
$ curl localhost:8002
{"message": "LiteDFS data service"}
```

## Operate With LiteDFS Cluster
```bash
# list root directory
$ litedfs localhost:9000 directory list -r /
# | id | type | size | name

# create test directory
$ litedfs localhost:9000 directory create -r /test
create directory[/test] success

# list root directory again
$ litedfs localhost:9000 directory list -r /
# | id | type      | size | name
1 |    | directory | 0    | test

# create a file
$ litedfs localhost:9000 file create -r /test/test.tar.gz -l ./examples.tar.gz 
create file[/test/test.tar.gz] success

# list test directory
$ litedfs localhost:9000 directory list -r /test
# | id                                   | type | size      | name       
1 | 878b17d4-cc11-4bba-88b0-2186b77ef552 | file | 110237727 | test.tar.gz

# create test2 directory
$ litedfs localhost:9000 directory create -r /test2
create directory[/test2] success

# list root directory again
$ litedfs localhost:9000 directory list -r /
# | id | type      | size | name 
1 |    | directory | 0    | test 
2 |    | directory | 0    | test2

# move test.tar.gz into test2 directory
$ litedfs localhost:9000 file move -s /test/test.tar.gz -t /test2
move file[/test/test.tar.gz] to /test2 success

# list test directory again
$ litedfs localhost:9000 directory list -r /test
# | id | type | size | name

# list test2 directory again
$ litedfs localhost:9000 directory list -r /test2
# | id                                   | type | size      | name       
1 | 878b17d4-cc11-4bba-88b0-2186b77ef552 | file | 110237727 | test.tar.gz

# create file with replica 2
$ litedfs localhost:9000 file create -r /test/test.tar.gz -l ./examples.tar.gz -R 2
create file[/test/test.tar.gz] success

# update file replica 3
$ litedfs localhost:9000 file create -r /test/test.tar.gz -l ./examples.tar.gz -R 3
update file[/test/test.tar.gz] success

# download /test/test.tar.gz to local file ./test.tar.gz
$ litedfs localhost:9000 file download -r /test/test.tar.gz -l ./test.tar.gz
download file[/test/test.tar.gz => ./test.tar.gz] success
```
