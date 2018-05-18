from socketIO_client import SocketIO, BaseNamespace
import argparse
import json
import time
from datetime import date
import os.path



class WSNamespace(BaseNamespace):
    def on_connect(self):
        print('[Connected]')
    def on_reconnect(self):
        print('[Reconnected]')

    def on_disconnect(self):
        print('[Disconnected]')

def exist_script(args):
	name = args["script"]
	uuid = args["uuid"]
	if os.path.isfile('scripts/'+name+'.py'):
		socketIO.emit('return_exist', {"exist":True, "uuid":uuid})

def exec_script(args):	
	code = ''
	name = args["script"]
	uuid = args["uuid"]
	global_var= dict()
	global_var["result"] = None;

	global_var["method"] = args["method"];
	
	if args["json"]:
		global_var["json"] = args["json"]
	else:
		global_var["json"] = {}
	global_var.update(args["args"])
	global_var.update(args["form"])
	with open('scripts/'+name+'.py', 'r') as myfile:
		code=myfile.read()
	print (uuid , name, global_var,"start exec")
	try:
		exec(code, global_var)
		ret = {"uuid":uuid,  "result": global_var['result']}
	except:
		print "error"
		ret = {"uuid":uuid,  "result": "error"}
	print (uuid , "ok")
	socketIO.emit('return_response', ret)
	return  ret



parser = argparse.ArgumentParser()
parser.add_argument('-d','--host',			dest='host', 		help='host destination  [127.0.0.1]', default="127.0.0.1",)
parser.add_argument('-p','--port',			dest='port', 		help='port destination  [5000]', type=int, default=5000,)
parser.add_argument('--proxies',			dest='proxies', 	help='proxies connection "{}"',  type=json.loads,  default={})
parser.add_argument('-c','--client',		dest='client', 		help='client name  client1',  	default="client1",)

args = parser.parse_args()

print args
socketIO = SocketIO(args.host, args.port, WSNamespace, 
	proxies = args.proxies,
	params  = {'client': args.client }
	)

ws_namespace = socketIO.define(WSNamespace, '/'+args.client)
root = socketIO.define(WSNamespace, '')
ws_namespace.on('exec_script',exec_script)
ws_namespace.on('exist_script',exist_script)

while True:
	socketIO.wait(seconds=20)

