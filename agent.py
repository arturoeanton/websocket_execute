#!/usr/bin/env python
from flask import Flask, jsonify, request
from flask_socketio import SocketIO, join_room, leave_room

from redis import Redis
from redis_semaphore import Semaphore
from threading import Thread
import argparse
import eventlet


import pika
import sys
import json 
import redis
import random
import signal
import os



parser = argparse.ArgumentParser()
parser.add_argument( 	'--host',			dest='host', 		help='host   		[0.0.0.0]', 			default="0.0.0.0",)
parser.add_argument('-p', '--port',			dest='port', 		help='port   		[5001]', 	type=int, 	default=5001,)
parser.add_argument('-e', '--exchange',		dest='exchange', 	help='exchange  	[topic1]', 				default="topic1",)
parser.add_argument('-mq','--rabbitmq',		dest='host_mq', 	help='host rabbit  	[localhost]', 			default="localhost",)
parser.add_argument('-r', '--routing',		dest='routing', 	help='routing key 	[client1]', 			default="client1",)
args = parser.parse_args()
semaphore = Semaphore(Redis(), count=1, namespace='sem1')
semaphore_con = Semaphore(Redis(), count=1, namespace='sem_con')


app = Flask(__name__)
app.threaded=True
io = SocketIO(app)
pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
eventlet.monkey_patch()
consumers = {}


@io.on('return_response')
def return_response(message):
	r = redis.Redis(connection_pool=pool)
	r.rpush(message["uuid"], json.dumps(message["result"]))


@io.on('disconnect')
def disconnect():
	leave_room(request.sid)
	count =  -1;
	routing=request.args["client"]
	print "disconnect " + routing
	if routing in  consumers:
		consumers[routing]["count"] -=  1
	print "status of " + routing + ": " + str(consumers[routing]["count"])


	return True

@io.on('connect')
def connect():
	join_room(request.sid)

	routing=request.args["client"]
	print "Connect " + routing
	if not routing in  consumers:
		thread = Thread(target = rabbitmq_wait, args=(args.host_mq, args.exchange, routing) )
		thread.setDaemon(True)
		thread.start()
		consumers[routing] = {"count":1, "thread": thread}
	else:
		consumers[routing]["count"] +=  1
	print "status of " + routing + ": " + str(consumers[routing]["count"] )

	return True

@io.on('return_exist')
def return_exist(msg):
	with semaphore:
		r = redis.Redis(connection_pool=pool)
		json_response = r.get("response-"+msg["uuid"])
		r.delete("response-"+msg["uuid"])
		if json_response != None and  msg["exist"]:
			response = json.loads(json_response)
			r.rpush("status-"+msg["uuid"], '{"status": "exist"}') # confirm to orche that script exist 
			io.emit('exec_script', response["param"], namespace=response["namespace"], room= request.sid)
			print(" [x] Execute Script %r" % ( response["param"]["script"], ))


def callback(ch, method, properties, body):
	data = json.loads(body)
	namespace = "/"+data["client"]
	r = redis.Redis(connection_pool=pool)
	json_response=json.dumps({"param": data, "namespace":namespace})
	r.set("response-"+data["uuid"], json_response)
	io.emit('exist_script', {"script": data["script"], "uuid": data["uuid"]},  namespace=namespace )
	print ("[.] exist script? " + namespace)





def rabbitmq_wait(host_mq,exchange,routing_key,):
	connection = pika.BlockingConnection(pika.ConnectionParameters(host=host_mq))
	channel = connection.channel()
	channel.exchange_declare(exchange=exchange,exchange_type='topic')
	result = channel.queue_declare(exclusive=True)
	queue_name = result.method.queue
	channel.queue_bind(exchange=exchange,queue=queue_name,routing_key=routing_key)
	print(' [*] Waiting for logs. To exit press CTRL+C')
	channel.basic_consume(callback, queue=queue_name, no_ack=True)
	try:
		channel.start_consuming()
	except pika.exceptions.ChannelClosed:
		print " [e] reconect to rabbit"
		rabbitmq_wait(host_mq,exchange,routing_key,)



if "__main__" == __name__:
	io.run(app, host='0.0.0.0', port=args.port,debug=False)
	#io.run(app, host=args.host, port=args.port,debug=False)