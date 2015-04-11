"""# coding: utf-8"""
# above line required when script written in gedit

#The purpose of this script is to process and print out all data coming in to the 
#attached coordinator xbee in api mode. 
# This script is intended to be run with interactive mode from a terminal: python -i XbeeBoss.py
# python-xbee package installed at /usr/local/lib/python2.7/dist-packages/xbee

# First git commit done on 2/22/2015

import threading
import subprocess
import multiprocessing
from configobj import ConfigObj
from datetime import datetime
import json
import serial
from serial.tools import list_ports
import time
import sys
from xbee import XBee,ZigBee
import pprint
import xbeeDB
# import threads # moving thread functions to separate module kept leading to global name errors

#setup --------------------------------------------

last_data = {} # gets value in print_data()
last_rx_node = {'addr_long':None,'addr':None, 'node_identifier':None}
nodes = [] # will become list of node dicts ( {'node_identifier', 'addr', 'addr_long', 'parent_address'} )
BC_LONG = '\x00\x00\x00\x00\x00\x00\xFF\xFF' #broadcast long addr. bc short addr is usually set as default

config = ConfigObj('config.ini', encoding = 'UTF8')

connectDB = config['connectDB'] # check the config.ini file to see if db should be connected to or not

minimum_poll_interval = 5

# end setup ---------------------------------------
	

def help():
	print "Sample commands:"
	print "xbee.send(\"remote_at\", dest_addr_long=nodes[0]['addr_long'],dest_addr=nodes[0]['addr'], command = 'AI',frame_id='A')"
	print "xbee.at(command='MY')"
	print "msg(msg_data = 'test', node = nodes[0])"
	
	
def node_discovery():
	global nodes
	nodes = [] #clear out existing nodes list
	""" have to clear the list or get redundant entries each time function is called.
		consider implementing code to check for duplicates. """
	xbee.send("at",frame_id='1',command='ND') #nodes list will be filled in the receive data function when the replies come in
	# frame id of '1' is reserved for ND
nd = node_discovery #shorthand

def status():
	"""
	Launch thread that will wait for response to status request (i.e. if seeking status of coordinator send xbee.at(command='MY') should 
	result in return message starting with {'command': 'MY', ... and 'status':\x00'. A result of 0 is good because that represents the 
	16 bit address of the coordinator. use remote_at to do same for all known nodes - replies should contain 16 bit addresses for those nodes
	be sure that threads have timeouts built in
	Then call actual commands that will receive the results of status requests
	"""
	pass
	
def reply(reply_msg = None): #only works if last_data contained 'rf_data'
	if (last_rx_node.get('addr_long') != None):
		source_addr_long = last_rx_node['addr_long']
		source_addr = last_rx_node['addr'] # might need to tighten this up
		xbee.send("tx", dest_addr_long = source_addr_long, dest_addr = source_addr, data = reply_msg)
	else:
		print "no messages received yet this session"
		return
				

def msg(msg_data = None, node = None): #typical use will be to specify a node listed in the nodes list e.g. msg(nodes[1], 'hello')
	if node == None: #if no destination specified send broadcast
		node = {'addr_long':'\x00\x00\x00\x00\x00\x00\xFF\xFF','addr':'\xFF\xFE'}
	elif type(node) !=	dict:
		print "node parameter requires a dict containing 'addr_long' element"
		return	
	if 'addr_long' in node:
		addr_long = node['addr_long']
	else:
		print "no long address provided"
		return
	if 'addr' in node:
		addr = node['addr']
	else:
		addr = '\xFF\xFE'
	if msg_data == None:
		msg_data = str(datetime.now())
	
	xbee.send("tx", dest_addr_long = addr_long, dest_addr = addr, data = msg_data)
	
