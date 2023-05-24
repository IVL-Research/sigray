#!/bin/bash

# Set the log file directory and interval to create new files
log_dir_0=/home/pi/sigray/logs/serial0
log_dir_1=/home/pi/sigray/logs/serial1
interval=5 # in seconds

# Create log file names with timestamp
filename_serial0="$log_dir_0/$(date +"%Y_%m_%d_%H_%M_%S").serial0.log"
filename_serial1="$log_dir_1/$(date +"%Y_%m_%d_%H_%M_%S").serial1.log"

pkill -f "cat*"

# Read incoming data from serial0, add a timestamp, and write it to the log file
cat /dev/ttyUSB0 | ts '[%Y-%m-%d %H:%M:%.S]' >> $filename_serial0 &
sleep 1
chmod 777 $filename_serial0

# Read incoming data from serial1, add a timestamp, and write it to the log file
cat /dev/ttyUSB1 | ts '[%Y-%m-%d %H:%M:%.S]' >> $filename_serial1 &
sleep 1
chmod 777 $filename_serial1

# Loop indefinitely
while true; do
  # Check if it's time to create new log files
  if (( $(date +"%s") % $interval == 0 )); then
    sudo killall cat
    
    # Create new log file names with timestamp
    filename_serial0="$log_dir_0/$(date +"%Y_%m_%d_%H_%M_%S").serial0.log"
    filename_serial1="$log_dir_1/$(date +"%Y_%m_%d_%H_%M_%S").serial1.log"
    
    # Read incoming data from serial0, add a timestamp, and write it to the log file
    cat /dev/ttyUSB0 | ts '[%Y-%m-%d %H:%M:%.S]' >> $filename_serial0 &
    sleep 1
    chmod 777 $filename_serial0
    
    # Read incoming data from serial1, add a timestamp, and write it to the log file
    cat /dev/ttyUSB1 | ts '[%Y-%m-%d %H:%M:%.S]' >> $filename_serial1 &
    sleep 1
    chmod 777 $filename_serial1
	
  fi

  # Sleep for 1 second before the next iteration
  sleep 1
done
