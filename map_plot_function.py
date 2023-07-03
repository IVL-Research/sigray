
import pynmea2
import numpy as np
import folium
import time
import dash
from dash import dcc, html
import os
from dash.dependencies import Input, Output, State
import chardet


log_path = r"/home/pi/sigray/logs"
log_path = r"C:\Users\elias4318\OneDrive - IVL Svenska Miljöinstitutet AB\Skrivbordet\2023_05_16_13_30\logs"
init_zoom = 13
interval_time = 5 * 1000  # milliseconds
nautical_miles_per_kilometer = 1852 / 1000
earth_radius = 3440.1

#encoding = "utf-8"
encoding = "cp1252"
if encoding == "cp1252":
    to_replace = 'QQ5Â±'
else:
    to_replace = 'QQ5±'


def get_gps_radar_paths():
    gps_data_path = ''
    radar_data_path = ''
    located = 0
    while not gps_data_path or not radar_data_path:
        folders = os.listdir(log_path)
        full_paths = [os.path.join(log_path, folder) for folder in folders if
                      os.path.isdir(os.path.join(log_path, folder))]

        for folder in full_paths:
            if not gps_data_path or not radar_data_path:
                files = os.listdir(folder)
                if len(files) > 1:
                    files.sort(reverse=True)
                    try:
                        for file1 in files:
                            highest_file = os.path.join(folder, file1)
                            #print(highest_file)
                            if os.path.isfile(highest_file):
                                with open(highest_file, "rt", encoding=encoding) as file:
                                    for line in file:
                                        line = line.rstrip()
                                        if 'GPGGA' in line or 'GPHDT' in line:
                                            gps_data_path = folder
                                            #print(full_paths)
                                            full_paths.pop(full_paths.index(gps_data_path))
                                            radar_data_path = full_paths[0]
                                            print("GPS and radar serial port located!")
                                            located = 1
                                            break
                            if located:
                                base_lat, base_long, radar_bearing_from_north = get_init_gps_position(highest_file)
                                break
                    except IOError:
                        time.sleep(1)

            else:
                break

    return radar_data_path, gps_data_path, base_lat, base_long, radar_bearing_from_north


def get_init_gps_position(gps_data_path):

    with open(gps_data_path, "rt", encoding=encoding) as gps_serial_data:

        GPGGA_stored = 0
        for line in reversed(list(gps_serial_data)):
            try:
                if 'GPGGA' in line.rstrip():
                    msg = pynmea2.parse(line.split('$')[1])
                    base_lat = np.radians(msg.latitude)  # Boat latitude
                    base_long = np.radians(msg.longitude)  # Boat longitud
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


def get_data():


    # Get a list of all the files in the output directory
    files = os.listdir(radar_data_path)
    files_gps = os.listdir(gps_data_path)

    target_list = []
    if len(files) >= 2:
        # Sort the files by name
        files.sort()

        # Get the second to last file (-2)
        highest_file_radar = os.path.join(radar_data_path, files[-2])
        radar_serial_data = open(highest_file, "rt", encoding=encoding)

        for line in radar_serial_data:
            try:
                line = line.split("] ")[1]
                line = line.replace(to_replace, '$RATTM,')
                if line.startswith("$RATTM"):
                    msg = pynmea2.parse(line)
                    status, ts, lat, long, target_nbr = get_target_data(msg)
                    if status:
                        target_list.append((target_nbr, lat, long))

            except Exception as e:
                print(e)
                print(f"at file {highest_file} and line {line}")
                pass

        radar_serial_data.close()

        os.rename(highest_file, os.path.join(radar_archive_path, files[-2]))

    if len(files_gps) >= 2:
        highest_file_gps = os.path.join(gps_data_path, files_gps[-2])
        # move gps file to archive
        os.rename(highest_file_gps, os.path.join(gps_archive_path, files_gps[-2]))


    return target_list


