import sys 
data=[]
#100000000

_name = None
if "name" in json:
	_name =  json["name"]

if 'name' in globals():
	_name = name


tope = int(10000) 
for i in range(0, tope):
	sys.stdout.write("i  %d : %d%%   \r" % (i, ((i*100)/tope)) )
	sys.stdout.flush()
	data.append(i)


result = {"saludo":"hola " + _name, "data" : data, "method": method}
print("termine")
