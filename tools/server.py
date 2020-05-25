from conversion_tools import prepare_landscape
import pika
from subprocess import Popen, PIPE, STDOUT

LANDSCAPE_FILE = 'fsx.nc'

connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

channel.queue_declare(queue='hello')

forefire = None

def init(msg):
    global forefire
    if forefire is not None:
        return
    parameters = msg.split(' ')[1:]
    if len(parameters) != 6:
        return
    prepare_landscape(
        float(parameters[0]),
        float(parameters[1]),
        float(parameters[2]),
        float(parameters[3]),
        parameters[4],
        LANDSCAPE_FILE)
    forefire = Popen(['../CommandShell'], stdout=PIPE, stdin=PIPE, stderr=STDOUT)
    print(forefire.communicate(input=f'setParameter[projection={parameters[4]}]\n'.encode('utf-8')))
    


def callback(ch, method, properties, body):
    msg = body.decode('utf-8')
    print(msg)
    if msg.startswith('INIT'):
        init(msg)

channel.basic_consume(queue='hello', on_message_callback=callback, auto_ack=True)

channel.start_consuming()