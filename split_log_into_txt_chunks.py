import datetime
import os

# Define the input and output file paths
input_file = r"C:\Projects\sigray\20220713\Serial1\test.log"
output_dir = r"C:\Projects\sigray\test_logs_dontDestroy_onlyCopy"

# Define the time interval for splitting the file (in seconds)
interval = 3

# Create the output directory if it doesn't already exist
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Open the input file and read the lines
with open(input_file, 'rt') as f:
    lines = f.readlines()

# Initialize the start time for the first interval
start_time = datetime.datetime.strptime(lines[0][1:20], '%Y-%m-%d %H:%M:%S')

# Initialize the current interval and latest line
current_interval = []
latest_line = ''

# Loop through each line in the file
for line in lines:
    # Parse the date and time from the bracketed part of the line
    line_time = datetime.datetime.strptime(line[1:20], '%Y-%m-%d %H:%M:%S')

    # Check if the current line falls within the current interval
    if (line_time - start_time).total_seconds() <= interval:
        current_interval.append(line)
        latest_line = line
    else:
        # If the current line falls outside the current interval, write the current interval to a file
        latest_time = datetime.datetime.strptime(latest_line[1:20], '%Y-%m-%d %H:%M:%S').strftime('%H_%M_%S')
        output_file = os.path.join(output_dir, f'{latest_time}.log')
        with open(output_file, 'wt') as f:
            f.writelines(current_interval)

        # Initialize a new interval and latest line
        start_time = line_time
        current_interval = [line]
        latest_line = line

# Write the final interval to a file
latest_time = datetime.datetime.strptime(latest_line[1:20], '%Y-%m-%d %H:%M:%S').strftime('%H_%M_%S')
output_file = os.path.join(output_dir, f'{latest_time}.log')
with open(output_file, 'wt') as f:
    f.writelines(current_interval)