def rss():
	print "signal strength testing beginning ....."

	def RSS_scanner(nodes):
		time_limit = 5.0
		t = time.time()
		nodes.append({}) # need an extra dict for the coordinator response
		output = [] # fill with responses and print before closing
		
		while len(nodes) > 0:
			if last_data.get('command') == 'DB':
				for node in nodes:
					if node.get('addr_long') == last_data.get('source_addr_long'): #in case of coordinator None and None will match
						if node.get('addr_long') == None: #must be the coordinator
							# have to collect output strings, otherwise output gets interspersed with DB responses
							output.append("RSS for coordinator is %d (%s) " % (ord(last_data.get('parameter')), last_data.get('parameter')) )
						elif 'parameter' not in last_data:
							print "Remote command transmission failed for ", last_data.get('source_addr_long').encode('hex')
						else:
							try:
								output.append("RSS for %s is %d (%s)" % (last_data.get('source_addr_long').encode('hex'), ord(last_data.get('parameter')), last_data.get('parameter')) )
							except Exception, e:
								print "Error: ",e
								print "last_data:"
								print last_data
						i = nodes.index(node)
						del nodes[i]
			#time.sleep(.1) #even this apparently was too slow: missed responses. probably not necessary as timeout should ensure it doesn't bog
							#things down for too long.
			
			if time.time() - t > time_limit:
				print "RSS scanner timed out"
				break
		
		time.sleep(1) # give receive_data() time to finish printing out responses
		for s in output:
			print s	
	
	t = threading.Thread(target = RSS_scanner, args = (list(nodes),), name = 'RSS scanner') #list(nodes) creates a copy. otherwise nodes gets passed by reference and makes a mess
	t.start()
	
	xbee.at(command='DB')
	print "AT DB sent to coordinator"
	for i in range(0, len(nodes)):
		xbee.send("remote_at",dest_addr_long=nodes[i]['addr_long'],dest_addr=nodes[i]['addr'], command = 'DB',frame_id='A')
		print "remote_at DB sent to ", nodes[i]['addr_long'].encode('hex')

	
	

def populate_devices(node):
	pass
	# query node for its devices and put corresponding entries in db
	# call after doing node discovery
	
#  <<<<<<<<<<<<<<<<<<<<< Thread functions >>>>>>>>>>>>>>>>>>>>>>>
def list_threads():
	return threading.enumerate()

def initiate_keep_alive(): #keep nodes active by periodically issuing ND command
	
	def keep_alive():
		while True:
			print "keep alive"
			node_discovery()
			config.reload()
			keep_alive_interval = config.as_int('keep_alive_interval')
			if (keep_alive_interval <= 0 or keep_alive_interval == None):
				print "Invalid keep alive interval. stopping keep alive"
				return
			time.sleep(keep_alive_interval)
	
	t = threading.Thread(target= keep_alive, name = 'keep alive')
	t.start()
	
def stop_keep_alive():
	config['keep_alive_interval'] = '0'
	config.write()
	print 


