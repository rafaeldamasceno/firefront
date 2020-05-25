import numpy as np
import math
from genForeFireCase import FiretoNC
from pyproj import Proj, transform

lcs_to_clcs = {
    2: 333,
    17: 323,
    21: 312,
    22: 312,
    23: 313,
    24: 313,
    25: 311,
    26: 311,
    30: 242,
    35: 241,
    41: 321,
    42: 321,
    52: 323,
    55: 324,
    57: 324,
    60: 313,
    62: 312,
    91: 324,
    100: 523,
    101: 111,
    105: 111,
    109: 112,
    113: 112,
    117: 112,
    121: 111}

def get_lcs():
    with open('LC-7-25-17.bin', 'rb') as f:
        lcs = []
        byte = f.read(1)
        while byte:
            lc = int.from_bytes(byte, 'little')
            if lc not in lcs:
                lcs.append(lc) 
            byte = f.read(1)
        lcs.sort()
        return lcs

def convert_lcs_to_fuel(path):
    fuel = []
    with open(path, 'rb') as lcs:
        byte = lcs.read(1)
        while byte:
            lc = int.from_bytes(byte, 'little')
            try:
                fuel.append(lcs_to_clcs[lc])
            except KeyError:
                fuel.append(322)
            byte = lcs.read(1)
    return fuel

def convert_dem_to_altitude(path):
    altitude = []
    with open(path, 'rb') as dem:
            byte = dem.read(2)
            n = 0
            while byte:
                height = int.from_bytes(byte, 'little')
                altitude.append(height)
                byte = dem.read(2)
    return altitude

def write_to_file(filename, list, size):
    with open(filename, 'w') as f:
        n = 0
        for e in list:
            f.write(f'{e}, ')
            n += 1
            if n == size:
                f.write('\n')
                n = 0

def calculate_qmid_bounds(left, right, top, bottom):
    l = 7
    
    factor = 2 ** (l - 1)
    width = 240 / factor
    height = 180 / factor

    min_u = None
    max_u = None
    max_v = None
    min_v = None

    min_long = None
    max_long = None
    max_lat = None
    min_lat = None

    for u in range(96):
        left_long = u * width - 180
        right_long = left_long + width

        if min_u is None and left_long < left and right_long > left:
            min_u = u
            min_long = left_long

        if max_u is None and left_long < right and right_long > right:
            max_u = u
            max_long = right_long

        if min_u is not None and max_u is not None:
            break

    for v in range(64):
        top_lat = 90 - v * height
        bottom_lat = top_lat - height

        if min_v is None and top_lat > top and bottom_lat < top:
            min_v = v
            max_lat = top_lat

        if (max_v is None and top_lat > bottom and bottom_lat < bottom):
            max_v = v
            min_lat = bottom_lat

        if min_v is not None and max_v is not None:
            break

    return (min_u, max_u, max_v, min_v), (min_long, max_long, max_lat, min_lat)

def prepare_landscape(left, right, top, bottom, proj, path):
    #lcs = get_lcs()
    qmid, coords = calculate_qmid_bounds(left, right, top, bottom)
    # print(qmid, coords)

    to_proj = Proj(proj) # conformal projection in metres
    from_proj = Proj('epsg:4326') # WGS 84, used by FSX

    sw_coords = transform(from_proj, to_proj, coords[3], coords[0])
    ne_coords = transform(from_proj, to_proj, coords[2], coords[1])
    length_x = ne_coords[0] - sw_coords[0]
    length_y = ne_coords[1] - sw_coords[1]

    # print(length_x, length_y)

    domainProperties = {
        'SWy': sw_coords[1],
        'SWx': sw_coords[0],
        'SWz': 0,
        'Lx': length_x,
        'Ly': length_y,
        'Lz': 0, 't0': 0,
        'Lt': float('inf')
    }

    fuel = None
    for v in range(qmid[3], qmid[2] + 1):
        row_fuel = None
        for u in range(qmid[0], qmid[1] + 1):
            # print(u, v)
            grid_fuel = convert_lcs_to_fuel(f'TerrainLandClass/LC-7-{u}-{v}.bin')
            grid_fuel = np.array(grid_fuel).reshape(257, 257)
            # print(grid_fuel)
            if row_fuel is None:
                row_fuel = grid_fuel
            else:
                row_fuel = np.concatenate((row_fuel[:,:-1], grid_fuel), axis=1)
        # print(row_fuel)
        if fuel is None:
                fuel = row_fuel
        else:
            fuel = np.concatenate((fuel[:-1,:], row_fuel))
    # print(fuel.shape)
    fuel = fuel[::-1]

    altitude = None
    for v in range(qmid[3], qmid[2] + 1):
        row_altitude = None
        for u in range(qmid[0], qmid[1] + 1):
            # print(u, v)
            grid_altitude = convert_dem_to_altitude(f'TerrainElevation/DEM-7-{u}-{v}.bin')
            grid_altitude = np.array(grid_altitude).reshape(257, 257)
            # print(grid_altitude)
            if row_altitude is None:
                row_altitude = grid_altitude
            else:
                row_altitude = np.concatenate((row_altitude[:,:-1], grid_altitude), axis=1)
        # print(row_altitude)
        if altitude is None:
                altitude = row_altitude
        else:
            altitude = np.concatenate((altitude[:-1,:], row_altitude))
    # print(altitude.shape)
    altitude = altitude[::-1]

    # fuel = convert_lcs_to_fuel()
    # write_to_file('fuel.txt', fuel, 257)
    # fuel = np.array(fuel).reshape(257, 257)[::-1]
    # fuel = fuel.repeat(2,axis=0).repeat(2,axis=1)

    # altitude = convert_dem_to_altitude()
    # write_to_file('altitude.txt', altitude, 257)
    # altitude = np.array(altitude).reshape(257, 257)[::-1]
    # altitude = altitude.repeat(2,axis=0).repeat(2,axis=1)

    wind_speed = 30
    wind_angle = math.radians(45)

    wind = {
        'zonal': np.repeat(wind_speed * math.sin(wind_angle), 257 * 257).reshape(257, 257),
        'meridian': np.repeat(wind_speed * math.cos(wind_angle), 257 * 257).reshape(257, 257)
    }

    FiretoNC(path, domainProperties, {'projection': 'EPSG:3857'}, fuel, altitude, wind)

if __name__ == "__main__":
    prepare_landscape(-10.9, -6, 42.1, 37, 'EPSG:3857', 'fsx.nc')