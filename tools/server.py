from conversion_tools import prepare_landscape
import pika
import pexpect
from select import select

LANDSCAPE_FILE = 'fsx.nc'

connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

channel.queue_declare(queue='hello')

forefire = None

def init(left, right, top, bottom, projection, date):
    global forefire
    if forefire is not None and not forefire.terminated:
        return
    prepare_landscape(
        left,
        right,
        top,
        bottom,
        projection,
        LANDSCAPE_FILE)
    
    forefire = pexpect.spawn('../CommandShell', echo=False)
    forefire.readline() # greeting lines
    forefire.readline() # greeting lines

    init_data = [f'setParameter[projection={projection}]',
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

def fire(x, y, t):
    if forefire is None or forefire.terminated:
        return
    forefire.sendline(f'startFire[loc=({x},{y},{t});t=0]')

def step(dt):
    if forefire is None or forefire.terminated:
        return
    forefire.sendline(f'step[dt={dt}]')
    forefire.sendline('print[]')
    while True:
        try:
            forefire.expect('\r\n', timeout=0.1)
        except pexpect.exceptions.TIMEOUT:
            break
        print(forefire.before)
    
def callback(ch, method, properties, body):
    msg = body.decode('utf-8')
    print(msg)
    if msg.startswith('INIT'):
        parameters = msg.split(' ')[1:]
        if len(parameters) != 6:
            return
        left = float(parameters[0])
        right = float(parameters[1])
        top = float(parameters[2])
        bottom = float(parameters[3])
        projection = parameters[4]
        date = parameters[5]
        init(left, right, top, bottom, projection, date)
    elif msg.startswith('FIRE'):
        parameters = msg.split(' ')[1:]
        if len(parameters) != 3:
            return
        x = parameters[0]
        y = parameters[1]
        t = parameters[2]
        fire(x, y, t)
    elif msg.startswith('STEP'):
        parameters = msg.split(' ')[1:]
        if len(parameters) != 1:
            return
        dt = parameters[0]
        step(dt)

channel.basic_consume(queue='hello', on_message_callback=callback, auto_ack=True)

channel.start_consuming()