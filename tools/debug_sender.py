#!/usr/bin/env python
import pika

connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

channel.queue_declare(queue='hello')

msg = input('Write message to be sent: ')
while msg:
    channel.basic_publish(exchange='', routing_key='hello', body=msg)
    msg = input('Write message to be sent: ')

connection.close()