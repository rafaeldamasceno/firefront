#!/usr/bin/env python
import pika

connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

channel.queue_declare(queue='hello')

channel.basic_publish(exchange='', routing_key='hello', body='INIT -86 -79 42 36 EPSG:3857 2020-03-20T12:00:00Z')
channel.basic_publish(exchange='', routing_key='hello', body='FIRE -9261781.634000361 5116146.294557266 0')
channel.basic_publish(exchange='', routing_key='hello', body='STEP 1200')

connection.close()