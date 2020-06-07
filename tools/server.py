from conversion_tools import prepare_landscape, convert_polygon
from datetime import datetime
import json
import pika
import pexpect
from select import select
import ssl
import time
import threading

LANDSCAPE_FILE = 'fsx.nc'
PROJECTION = 'EPSG:3857'
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

channel.queue_declare(queue='ForeFireRecv')
channel.exchange_declare('ForeFire')
channel.queue_bind('ForeFireRecv', 'ForeFire', routing_key='ForeFireRecv')

forefire = None

current_time = None

def init(left, right, top, bottom, date):
    global forefire, current_time
    if forefire is not None and not forefire.terminated:
        return
    prepare_landscape(
        left,
        right,
        top,
        bottom,
        PROJECTION,
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

def fire(x, y, t):
    if forefire is None or forefire.terminated:
        return
    forefire.sendline(f'startFire[loc=({x},{y},{t});t=0]')

def step():
    global current_time
    if forefire is None or forefire.terminated:
        return
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
            threading.Thread(target=convert_polygon, args=(result))
            # print(result)
            if result['fronts'][0]['date'] > current_time:
                current_time = result['fronts'][0]['date']
        except pexpect.exceptions.TIMEOUT:
            continue

    
def callback(ch, method, properties, body):
    msg = body.decode()
    print(msg)
    previous_time = current_time
    start_timer = time.perf_counter()
    if msg.startswith('INIT'):
        parameters = msg.split(' ')[1:]
        if len(parameters) != 5:
            return
        left = float(parameters[0])
        right = float(parameters[1])
        top = float(parameters[2])
        bottom = float(parameters[3])
        date = parameters[4]
        init(left, right, top, bottom, date)
    elif msg.startswith('FIRE'):
        parameters = msg.split(' ')[1:]
        if len(parameters) != 3:
            return
        x = parameters[0]
        y = parameters[1]
        t = parameters[2]
        fire(x, y, t)
    elif msg.startswith('STEP'):
        step()
    elif msg.startswith('END'):
        pass
    end_timer = time.perf_counter()
    if previous_time is not None:
        time_difference = (datetime.strptime(current_time, TIME_FORMAT) - datetime.strptime(previous_time, TIME_FORMAT)).total_seconds()
        print(time_difference, end_timer - start_timer, time_difference / (end_timer - start_timer))


channel.basic_consume(queue='ForeFireRecv', on_message_callback=callback, auto_ack=True)

channel.start_consuming()