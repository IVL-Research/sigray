import pynmea2
import numpy as np
import folium

# Dash
import dash
from dash import dcc, html
import os
from dash.dependencies import Input, Output, State


def test_read_data(output_dir, nauticalMiles2meters, earth_radius, base_lat, base_long):

    # Get a list of all the files in the output directory
    files = os.listdir(output_dir)

    # Sort the files by name
    files.sort()

    for file in files:
        radar_serial_data = open(os.path.join(output_dir,file), "rt", encoding='cp1252')
#        print(radar_serial_data)
        for line in radar_serial_data:
            try:
                line = line.split("] ")[1]
                line = line.replace('QQ5±', '$RATTM,')
                if line.startswith("$RATTM"):
                    print("--------")
                    print(file)                
                    msg = pynmea2.parse(line)
                    status, ts, lat, long, target_nbr = get_target_data(msg, nauticalMiles2meters, earth_radius, base_lat,
                                                                        base_long)
                    print(f"file: {file}, status: {status}, target: {target_nbr}, lat: {lat}, long: {long}")
            except Exception as e:
                print(file)
                print(line)
                print(e)
                pass
        radar_serial_data.close()


def get_target_data(msg, nauticalMiles2meters, R, base_lat, base_long):
    print(msg)
    if (msg.status == 'T'):

        timestamps = msg.timestamp.replace(tzinfo=None)

        # Finding range for target
        r = float(msg.distance) * nauticalMiles2meters

        bearing_rad = np.radians(float(msg.bearing))

        # Coordinate calulcation
        d = r / nauticalMiles2meters  # Distance to object (nautical miles)

        Ad = d / R  # Angular distance i.e d/R (nautical miles)

        tmp_la = np.degrees(
            np.arcsin(np.sin(base_lat) * np.cos(Ad) + np.cos(base_lat) * np.sin(Ad) * np.cos(bearing_rad)))
        tmp_lo = np.degrees(base_long + np.arctan2((np.sin(bearing_rad) * np.sin(Ad) * np.cos(base_lat)),
                                                   (np.cos(Ad) - np.sin(base_lat) * np.sin(tmp_la))))

        return True, timestamps, tmp_la, tmp_lo, int(msg.target_number)
    else:
        return False, None, None, None, None


if __name__ == '__main__':
    base_lat, base_long = (1.0061238452447892, 0.20680522662164277)
    nauticalMiles2meters = 1852 / 1000
    earth_radius = 3440.1  # Radius of Earth
    output_dir = r"/home/pi/sigray/tmp_log_dir_copy/serial1"
    test_read_data(output_dir, nauticalMiles2meters, earth_radius, base_lat, base_long)

