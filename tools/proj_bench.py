from conversion_tools import convert_coordinates
import time
import random

NUM_TRIES = 10
MAX = 500

coords = []

times = [0] * MAX

for i in range(MAX):
    coords.append((random.uniform(-90, 90), random.uniform(-180, 180)))

for j in range(NUM_TRIES):
    start = time.perf_counter()
    for i in range(len(coords)):
        convert_coordinates(coords[i], 'EPSG:3395')
        times[i] += time.perf_counter() - start

print([n / NUM_TRIES for n in times])