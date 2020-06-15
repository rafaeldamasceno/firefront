#!/usr/bin/env python
import pika

credentials = pika.PlainCredentials('guest', 'guest')
connection = pika.BlockingConnection(pika.ConnectionParameters(host='127.0.0.1', credentials=credentials))
channel = connection.channel()

channel.basic_publish(exchange='ForeFire', routing_key='ForeFireRecv', body='INIT -86 -79 42 36 2020-03-20T12:00:00Z')
channel.basic_publish(exchange='ForeFire', routing_key='ForeFireRecv', body='FIRE -9261781.634000361 5116146.294557266 0')
for i in range(100):
    channel.basic_publish(exchange='ForeFire', routing_key='ForeFireRecv', body='STEP')

connection.close()