def initiate_device_monitoring():
	# will launch a thread which will periodically check db for devices that are flagged for polling 
	# and then launch poller threads for each of those devices
	
	def find_match(device, old_list):
		match = {}
		for old_device in old_list:
			if old_device['parent_node'] == device['parent_node'] and old_device['device_id'] == device['device_id']:
				match = old_device
		return match
	
	def launch_poller(device): # called as target of device monitoring thread. launches additional polling device polling threads
		
		def poller(device): 
			
			# To do: check to see whether parent node is in network 
			
			time.sleep(1) #so output doesn't get garbled with thread calling code output
			print threading.current_thread()._Thread__name, " poller thread has been launched"
			
			device = find_match(device, xbeeDB.list_devices())
			next_poll_time = time.time() + device['poll_interval']
			
			while True: # send out msg to device to request reading at poll interval
				device_list = xbeeDB.list_devices()
				device = find_match(device, device_list)
				
				if device['poll'] != 'True': #exit from loop in order to let thread die
					break
					
				if int(device['poll_interval']) <= minimum_poll_interval: 
					raise Exception("poll_interval too short") # of course we shouldn't have gotten this far
					break
				
				if time.time() >= next_poll_time:
					print "polling ", device['device_id'], " (addr_long = ", device['parent_node'], ", time = ", time.time(), ")"
					#Send a message to node containing device we want to interrogate (e.g. thermo1).
					#Upon receiving the name of the device the Arduino code should send back a reading from that device
					msg(msg_data = str(device['device_id']), node = {'addr_long':device['parent_node'].decode('hex')})
					next_poll_time = time.time() + device['poll_interval']
				
				time.sleep(1) # give other processes and threads time to do their jobs
			
			# we've left the while loop so go ahead and exit
			print threading.current_thread()._Thread__name, " thread exiting"
			time.sleep(2) # give print statements time to complete
			
		t = threading.Thread(target = poller, args = (device,), name = device['device_id']) #To do: improve thread name
		t.start()
		print "device poller thread launched for ", device['device_id'], " (node = ", device['parent_node'],")"
			
	def monitor_devices(): # call this once as the target of a monitoring thread.
		# check for devices (new or otherwise) where polling equals true but didn't previously
		# To do: add code to allow this thread to be killed on command. as is it will run until program terminates
		
		old_list = xbeeDB.list_devices() #call this once so there is a valid list to compare against first time through while loop
		
		for device in old_list: 
			device['poll'] = '' # clear all poll settings so that they may be caught in the while loop below
			
		while True:
			new_list = xbeeDB.list_devices()
			for device in new_list: # check each device in current device list to see if its poll status changed from != true to == true.
									# and launch poller thread for each of those devices
				new_poll = False
				if device['poll'] != 'True': #no point in checking further if polling isn't set
					break
				if type(device['poll_interval']) != int or device['poll_interval'] < minimum_poll_interval:
					#print "invalid or too short poll interval" #need to figure clean way of just saying this once
					break
				old_device = find_match(device, old_list)
				#at this point we already know device['poll'] is true ...
				if old_device == {}: # find_match returns empty dict if no match found
					new_poll = True 
				elif old_device['poll'] != 'True': 
					new_poll = True
				
				if new_poll == True:
					launch_poller(device)
					time.sleep(3) # to help prevent pile-up of overlapping messages from poller threads
	
			old_list = new_list
			time.sleep(1) 
	
	t = threading.Thread(target = monitor_devices, name = 'device monitor')	
	t.start()
	
	if 'device monitor' in str(list_threads()):
		print 'device monitor thread launched'
	else:
		print 'device monitor thread failed to launch'
		
def initiate_polling():
	"""
	Alternate approach to managing device polling. Can be used for starting polling threads for individual devices regardless of polling state.
	sample code to be found in threads.py
	 - idea is to pass a global list of devices for polling. 
	 - devices can be killed by removing device from list
	"""
	pass

def refresh_config():
	pass
	#consider implementing as an alternative to having each function making repeated file reads to config file
	# launch a thread to update global variables from config file at set interval

# end thread functions

def enum_ports():
	#ports = serial.tools.list_ports.grep(r"\USB") # not sure how to use grep here. so doing long way:
	#following code was inspired by this post:
	#http://stackoverflow.com/questions/19809867/how-to-check-if-serial-port-is-already-open-by-another-process-in-linux-using
	ports = []	
	for port in serial.tools.list_ports.comports():
		if port[0].find('USB') >= 0: 
			#print port[0],
			ports.append(port[0])			
	return ports

