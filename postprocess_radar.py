import pynmea2
import numpy as np
import pandas as pd
import datetime
import os
import chardet
import folium
import logging


def create_map_object(init_zoom, radar_init_lat, radar_init_long):
    map_object = folium.Map([radar_init_lat, radar_init_long], zoom_start=init_zoom, tiles="cartodbpositron")
    folium.Marker(
        location=[radar_init_lat, radar_init_long],
        popup="Boat radar",
    ).add_to(map_object)

    return map_object


def detect_encoding(file_path):
    with open(file_path, 'rb') as file:
        raw_data = file.read()
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        if encoding == 'utf-8':
            replacer = 'QQ5±'
        else:
            replacer = 'QQ5Â±'
        return encoding, replacer


def gps_data_to_df(gps_data_path):
    if type(gps_data_path) is not list:
        gps_data_path = [gps_data_path]

    logging.basicConfig(filename='error_gps.log', level=logging.ERROR)

    for gps_dir in gps_data_path:
        files = os.listdir(gps_dir)
        df_gpgga = pd.DataFrame(
            columns=["timestamp", "message_id", "utc", "lat", "lon", "position_accuracy", "altitude_above_sea"])
        df_gphdt = pd.DataFrame(columns=["timestamp", "message_id", "heading_degrees"])
        for gps_file in files:
            gps_file = os.path.join(gps_dir, gps_file)
            encoding, _ = detect_encoding(gps_file)
            with open(gps_file, "rt", encoding=encoding) as gps_serial_data:
                for line in gps_serial_data:
                    try:
                        if 'GPGGA' in line.rstrip():
                            gpgga = pynmea2.parse(line.split('$')[1])

                            # Extract the desired information
                            timestamp = line.split('$')[0]
                            timestamp = timestamp.strip("[] ")
                            timestamp = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
                            timestamp = timestamp.timestamp()
                            message_id = gpgga.sentence_type
                            utc = gpgga.timestamp.replace(tzinfo=None)
                            lat = gpgga.latitude
                            lon = gpgga.longitude
                            position_accuracy = gpgga.gps_qual
                            altitude_above_sea = gpgga.altitude

                            df_gpgga = pd.concat([df_gpgga, pd.Series({"timestamp": timestamp,
                                                                       "message_id": message_id,
                                                                       "utc": utc,
                                                                       "lat": lat,
                                                                       "lon": lon,
                                                                       "position_accuracy": position_accuracy,
                                                                       "altitude_above_sea": altitude_above_sea}).to_frame().T],
                                                 ignore_index=True)

                        if 'GPHDT' in line.rstrip():
                            gphdt = pynmea2.parse(line.split('$')[1])

                            # Extract the desired information
                            timestamp = line.split('$')[0]
                            timestamp = timestamp.strip("[] ")
                            timestamp = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
                            timestamp = timestamp.timestamp()
                            message_id = gphdt.sentence_type
                            heading_degrees = float(gphdt.heading) * np.pi / 180

                            df_gphdt = pd.concat([df_gphdt, pd.Series({"timestamp": timestamp,
                                                                       "message_id": message_id,
                                                                       "heading_degrees": heading_degrees}).to_frame().T],
                                                 ignore_index=True)

                    except Exception as e:
                        # Handle parse errors, if any
                        logging.error(str(e))
                        pass

    return df_gpgga, df_gphdt


def radar_data_to_df(radar_data_path):
    if type(radar_data_path) is not list:
        radar_data_path = [radar_data_path]

    logging.basicConfig(filename='error_radar.log', level=logging.ERROR)

    df = pd.DataFrame(
        columns=["timestamp", "message_id", 'target_number', 'distance', 'bearing', 'brg_ref', 'speed', 'cog',
                 'cog_unit', 'dist_cpa', 'time_cpa', 'dist_unit', 'name', 'status', 'reference', 'utc', 'acquisition'])
    for radar_data in radar_data_path:
        encoding, replacement_string = detect_encoding(radar_data)
        with open(radar_data, "rt", encoding=encoding) as radar_serial_data:
            for line in radar_serial_data:
                try:

                    line = line.replace(replacement_string, '$RATTM,')
                    if 'RATTM' in line.rstrip():
                        rattm = pynmea2.parse(line.split('$')[1])

                        # Extract the desired information
                        timestamp = line.split('$')[0]
                        timestamp = timestamp.strip("[] ")
                        timestamp = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
                        timestamp = timestamp.timestamp()
                        message_id = rattm.sentence_type
                        utc = rattm.timestamp.replace(tzinfo=None)
                        target_number = rattm.target_number
                        distance = rattm.distance
                        bearing = rattm.bearing
                        brg_ref = rattm.brg_ref
                        speed = rattm.speed
                        cog = rattm.cog
                        cog_unit = rattm.cog_unit
                        dist_cpa = rattm.dist_cpa
                        time_cpa = rattm.time_cpa
                        dist_unit = rattm.dist_unit
                        name = rattm.name
                        status = rattm.status
                        reference = rattm.reference
                        utc = rattm.timestamp
                        acquisition = rattm.acquisition

                        df = pd.concat([df, pd.Series({"timestamp": timestamp,
                                                       "message_id": message_id,
                                                       'target_number': target_number,
                                                       'distance': distance,
                                                       'bearing': bearing,
                                                       'brg_ref': brg_ref,
                                                       'speed': speed,
                                                       'cog': cog,
                                                       'cog_unit': cog_unit,
                                                       'dist_cpa': dist_cpa,
                                                       'time_cpa': time_cpa,
                                                       'dist_unit': dist_unit,
                                                       'name': name,
                                                       'status': status,
                                                       'reference': reference,
                                                       'utc': utc,
                                                       'acquisition': acquisition}).to_frame().T], ignore_index=True)

                except Exception as e:
                    # Handle parse errors, if any
                    logging.error(str(e))
                    pass
    return df


