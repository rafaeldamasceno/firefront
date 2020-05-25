from pyproj import Proj, transform
import os
import json

i = 0

epsg3857 = Proj('epsg:3857')
epsg4326 = Proj('epsg:4326')

for _, _, files in os.walk('../Examples/aullene'):
    for file in files:
        if file.endswith(f'.json'):
            with open('../Examples/aullene/' + file) as json_file:
                data = json.load(json_file)
                polygon = data['fronts'][0]['coordinates']

                new_polygon = []

                for vertex in polygon.split(' '):
                    coordinates = vertex.split(',')[:2]
                    new_polygon.append(transform(epsg3857, epsg4326, coordinates[0], coordinates[1]))

                print(f'#P{i}')
                for lat, lon in new_polygon:
                    print(f'{lat}, {lon}')
                i += 1
