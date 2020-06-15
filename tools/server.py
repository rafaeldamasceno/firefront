from conversion_tools import calculate_qmid_bounds, calculate_wind_map, prepare_landscape, convert_coordinates, convert_polygon, convert_wind_to_u_v
from datetime import datetime
import json
import pika
import pexpect
from select import select
import signal
import ssl
import time
import threading

PROJECTION = 'EPSG:3395'
LANDSCAPE_FILE = 'fsx.nc'
TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

context = ssl.create_default_context(
    cafile="/mnt/c/Users/Rafael/Desktop/SimPlatform/certificates/CA certificate/ca_certificate.pem")
context.load_cert_chain("/mnt/c/Users/Rafael/Desktop/SimPlatform/certificates/FireFront certificate/FireFront_certificate_signed.pem",
                        "/mnt/c/Users/Rafael/Desktop/SimPlatform/certificates/FireFront certificate/FireFront_private_key.pem")
ssl_options = pika.SSLOptions(context, '127.0.0.1')
conn_params = pika.ConnectionParameters(port=5671, ssl_options=ssl_options, credentials=pika.credentials.ExternalCredentials())


# credentials = pika.PlainCredentials('admin', 'admin')
# connection = pika.BlockingConnection(pika.ConnectionParameters(host='192.168.0.101', credentials=credentials))

connection = pika.BlockingConnection(conn_params)

channel = connection.channel()

channel.exchange_declare('ForeFire')
channel.queue_declare(queue='ForeFireRecv')
channel.queue_declare(queue='ForeFireSend')
channel.queue_bind('ForeFireRecv', 'ForeFire', routing_key='ForeFireRecv')
channel.queue_bind('ForeFireSend', 'ForeFire', routing_key='ForeFireSend')

forefire = None
current_time = None

qmid = None
coords = None

airports = {}
winds = {}
wind_map = None

threads = []

def send_message(msg_body):
    channel.basic_publish(exchange='ForeFire', routing_key='ForeFireSend', body=msg_body)

def init(left, right, top, bottom):
    global current_time, qmid, coords, airports

    if forefire is not None and not forefire.terminated:
        return

    qmid, coords = calculate_qmid_bounds(left, right, top, bottom)

    with open('/mnt/c/FEUP/runways.csv') as f:
        for line in f.readlines():
            data = line.split(',', 4)
            if data[0].isalpha() and len(data[0]) == 4 and data[0] not in airports:
                airports[data[0]] = (float(data[2]), float(data[3]))
    
    airports = {airport: coords for airport, coords in airports.items() 
    if (coords[1] > left and coords[1] < right and coords[0] < top and coords[0] > bottom)}

    send_message(f"WIND {' '.join([airport for airport, _ in airports.items()])}")

def fire(lat, lon, t):
    if forefire is None or forefire.terminated:
        return
    x, y = convert_coordinates((lat, lon), PROJECTION)
    forefire.sendline(f'startFire[loc=({x},{y},{t});t=0]')

def step():
    global current_time, threads
    if forefire is None or forefire.terminated:
        return
    previous_time = current_time
    start_timer = time.perf_counter()
    new_event = False
    # i = 0
    while not new_event:
        # i += 1
        forefire.sendline(f'step[dt=1]')

        try:
            forefire.expect(['0: ', 'trashing'], timeout=0.1)
            new_event = True
            forefire.sendline('print[]')
            forefire.expect('\r\n({.*})\r\n')
            result = json.loads(forefire.match.group(1).decode())
            if result['fronts'][0]['date'] > current_time:
                current_time = result['fronts'][0]['date']
            # send_fire_info(result, previous_time, start_timer)
            threading.Thread(target=send_fire_info, args=(result, previous_time, start_timer)).start()
        except pexpect.exceptions.TIMEOUT:
            continue

def send_fire_info(result, previous_time, start_timer):
    polygon = convert_polygon(result, PROJECTION)
    end_timer = time.perf_counter()
    if previous_time is not None:
        time_difference = (datetime.strptime(current_time, TIME_FORMAT) - datetime.strptime(previous_time, TIME_FORMAT)).total_seconds()
        # f = open(result['fronts'][0]['date'], 'w')
        # f.write(f'{time_difference} {end_timer - start_timer} {time_difference / (end_timer - start_timer)}')
        # f.close()
        print(time_difference, end_timer - start_timer, time_difference / (end_timer - start_timer))

def process_metar(airport, heading, speed, unit):
    global winds
    winds[airport] = convert_wind_to_u_v(heading, speed, unit)
    signal.setitimer(signal.ITIMER_REAL, 0.1)
    

def prepare_wind_map(signum, frame):
    global airports, wind_map
    airports = {airport:coordinates for airport, coordinates in airports.items() if airport in winds.keys()}
    wind_map = calculate_wind_map(qmid, coords, winds, airports)
    send_message('READY')

def finish_init(date):
    global forefire, current_time

    prepare_landscape(
    qmid,
    coords,
    PROJECTION,
    wind_map,
    LANDSCAPE_FILE)
    
    forefire = pexpect.spawn('../CommandShell', echo=False)
    forefire.readline() # greeting lines
    forefire.readline() # greeting lines

    init_data = [f'setParameter[projection={PROJECTION}]',
        'setParameter[fuelsTableFile=../Examples/aullene/fuels.ff]',
        'setParameter[spatialIncrement=3]',
        'setParameter[propagationModel=Rothermel]',
        'setParameter[minSpeed=0.02]',
        'setParameter[dumpMode=json]',
        'setParameter[caseDirectory=.]',
        'setParameter[ForeFireDataDirectory=.]',
        f'loadData[{LANDSCAPE_FILE};{date}]']

    for line in init_data:
        forefire.sendline(line)

    current_time = date

def callback(ch, method, properties, body):
    msg = body.decode()
    print(msg)
    if msg.startswith('INIT'):
        parameters = msg.split(' ')[1:]
        if len(parameters) != 4:
            return
        left = float(parameters[0])
        right = float(parameters[1])
        top = float(parameters[2])
        bottom = float(parameters[3])
        init(left, right, top, bottom)
    elif msg.startswith('METAR'):
        parameters = msg.split(' ')[1:]
        if len(parameters) != 4:
            return
        airport = parameters[0]
        heading = int(parameters[1])
        speed = int(parameters[2])
        unit = parameters[3]
        process_metar(airport, heading, speed, unit)
    elif msg.startswith('START'):
        parameters = msg.split(' ')[1:]
        if len(parameters) != 1:
            return
        date = parameters[0]
        finish_init(date)
    elif msg.startswith('FIRE'):
        parameters = msg.split(' ')[1:]
        if len(parameters) != 3:
            return
        lat = parameters[0]
        lon = parameters[1]
        t = parameters[2]
        fire(lat, lon, t)
    elif msg.startswith('STEP'):
        step()
        pass
    elif msg.startswith('END'):
        pass

signal.signal(signal.SIGALRM, prepare_wind_map)

channel.basic_consume(queue='ForeFireRecv', on_message_callback=callback, auto_ack=True)

channel.start_consuming()