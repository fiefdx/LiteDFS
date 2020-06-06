#!/bin/bash
cmd_path=$(dirname $0)
cd $cmd_path

function main()
{
    case "$1" in
    start)
        nohup ldfsviewer -c ./configuration.yml > /dev/null 2>&1 &
        ;;
    stop)
        ps -ef | grep ldfsviewer | grep -v grep | awk '{print "kill -15 "$2}' | sh
        ;;
    restart)
        main stop
        main start
        ;;
    *)
        echo "usage:viewer.sh (start|stop|restart)"
        ;;   
    esac
}

main $@

exit 0
