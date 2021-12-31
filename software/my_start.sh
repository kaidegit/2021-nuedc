#!/bin/bash
case "$1" in
    start):
        echo "Starting app"
        su pi -c "nohup /usr/bin/python3 /home/pi/2021-nuedc-python/letnet_cv/main.py &" &
    ;;
    stop):
        echo "to"
        #kill $( ps aux | grep -m 1 'python3 /home/pi/share/ip_acquire.py' | awk '{ print $2 }') ;; *)
        echo "Usage: service start_tool start|stop"
        exit 1 ;;
esac

exit 0