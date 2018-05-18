#!/usr/bin/env python
from threading import Lock
from flask import Flask, render_template, session, request,jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room, \
    close_room, rooms, disconnect
from flask.json import JSONEncoder

import uuid
import eventlet


# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None

class MiniJSONEncoder(JSONEncoder):
    """Minify JSON output."""
    item_separator = ','
    key_separator = ':'
app = Flask(__name__)
app.threaded=True
#app.json_encoder = MiniJSONEncoder
#app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app,message_queue='redis://127.0.0.1')
eventlet.monkey_patch()

thread = None
thread_lock = Lock()


clientsByUsername = {}
clientsBySid = {}

@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)



@socketio.on('return_response')
def return_response(message):
	username = clientsBySid[request.sid]["username"]
	responses = clientsByUsername[username]["responses"]
	responses[message["uuid"]] = message["result"]

@app.route('/api/<username>/<name>',  methods=['GET', 'POST','PUT','DELETE','PATCH','HEAD', 'CONNECT', 'TRACE', 'OPTIONS'])
def remote_api(username, name):
	request_uuid = str(uuid.uuid4())

	if not (username in clientsByUsername):
		return jsonify({"error":"user not exit"})

	responses = clientsByUsername[username]["responses"]
	responses[request_uuid] = None;
	
	param ={ \
	"name":name,\
	"method": request.method, \
	"args":request.args,\
	"form": request.form,\
	"json": request.json,
	"uuid":request_uuid\
	}
	namespace=clientsByUsername[username]["namespace"]
	
	socketio.emit('exec_script', param , namespace=namespace)
	print (namespace,request_uuid , "wait")

	while responses[request_uuid] == None:
		socketio.sleep(1)

	print ("strar jsonify")
	req = jsonify(responses[request_uuid])
	print ("end jsonify")
	del responses[request_uuid]
	return   req

@app.route('/mapi/<namespace>/<name>',  methods=['GET', 'POST','PUT','DELETE','PATCH','HEAD', 'CONNECT', 'TRACE', 'OPTIONS'])
def remote_api_multiple(namespace,name):
	request_uuid = "M|"+str(uuid.uuid4())
	
	param ={ \
	"name":name,\
	"method": request.method, \
	"args": request.args,\
	"form": request.form,\
	"json": request.json,
	"uuid": request_uuid\
	}
	clients = {k:x for k,x in clientsByUsername.iteritems() if x["namespace"] == "/"+namespace}
	
	if len (clients)<=0:
		return jsonify({"error":"namespace empty"})
	
	for key in clients:
		client=clientsByUsername[key]
		client["responses"][request_uuid]=None 
	
	socketio.emit('exec_script', param , namespace="/"+namespace)
	print (request_uuid , "wait")

	flag = True

	ret = {}

	while flag:
		for key in clients:
			client=clientsByUsername[key]
			flag=False
			if client["responses"][request_uuid] == None:
				flag = True
				break
			else:
				if not (key in ret):
					ret[key] = (client["responses"][request_uuid])
		socketio.sleep(1)
	for key in clients:
		client=clientsByUsername[key]
		del client["responses"][request_uuid] 
	
	req = jsonify(ret)
	return   req


@socketio.on('connect')
def connect():
	if not(request.args["username"] in clientsByUsername):
		clientsByUsername[request.args["username"]] = {"responses":{},"sid":request.sid, "namespace": request.args["namespace"]}
		clientsBySid[request.sid] = {"username":request.args["username"]}
		join_room(request.sid)
	else:
		return False
		


@socketio.on('disconnect')
def disconnect():
	if request.sid in clientsBySid:
		username = clientsBySid[request.sid]["username"]
		del clientsBySid[request.sid]
		if username in clientsByUsername:
			del clientsByUsername[username]
	

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000,debug=False)

#uwsgi --socket 127.0.0.1:8000 --wsgi-file app.py --callable app --processes 4 --threads 2 --stats 127.0.0.1:9191
#  gunicorn --worker-class eventlet -w 3 app:app