def create_combined_dataframe(df_rattm, df_gpgga, df_gphdt, nautical_miles_per_kilometer, earth_radius):
    closest_values = []

    timestamps_gpgga = pd.to_datetime(df_gpgga['timestamp'], unit='s')
    timestamps_gphdt = pd.to_datetime(df_gphdt['timestamp'], unit='s')

    # Iterate over each timestamp in DataFrame B
    for timestamp_b in df_rattm['timestamp']:
        timestamp_b = pd.to_datetime(timestamp_b, unit='s')

        # Calculate the time difference between each timestamp in B and all timestamps in A
        time_diff_gpgga = np.abs(timestamps_gpgga - timestamp_b)
        time_diff_gphdt = np.abs(timestamps_gphdt - timestamp_b)

        # Find the index of the timestamp in A with the minimum time difference
        closest_index_gpgga = time_diff_gpgga.idxmin()
        closest_index_gphdt = time_diff_gphdt.idxmin()

        # Get the corresponding value from A using the closest index
        closest_lat = df_gpgga.loc[closest_index_gpgga, 'lat']
        closest_long = df_gpgga.loc[closest_index_gpgga, 'lon']
        closest_heading = float(df_gphdt.loc[closest_index_gphdt, 'heading_degrees'])

        # Add the closest value to the list
        closest_values.append([closest_lat, closest_long, closest_heading])

    gps_df = pd.DataFrame(np.array(closest_values), columns=['lat_ref', 'long_ref', 'bearing_ref'])
    df_comb = pd.concat([df_rattm, gps_df], axis=1)
    df_comb[['calculated_lat', 'calculated_long']] = df_comb.apply(calculate_lat_and_long,
                                                                   args=(nautical_miles_per_kilometer, earth_radius,),
                                                                   axis=1)
    return df_comb


def calculate_lat_and_long(row, nautical_miles_per_kilometer, earth_radius):
    if row.status == 'T':

        # Finding range for target
        r = float(row.distance) * nautical_miles_per_kilometer  # km

        bearing_rad = np.radians(float(row.bearing))  # rad

        # Coordinate calculation
        d = r / nautical_miles_per_kilometer  # Distance to object km

        Ad = d / earth_radius  # Angular distance i.e d/R (nautical miles) # (rad)

        lat1 = np.radians(row.lat_ref)  # rad
        long1 = np.radians(row.long_ref)  # rad

        tmp_la = np.degrees(np.arcsin(np.sin(lat1) * np.cos(Ad) + np.cos(lat1) * np.sin(Ad) * np.cos(bearing_rad)))
        tmp_lo = np.degrees(long1 + np.arctan2((np.sin(bearing_rad) * np.sin(Ad) * np.cos(lat1)),
                                               (np.cos(Ad) - np.sin(lat1) * np.sin(np.radians(tmp_la)))))
    else:
        tmp_lo = None
        tmp_la = None

    return pd.Series([tmp_la, tmp_lo], index=['calculated_lat', 'calculated_long'])


def postprocess_radar_data(gps_data_path, radar_data_path, nautical_miles_per_kilometer, earth_radius):
    df_gpgga, df_gphdt = gps_data_to_df(gps_data_path)
    df_rattm = radar_data_to_df(radar_data_path)
    df_comb = create_combined_dataframe(df_rattm, df_gpgga, df_gphdt, nautical_miles_per_kilometer, earth_radius)
    return df_comb


if __name__ == '__main__':
    gps_data_path = [r"C:\Projects\sigray\logs\logs_20230512\log_path_demo\2023_05_16_13_30\serial1",
                     r"C:\Projects\sigray\logs\logs_20230512\log_path_demo\2023_05_16_11_30\serial1"]
    radar_data_path = [r"C:\Projects\sigray\logs\logs_20230512\log_path_demo\2023_05_16_13_30\serial0\complete_log.log",
                       r"C:\Projects\sigray\logs\logs_20230512\log_path_demo\2023_05_16_11_30\serial0\complete_log.log"]
    nautical_miles_per_kilometer = 1852 / 1000
    earth_radius = 6371  # Radius of Earth
    df = postprocess_radar_data(gps_data_path, radar_data_path, nautical_miles_per_kilometer, earth_radius)

