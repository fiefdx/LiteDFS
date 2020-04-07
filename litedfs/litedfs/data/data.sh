#!/bin/bash
cmd_path=$(dirname $0)
cd $cmd_path

function main()
{
    case "$1" in
    start)
        nohup litedata -c ./configuration.yml > /dev/null 2>&1 &
        ;;
    stop)
        ps -ef | grep litedata | grep -v grep | awk '{print "kill -15 "$2}' | sh
        ;;
    restart)
        main stop
        main start
        ;;
    *)
        echo "usage:data.sh (start|stop|restart)"
        ;;   
    esac
}

main $@

exit 0