def receive_data(data):
	"""
	python-xbee Documentation, Release 2.1.0
	This method is called whenever data is received
	from the associated XBee device. Its first and
	only argument is the data contained within the
	frame.
	"""
	t0 = time.time()
	global last_data
	last_data = dict.copy(data) #this makes data available from interactive shell
	
	pprint.pprint(data)
	
	if ('command' in data and data['command'] == 'ND'): 
		#data received is a result of a node discovery
		node = dict()
		parameters = data.get('parameter', {'node_identifier': None, 'source_addr': None, 'source_addr_long': None, 'parent_address': None}) 
		#dict after comma in .get() above is default value
		node['addr'] = parameters.get('source_addr')
		node['addr_long'] = parameters.get('source_addr_long')
		node['node_identifier'] = parameters.get('node_identifier')
		node['parent_address'] = parameters.get('parent_address')
		nodes.append(node) # no danger of duplicates because nodes is cleared when node_discovery() called
		print "Node added to nodes list. "
		
		global connectDB
		if connectDB == 'True':
			xbeeDB.update_node(node) # will add node to DB if new and ignore duplicates
			
		
	if 'id' in data and 'rx' in data['id']: # catches rx and rx_explicit msgs (e.g. when node rejoins, rf_data or io data recvd)
		global last_rx_node # for use in msg_reply()
		last_rx_node['addr'] = data.get('source_addr')
		last_rx_node['addr_long'] = data.get('source_addr_long')
		
		if 'rf_data' in data:
			try:
				rf = json.loads(data['rf_data']) #check for json formatted message
				
				if 'devices' in rf.keys(): # this could occur as a result of something like this: msg('devices')
										   # be aware that calling msg('devices') more than once will result in an error message
					devices = rf['devices'] #should return a list of strings with names of devices
					for device in devices: # add devices in list to devices table
						try:
							xbeeDB.new_device(device_id = device, parent_node = last_data['source_addr_long'].encode('hex'))
						except Exception, e:
							print device, " already exists in device table." #
							
				elif 'device' in rf.keys(): # must be elif because of overlap in key words ( device(s) )
					# typical rf_data from smart node would be like -  'rf_data': '{"device":"thermo1","msgtype":"poll","data":"21.37"}'
					
					if rf['msgtype'] == 'poll':
						# device monitor thread will capture any changes in data vals and launch a poller thread if polling enabled
						xbeeDB.update_device(device_id = rf['device'], parent_node = last_data['source_addr_long'].encode('hex'), last_val = rf['data'])
					
					if rf['msgtype'] == 'alarm':
						print "alarm message received"
						# replace this with something better. problem is each call will result in a new window
						# if using subprocess, maybe have a list of subprocesses opening each one as 'p = subprocess.Popen(args)'
						# then I can check the list and see if window already exists and kill it if desired
						subprocess.Popen(["python", "./alarms/Alarm_Window.py", "-d 4"], shell = False) # doing this appears to take between 3 and 6 millis
							
						
			except ValueError, e: # e == No JSON object could be decoded
				print "non json data received: ", e
				# rf_data from rx_explicits where node rejoins mesh can be caught here - use to update node list and db

		#To do: Implement the following catchers:
		# - io data
		# - alarm messages (implement in arduino code by setting msgtype = 'alarm')
		# currently trigger code in new_device_table catches all changes in data field. not sure if that will be optimal or not. 
	
	t1 = time.time()
	print t1 - t0
	print #blank line so display starts after >>> line
	

def main():
	
	#move this to a setup() routine and call that here?
	ports = enum_ports()
	
	try:
		global serial_port
		serial_port = serial.Serial(ports[0], 9600)
		# above assumes that first port found will be the right one.
		print "Connected to serial port: ", ports[0]
		print "--------------------------------------------"
	except:
		print "Serial Exception raised. The following ports were found:"
		print ports
		sys.exit()
	"""
	try: #keeping this in case I have trouble with multiple usb connections
		serial_port = serial.Serial("/dev/ttyUSB0", 9600)
	except serial.SerialException:
		print "Serial Exception raised. Try another port."
		ports = enum_ports()
		sys.exit()
	"""
	
	global xbee
	xbee = ZigBee(serial_port, callback=receive_data)

	print "Enter control-c to bring back interpreter prompt (>>>) after message is displayed"
	print "Enter control-z to exit script (send to bg) and get back to terminal prompt ($)"
	print "(type fg at terminal prompt to resume execution)"
	print
	
	node_discovery()
	initiate_device_monitoring()

if __name__ == '__main__':
    main()

