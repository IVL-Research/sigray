import pynmea2
import numpy as np
import folium
import sys

# Dash
import dash
from dash import dcc, html
import os
from dash.dependencies import Input, Output, State

def get_init_gps_position(gps_data_path):
    # TODO: Check folders, return serial0/1 to correct path and read gps pos
    GPS_serial_data = open(gps_data_path, "rt")

    GPGGA_stored = 0
    for line in reversed(list(GPS_serial_data)):

        if 'GPGGA' in line.rstrip():
            msg2 = pynmea2.parse(line.split('$')[1])
            base_lat = np.radians(msg2.latitude)  # Boat latitude
            base_long = np.radians(msg2.longitude)  # Boat longitude
            GPGGA_stored = 1

        if 'GPHDT' in line.rstrip():
            msg3 = pynmea2.parse(line.split('$')[1])
            radar_bearing_from_north = float(msg3.data[0]) * np.pi / (180)  # Radarns bäring mot norr

            if GPGGA_stored == 1:
                break

    return base_lat, base_long, radar_bearing_from_north

def get_data(output_dir, nauticalMiles2meters, earth_radius, base_lat, base_long):

    # Create a output log file if not existing
    output_log = os.path.join(output_dir, 'complete_log.log')
    if not os.path.exists(output_log):
        with open(output_log, 'w') as f:
            pass

    # Get a list of all the files in the output directory
    files = os.listdir(output_dir)
    target_list = []
    if len(files) >= 2:

        # Sort the files by name
        files.sort()

        # Get the second to last file (-2)
        highest_file = os.path.join(output_dir, files[-2])

        radar_serial_data = open(highest_file, "rt", encoding='cp1252')

        for line in radar_serial_data:
            line = line.replace('QQ5±', '$RATTM,')
            if 'RATTM' in line:
                msg = pynmea2.parse(line.split('$')[1])
                status, ts, lat, long, target_nbr = get_target_data(msg, nauticalMiles2meters, earth_radius, base_lat,
                                                                    base_long)
                if status:
                    target_list.append((target_nbr, lat, long))

            # Append the lines to the output file
            with open(output_log, 'a') as f:
                f.writelines(line)

        radar_serial_data.close()
        os.remove(highest_file)

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
                                                   (np.cos(Ad) - np.sin(base_lat) * np.sin(tmp_la))))

        return True, timestamps, tmp_la, tmp_lo, int(msg.target_number)
    else:
        return False, None, None, None, None


gps_data_path = r"/home/pi/sigray/logs/gps"
base_lat, base_long, radar_bearing_from_north = get_init_gps_position(gps_data_path)
init_zoom = 13
interval_time = 1 * 1000  # milliseconds

radar_data_path = r"/home/pi/sigray/logs/radar"
#output_dir = r"C:\Projects\sigray\logs\logs_20230512\logs"

nauticalMiles2meters = 1852 / 1000
earth_radius = 3440.1  # Radius of Earth

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
    print("Enter")
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
