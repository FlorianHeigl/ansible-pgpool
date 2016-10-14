#!/bin/bash

sudo /etc/init.d/pgpool-II-95 stop
sudo /etc/init.d/postgresql-9.5 stop
sudo killall postgres
sudo killall pgpool
sudo rm -rf /var/lib/pgsql/9.5/data

