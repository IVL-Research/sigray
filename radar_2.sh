#!/bin/bash

# Set the log file directory
log_dir=/home/pi/sigray

# Create log file names with timestamp
filename_serial0="$log_dir/$(date +"%Y_%m_%d_%H_%M_%S").serial0.log"
filename_serial1="$log_dir/$(date +"%Y_%m_%d_%H_%M_%S").serial1.log"

# Initialize line counters
line_count_serial0=0
line_count_serial1=0

# Loop indefinitely
while true; do
  # Check if line count has reached the maximum
  if [ "$line_count_serial0" -ge 1000 ]; then
    # Create a new log file for serial0
    filename_serial0="$log_dir/$(date +"%Y_%m_%d_%H_%M_%S").serial0.log"
    line_count_serial0=0
  fi

  if [ "$line_count_serial1" -ge 1000 ]; then
    # Create a new log file for serial1
    filename_serial1="$log_dir/$(date +"%Y_%m_%d_%H_%M_%S").serial1.log"
    line_count_serial1=0
  fi

  # Read incoming data from serial0, add a timestamp, and write it to the log file
  #cat /dev/ttyUSB0 | ts '[%Y-%m-%d %H:%M:%.S]' | tee -a "$filename_serial0" | python -c "import sys; print(sys.stdin.read())" | parse_radar.py &
  cat /dev/ttyUSB0 | ts '[%Y-%m-%d %H:%M:%.S]' >> $filename_serial0 &
  
  # Increment the line count for serial0
  ((line_count_serial0++))

  # Read incoming data from serial1, add a timestamp, and write it to the log file
  #cat /dev/ttyUSB1 | ts '[%Y-%m-%d %H:%M:%.S]' | tee -a "$filename_serial1" | python -c "import sys; print(sys.stdin.read())" | parse_radar.py &
  cat /dev/ttyUSB1 | ts '[%Y-%m-%d %H:%M:%.S]' >> $filename_serial1 &

  # Increment the line count for serial1
  ((line_count_serial1++))

  # Sleep for 1 second before the next iteration
  sleep 1
done