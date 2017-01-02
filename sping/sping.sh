#!/bin/bash

# based on:
# http://unix.stackexchange.com/questions/207234/host-monitoring-script-with-timestamp

echo "Pinging host " $@
HOST=$@
ALIVE=false

ping -DO $HOST | while read PONG
do
        grep -q ttl <<< "$PONG"
        if [ $? -eq 0 ]; then
            if [ $ALIVE == false ]; then
                echo "`date +%Y%m%d-%H%M%S.%N`: $HOST is UP"
                ALIVE=true
            fi
        else
            if [ $ALIVE == true ]; then 
                echo "`date +%Y%m%d-%H%M%S.%N`: $HOST is DOWN!"
                ALIVE=false
            fi
        fi
done

