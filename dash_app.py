import folium
import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output, State
from postprocess_radar import postprocess_radar_data, create_map_object


# Define a Dash app
app = dash.Dash(__name__)

m = None

# Define the app layout
app.layout = html.Div([
    html.Iframe(id='map', srcDoc='', width='100%', height='1000'),
    dcc.Store(id='stored_targets_prev', data=[]),
    dcc.Store(id='stored_targets_hist', data=[]),
    dcc.Interval(
        id="interval",
        interval=10000,     # placeholder for main
        n_intervals=0
    )
])


# Define a callback function to update the map
@app.callback(
    Output("map", "srcDoc"),
    Output('stored_targets_prev', 'data'),
    Output('stored_targets_hist', 'data'),
    Input("interval", "n_intervals"),
    State('stored_targets_prev', 'data'),
    State('stored_targets_hist', 'data')
)
def update_map(n, old_targets, hist_targets):
    # Current interval
    interval_seconds = n * interval_time / 1000

    # Calculate the start and end timestamps based on the interval
    start_time = df['timestamp'].iloc[0] + (interval_seconds - interval_time / 1000)
    end_time = df['timestamp'].iloc[0] + interval_seconds

    # Add new markers to the Folium map object
    new_m = create_map_object(init_zoom, base_lat, base_long)

    filtered_df = df[(df['timestamp'] >= start_time) & (df['timestamp'] <= end_time)]
    filtered_df = filtered_df.dropna()
    targets = []

    # New targets
    for target_nbr, lat, long in zip(filtered_df.target_number, filtered_df.calculated_lat,
                                     filtered_df.calculated_long):
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
        targets.append((target_nbr, lat, long))

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
    init_zoom = 14
    interval_time = 2 * 1000
    nautical_miles_per_kilometer = 1852 / 1000
    earth_radius = 6371  # Radius of Earth
    gps_data_path = [r"C:\Projects\sigray\logs\logs_20230512\log_path_demo\2023_05_16_13_30\serial1",
                     r"C:\Projects\sigray\logs\logs_20230512\log_path_demo\2023_05_16_11_30\serial1"]
    radar_data_path = [r"C:\Projects\sigray\logs\logs_20230512\log_path_demo\2023_05_16_13_30\serial0\complete_log.log",
                       r"C:\Projects\sigray\logs\logs_20230512\log_path_demo\2023_05_16_11_30\serial0\complete_log.log"]

    # Get processed radar data
    df = postprocess_radar_data(gps_data_path, radar_data_path, nautical_miles_per_kilometer, earth_radius)

    # Create the initial map object
    base_lat, base_long = df.iloc[0][['lat_ref', 'long_ref']]
    m = create_map_object(init_zoom, base_lat, base_long)

    # Update the interval time in the Dash layout
    app.layout['interval'].interval = interval_time
    # Run the app
    app.run_server()
