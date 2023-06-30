# -*- coding: utf-8 -*-

import pynmea2
import numpy as np
import folium
import chardet
import time

# Dash
import dash
from dash import dcc, html
import os
from dash.dependencies import Input, Output, State



def create_map_object(init_zoom, radar_init_lat, radar_init_long):
    map_object = folium.Map([np.degrees(radar_init_lat), np.degrees(radar_init_long)], zoom_start=init_zoom,
                            tiles="cartodbpositron")
    folium.Marker(
        location=[radar_init_lat, radar_init_long],
        popup="Boat radar",
    ).add_to(map_object)
    html_string = '''
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8">  
        <title>Map</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css">
        {{ script }}
    </head>
    <body>
        <div class="container-fluid">
            <div class="row-fluid">
                <div class="span12">
                    <div id="map"></div>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''
    folium_map = folium.Map(location=[radar_init_lat, radar_init_long], zoom_start=init_zoom)
    folium_map.add_to(folium.Html(html_string))

    # display initial map
    map_name = 'map.html'
    folium_map.save(map_name)
    return map_object, map_name


def get_gps_radar_paths(base_path):
    gps_folder = ''
    radar_folder = ''

    while not gps_folder or not radar_folder:
        folders = os.listdir(base_path)
        full_paths = [os.path.join(base_path, folder) for folder in folders if os.path.isdir(os.path.join(base_path,folder))]
        print(folders, full_paths)

        for folder in full_paths:
            files = os.listdir(folder)
            if len(files) > 1:
                files.sort()
                try:
                    highest_file = os.path.join(folder, files[-2])
                    if os.path.isfile(highest_file):
                        encoding, _ = detect_encoding(highest_file)
                        with open(highest_file, "rt", encoding=encoding) as file:
                            for line in file:
                                line = line.rstrip()
                                if 'GPGGA' in line or 'GPHDT' in line:
                                    gps_folder = folder
                                    full_paths.pop(full_paths.index(gps_folder))
                                    radar_folder = full_paths[0]
                                    print("GPS and radar serial port located!")
                                    break
                except IOError:
                    time.sleep(1)

            else:
                break

    return gps_folder, radar_folder


def detect_encoding(file_path):
    with open(file_path, 'rb') as file:
        raw_data = file.read()
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        if encoding == 'utf-8':
            replacer = 'QQ5±'
        else:
            replacer = 'QQ5Â±'

        #print("Cofidence:", result['confidence'])
        return encoding, replacer


def test_read_data(output_dir, nauticalMiles2meters, earth_radius, base_lat, base_long):

    # Get a list of all the files in the output directory
    files = os.listdir(output_dir)

    # Sort the files by name
    files.sort()
    files.pop(files.index("complete_log.log"))
    
    target_list = []
    for file in files:
        encoding, replacer = detect_encoding(file)
        radar_serial_data = open(os.path.join(output_dir,file), "rt", encoding=encoding)
#        print(radar_serial_data)
        for line in radar_serial_data:
            try:
                line = line.split("] ")[1]
                line = line.replace(replacer, '$RATTM,')
                if line.startswith("$RATTM"):
                    print("--------")
                    print(file)                
                    msg = pynmea2.parse(line)
                    status, ts, lat, long, target_nbr = get_target_data(msg, nauticalMiles2meters, earth_radius, base_lat,
                                                                        base_long)
                    if status:
                        target_list.append((target_nbr, lat, long))

                    #print(f"file: {file}, status: {status}, target: {target_nbr}, lat: {lat}, long: {long}")

            except Exception as e:
                print(file)
                print(line)
                print(e)
                pass
        radar_serial_data.close()
    return target_list


def get_init_gps_position(gps_data_path):
    # TODO: Check folders, return serial0/1 to correct path and read gps pos
    files = os.listdir(gps_data_path)
    files.sort()
    highest_file = os.path.join(gps_data_path, files[-2])
    encoding, _ = detect_encoding(highest_file)
    with open(highest_file, "rt", encoding=encoding) as gps_serial_data:

        GPGGA_stored = 0
        for line in reversed(list(gps_serial_data)):
            try:
                if 'GPGGA' in line.rstrip():
                    msg = pynmea2.parse(line.split('$')[1])
                    base_lat = msg.latitude  # Boat latitude
                    base_long = msg.longitude  # Boat longitud
                    GPGGA_stored = 1

                if 'GPHDT' in line.rstrip():
                    msg = pynmea2.parse(line.split('$')[1])
                    radar_bearing_from_north = float(msg.data[0]) * np.pi / (180)  # Radarns baring mot norr

                    if GPGGA_stored == 1:
                        break
            except Exception as e:
                print(e)
                pass

        return base_lat, base_long, radar_bearing_from_north


def get_target_data(msg, nauticalMiles2meters, R, base_lat, base_long):
    print(msg)
    if (msg.status == 'T'):

        timestamps = msg.timestamp.replace(tzinfo=None)

        # Finding range for target
        r = float(msg.distance) * nautical_miles_per_kilometer

        bearing_rad = np.radians(float(msg.bearing))

        # Coordinate calulcation
        d = r / nautical_miles_per_kilometer  # Distance to object (nautical miles)

        Ad = d / R  # Angular distance i.e d/R (nautical miles)

        base_lat = np.radians(base_lat)  # rad
        base_long = np.radians(base_long)  # rad

        tmp_la = np.degrees(
            np.arcsin(np.sin(base_lat) * np.cos(Ad) + np.cos(base_lat) * np.sin(Ad) * np.cos(bearing_rad)))
        tmp_lo = np.degrees(base_long + np.arctan2((np.sin(bearing_rad) * np.sin(Ad) * np.cos(base_lat)),
                                                   (np.cos(Ad) - np.sin(base_lat) * np.sin(np.radians(tmp_la)))))

        return True, timestamps, tmp_la, tmp_lo, int(msg.target_number)
    else:
        return False, None, None, None, None


log_path = r"/home/pi/sigray/logs"
#log_path = r"C:\Projects\sigray\logs\logs_20230512\log_path_Copy"
gps_data_path, radar_data_path = get_gps_radar_paths(log_path)
base_lat, base_long, radar_bearing_from_north = get_init_gps_position(gps_data_path)
init_zoom = 13
interval_time = 5 * 1000  # milliseconds

nautical_miles_per_kilometer = 1852 / 1000
earth_radius = 6371  # Radius of Earth

m, _ = create_map_object(init_zoom, base_lat, base_long)

# Create a Dash app
app = dash.Dash(__name__)
# Run the app
app.layout = html.Div([
    html.Iframe(id='map', srcDoc=m._repr_html_(), width='100%', height='1000'),
    dcc.Interval(
        id="interval",
        interval=interval_time,
        n_intervals=0
    )
])

# Define a callback function to update the map
@app.callback(Output("map", "srcDoc"),
              Input("interval", "n_intervals")
              )
def update_map(n):
    # Add new markers to the Folium map object
    new_m, _ = create_map_object(init_zoom, base_lat, base_long)
    targets = test_read_data(radar_data_path, nautical_miles_per_kilometer, earth_radius, base_lat, base_long)

    # New targets
    for target in targets:
        target_nbr, lat, long = target
        color_map = {0: "red", 1: "blue", 2: "green", 3: "purple", 4: 'orange', 5: 'darkred', 6: 'lightred', 7: 'beige',
                     8: 'darkblue', 9: 'darkgreen', 10: 'pink'}
        color = color_map[target_nbr]
        folium.CircleMarker(location=[lat, long],
                            radius=3,
                            color="black",
                            opacity=0.8,
                            weight=1,
                            fill=True,
                            fill_color=color,
                            fill_opacity=0.8,
                            ).add_to(new_m)

    # Convert the Folium map object to HTML
    html_map = new_m._repr_html_()

    # Return the HTML as a child of the Dash Map component
    return html_map



if __name__ == '__main__':
    app.run_server()
    #base_lat, base_long = (1.0061238452447892, 0.20680522662164277)
    #nauticalMiles2meters = 1852 / 1000
    #earth_radius = 3440.1  # Radius of Earth
    #output_dir = r"/home/pi/sigray/tmp_log_dir_copy/serial1"
    #test_read_data(output_dir, nauticalMiles2meters, earth_radius, base_lat, base_long)

