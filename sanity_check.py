import pynmea2
import numpy as np
import folium
import time

# Dash
import dash
from dash import dcc, html
import os
from dash.dependencies import Input, Output, State


def get_gps_radar_paths(base_path):
    gps_folder = ''
    radar_folder = ''
    located = 0
    while not gps_folder or not radar_folder:
        folders = os.listdir(base_path)
        full_paths = [os.path.join(base_path, folder) for folder in folders if
                      os.path.isdir(os.path.join(base_path, folder))]

        for folder in full_paths:
            if not gps_folder or not radar_folder:
                files = os.listdir(folder)
                if len(files) > 1:
                    files.sort(reverse=True)
                    try:
                        for file1 in files:
                            highest_file = os.path.join(folder, file1)
                            #print(highest_file)
                            if os.path.isfile(highest_file):
                                with open(highest_file, "rt", encoding='cp1252') as file:
                                    for line in file:
                                        line = line.rstrip()
                                        if 'GPGGA' in line or 'GPHDT' in line:
                                            gps_folder = folder
                                            #print(full_paths)
                                            full_paths.pop(full_paths.index(gps_folder))
                                            radar_folder = full_paths[0]
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

    return radar_folder, base_lat, base_long, radar_bearing_from_north


def get_init_gps_position(gps_data_path):

    with open(gps_data_path, "rt", encoding='cp1252') as gps_serial_data:

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


def get_data(output_dir, nauticalMiles2meters, earth_radius, base_lat, base_long):
    # Create a output log file if not existing
    # output_log = os.path.join(output_dir, 'complete_log.log')
    # if not os.path.exists(output_log):
    #     with open(output_log, 'w') as f:
    #         pass

    # Get a list of all the files in the output directory
    #files = os.listdir(output_dir)
    target_list = []
    #if len(files) >= 2:

    # Sort the files by name
    #files.sort()
    #files.pop(files.index("complete_log.log"))

    # Get the second to last file (-2)
    #highest_file = os.path.join(output_dir, files[-2])

    radar_serial_data = open(os.path.join(output_dir, 'complete_log.log'), "rt", encoding='utf-8')

    for line in radar_serial_data:
        try:
            # Append the lines to the output file
            #with open(output_log, 'a') as f:
            #    f.writelines(line)

            line = line.split("] ")[1]
            line = line.replace('QQ5±', '$RATTM,')
            if line.startswith("$RATTM"):
                msg = pynmea2.parse(line)
                status, ts, lat, long, target_nbr = get_target_data(msg, nauticalMiles2meters, earth_radius,
                                                                    base_lat,
                                                                    base_long)
                if status:
                    target_list.append((target_nbr, lat, long))

        except Exception as e:
            print(e)
            print(line)
            #print(f"at file {highest_file} and line {line}")
            pass

    radar_serial_data.close()
    print(target_list)

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


def get_target_data(msg, nauticalMiles2meters, R, base_lat, base_long):
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
                                                   (np.cos(Ad) - np.sin(base_lat) * np.sin(np.radians(tmp_la)))))

        return True, timestamps, tmp_la, tmp_lo, int(msg.target_number)
    else:
        return False, None, None, None, None


log_path = r"/home/pi/sigray/logs"
#log_path = r"C:\Users\jens3109\Downloads\2023_05_16_13_30\logs"
radar_data_path, base_lat, base_long, radar_bearing_from_north = get_gps_radar_paths(log_path)
print(radar_data_path, np.degrees(base_lat), np.degrees(base_long), radar_bearing_from_north)
init_zoom = 13
interval_time = 10 * 1000  # milliseconds
nauticalMiles2meters = 1852 / 1000
earth_radius = 3440.1  # Radius of Earth in nautic miles

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
    targets = get_data(radar_data_path, nauticalMiles2meters, earth_radius, base_lat, base_long)

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