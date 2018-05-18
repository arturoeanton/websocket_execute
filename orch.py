#docker run -d --hostname my-rabbit --name my-rabbit -p 4369:4369 -p 5671:5671 -p 25672:25672 -p 5672:5672 rabbitmq
#docker run -d --hostname my-redis --name my-redis -p 6379:6379 redis

from flask import Flask,jsonify, request
import pika
import argparse
import json 
import uuid
import redis

parser = argparse.ArgumentParser()
parser.add_argument('-d','--host',			dest='host', 		help='host   		[0.0.0.0]', 			default="0.0.0.0",)
parser.add_argument('-p','--port',			dest='port', 		help='port   		[5000]', 	type=int, 	default=5000,)
parser.add_argument('-e','--exchange',		dest='exchange', 	help='exchange  	[topic1]', 				default="topic1",)
parser.add_argument('-mq','--rabbitmq',		dest='host_mq', 	help='host rabbit  	[localhost]', 			default="localhost",)
args = parser.parse_args()

app = Flask(__name__)
pool = redis.ConnectionPool(host='localhost', port=6379, db=0)

class Publisher:
	def __init__(self, host, exchange):
		self.host = host
		self.exchange = exchange
		self.channel = None
		self.connection = None
		self.connect()

	def connect(self):
		print(" [>] Connect %s exchange %s"% (self.host, self.exchange))
		self.connection = pika.BlockingConnection(pika.ConnectionParameters(self.host))
		self.channel = self.connection.channel()
		self.channel.exchange_declare(exchange=self.exchange, exchange_type='topic')
		self.channel = self.connection.channel()
		return self

	def send(self, client, message):
		try:
			self.channel.basic_publish(exchange=self.exchange, routing_key=client, body=json.dumps(message))
		except pika.exceptions.ConnectionClosed:
			self.connect()
			self.channel.basic_publish(exchange=self.exchange, routing_key=client, body=json.dumps(message))
		except pika.exceptions.ChannelClosed:
			self.connect()
			self.channel.basic_publish(exchange=self.exchange, routing_key=client, body=json.dumps(message))
		





@app.route('/api/<client>/<script>', defaults={'timeout': 200})
@app.route('/api/<client>/<script>/<int:timeout>')
def run(client, script, timeout):
	if timeout >= 600:
		print ("[e] timeout 200 not %d" % timeout)
		timeout = 200
	r = redis.Redis(connection_pool=pool)
	id_request = str(uuid.uuid4());
	message = { 
	'type': 'run',
	'client': client ,  
	'script': script , 
	'uuid': id_request,
	"method": request.method, 
	"args": request.args,
	"form": request.form,
	"json": request.json
	}
	publisher.send(client, message)
	data = r.blpop("status-"+id_request, 10)
	if data == None:
		print ("[e] script not found")
		return app.response_class( response='{"error":404, "description":"script not found"}', status=404, mimetype='application/json' )
	print ("[*] script found")
	print ("[t] timeout %d second" % (timeout,))
	data = r.blpop(id_request, timeout)
	if data == None:
		return app.response_class( response='{"error":408, "description":"timeout in step(2)"}', status=408, mimetype='application/json' )
	
	response = app.response_class(response=data[1],status=200, mimetype='application/json')
	return response

if "__main__" == __name__:
	publisher = Publisher(host=args.host_mq,exchange = args.exchange)
	app.run(host=args.host, port=args.port, debug=False, threaded=True)