def create_map_object(init_zoom, radar_init_lat, radar_init_long):
    map_object = folium.Map([np.degrees(radar_init_lat), np.degrees(radar_init_long)], zoom_start=init_zoom,
                            tiles="cartodbpositron")
    folium.Marker(
        location=[np.degrees(radar_init_lat), np.degrees(radar_init_long)],
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


def create_archive_logging():
    # Check base directory and create if now created
    base_path = os.path.join(os.path.dirname(log_path), 'archive_logs')
    if not os.path.isdir(base_path):
        os.mkdir(base_path)

    # Create datetime directory
    timestamp = datetime.datetime.now()
    timestamp = timestamp.strftime("%Y_%m_%d-%H_%M_%S")
    archive_path = os.path.join(base_path, timestamp)
    os.mkdir(archive_path)

    # Create radar and gps paths
    radar_archive_path = os.path.join(archive_path, os.path.basename(radar_data_path))
    gps_archive_path = os.path.join(archive_path, os.path.basename(gps_data_path))
    os.mkdir(radar_archive_path)
    os.mkdir(gps_archive_path)

    return radar_archive_path, gps_archive_path


def get_target_data(msg):
    if (msg.status == 'T'):

        timestamps = msg.timestamp.replace(tzinfo=None)

        # Finding range for target
        r = float(msg.distance) * nautical_miles_per_kilometer

        bearing_rad = np.radians(float(msg.bearing))

        # Coordinate calulcation
        d = r / nautical_miles_per_kilometer  # Distance to object (nautical miles)

        Ad = d / earth_radius  # Angular distance i.e d/R (nautical miles)

        tmp_la = np.degrees(
            np.arcsin(np.sin(base_lat) * np.cos(Ad) + np.cos(base_lat) * np.sin(Ad) * np.cos(bearing_rad)))
        tmp_lo = np.degrees(base_long + np.arctan2((np.sin(bearing_rad) * np.sin(Ad) * np.cos(base_lat)),
                                                   (np.cos(Ad) - np.sin(base_lat) * np.sin(np.radians(tmp_la)))))

        return True, timestamps, tmp_la, tmp_lo, int(msg.target_number)
    else:
        return False, None, None, None, None

radar_data_path, gps_data_path, base_lat, base_long, radar_bearing_from_north = get_gps_radar_paths()
radar_archive_path, gps_archive_path = create_archive_logging()
m, _ = create_map_object(init_zoom, base_lat, base_long)

# Create a Dash app
app = dash.Dash(__name__)
# Run the app
app.layout = html.Div([
    html.Iframe(id='map', srcDoc=m._repr_html_(), width='100%', height='1000'),
    dcc.Store(id='stored_targets_prev', data=[]),
    dcc.Store(id='stored_targets_hist', data=[]),
    dcc.Interval(
        id="interval",
        interval=interval_time,
        n_intervals=0
    )
])

# Define a callback function to update the map
@app.callback(Output("map", "srcDoc"),
              Output('stored_targets_prev', 'data'),
              Output('stored_targets_hist', 'data'),
              Input("interval", "n_intervals"),
              State('stored_targets_prev', 'data'),
              State('stored_targets_hist', 'data'))
def update_map(n, old_targets, hist_targets):
    # Add new markers to the Folium map object
    new_m, _ = create_map_object(init_zoom, base_lat, base_long)
    targets = get_data()

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

    # Previous targets
    for old_target in old_targets:
        target_nbr, lat, long = old_target
        color_map = {0: "red", 1: "blue", 2: "green", 3: "purple", 4: 'orange', 5: 'darkred', 6: 'lightred', 7: 'beige',
                     8: 'darkblue', 9: 'darkgreen', 10: 'pink'}
        color = color_map[target_nbr]
        folium.CircleMarker(location=[lat, long],
                            radius=3,
                            color="black",
                            opacity=0.5,
                            weight=1,
                            fill=True,
                            fill_color=color,
                            fill_opacity=0.5,
                            ).add_to(new_m)

    # Previous targets
    for hist_target in hist_targets:
        target_nbr, lat, long = hist_target
        color_map = {0: "red", 1: "blue", 2: "green", 3: "purple", 4: 'orange', 5: 'darkred', 6: 'lightred', 7: 'beige',
                     8: 'darkblue', 9: 'darkgreen', 10: 'pink'}
        color = color_map[target_nbr]
        folium.CircleMarker(location=[lat, long],
                            radius=3,
                            color="black",
                            opacity=0.2,
                            weight=1,
                            fill=True,
                            fill_color=color,
                            fill_opacity=0.2,
                            ).add_to(new_m)

    # Convert the Folium map object to HTML
    html_map = new_m._repr_html_()

    # Return the HTML as a child of the Dash Map component
    return html_map, targets, old_targets


# Run the app
if __name__ == '__main__':

    app.run_server()
