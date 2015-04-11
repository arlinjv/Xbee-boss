"""
To do:
- implement following columns: connected (to mesh), devices (foreign key) (consider polling devices only)
- update arduino code to return device names (what to do with dumb nodes?)
"""
import sqlite3 as lite
import sys #not sure if this is necessary

test_nodes = [{'node_identifier': 'DEVICE B', 'parent_address': '\xff\xfe', 'addr': '-\xb3', 'addr_long': '\x00\x13\xa2\x00@\x8bH\x8e'}, 
	{'node_identifier': 'DEVICEA', 'parent_address': '\xff\xfe', 'addr': 'K\x0f', 'addr_long': '\x00\x13\xa2\x00@\xac\xb5\x14'}]

tn = test_nodes

def new_node_table():
		
	con = lite.connect('xbee.db')
	
	with con:
		
		con.text_factory = str #sqlite would prefer I use unicode
		cur = con.cursor()
		
		cur.execute("""
			CREATE TABLE IF NOT EXISTS Nodes(addr_long TEXT UNIQUE, addr TEXT, node_identifier TEXT, 
			parent_address TEXT, status TEXT, description TEXT DEFAULT "No description", 
			time_stamp DATETIME DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(addr_long));""")		
			# status attribute can be active, inactive, deleted(?). set to active when entered into table or updated
		
		cur.execute("""create trigger update_node_time after update on Nodes
						begin
							update nodes set time_stamp = datetime('now') where  rowid = old.rowid;
						end; """) # update time stamp whenever a row is updated
		
		# 

		
		con.commit()
		
		print "Nodes table created"
		
def update_nodes_table(nodes):
	# take a list of nodes and check for other nodes that haven't been updated. those nodes will be updated to 'inactive status'
	# not sure if this should be done on regular basis. maybe implement only for maintenance (via gui or command line) 
	# or maybe call when certain errors occur (like expected message not arriving)
	pass

def update_node_old(node, _status = "active", _description = "No description"):
	
	vals = (node['addr_long'].encode('hex'), node['addr'].encode('hex'), node['node_identifier'], node['parent_address'].encode('hex'), _status, _description)
	addr_long, addr, node_identifier, parent_address, status, description = vals #unpack list. convenient to use vals intermediary because of 'if vals[0:5] == r[0:5]:' below
	# status is "active" above assuming that that is the current state. if not it will be updated.
	
	con = lite.connect('xbee.db')
	
	with con:
		
		con.text_factory = str #sqlite would prefer I use unicode
		cur = con.cursor()
		
		print "checking DB... ", 
		
		#check to see if Nodes table exists
		cur.execute("select count(*) from sqlite_master where type = 'table' and name = 'Nodes';")
		if cur.fetchone()[0] == 0: #should return 1 if table exists
			print "Nodes table did not exist. Creating now"
			new_node_table()			
		
		try: #try making a new entry
			cur.execute("INSERT INTO Nodes(addr_long, addr, node_identifier, parent_address, status, description) VALUES(?, ?, ?, ?, ?, ?)", 
						(addr_long, addr, node_identifier, parent_address, status, description))
			print "New node inserted"
		
		except lite.IntegrityError, e: #node already exists. e gives 'column addr_long is not unique'
					# update node with any new vals ('addr' is most likely to change. also checking status)
			cur.execute("select * from Nodes where addr_long = ?", (addr_long,)) # find the matching row
			r= cur.fetchone()

			if vals[0:6] == r[0:6]: #checking only attributes affected during node discovery (Plus whether status and description changed, but not timestamp)
				print "Row unchanged"
			else:
				sql = "update Nodes set addr = ?, node_identifier = ?, parent_address = ?, status = ?, description = ? where addr_long = ?"
				cur.execute (sql, (addr, node_identifier, parent_address, status, description, addr_long) ) 
				print cur.rowcount, " row(s) updated"			
		
		con.commit()

def update_node(node, status = 'active', description = None):
	#node (xbee code and db) format: 'addr_long', 'addr', 'parent_address', 'node_identifier'
	#additional attributes (db): status, description, time stamp
	#update_node() called upon receipt of ND, rx and other api responses. (status defaults to active because update is only called after msgs received from active nodes)
	"""	
	To do:
	- Consider adapting for non-ND cases. rx and rx_explicit msgs will not have parent_address and node_identifier data
	- Implement change log 	via trigger - http://www.tutorialspoint.com/sqlite/sqlite_triggers.htm
	- timestamp not getting updated when values change - decide if this is what I want
	"""
	
	vals = {'addr_long':node['addr_long'].encode('hex'), 'addr':node['addr'].encode('hex'), 'node_identifier':node['node_identifier'],
	 'parent_address':node['parent_address'].encode('hex'), 'status':status, 'description':description} # these are the attributes that will get updated

	
	con = lite.connect('xbee.db')
	
	with con:
		
		con.text_factory = str #sqlite would prefer I use unicode
		con.row_factory = lite.Row #row is now returned as a dict-like row object
		cur = con.cursor()
		
		print "checking DB... ", 
		
		#check to see if Nodes table exists
		cur.execute("select count(*) from sqlite_master where type = 'table' and name = 'Nodes';")
		if cur.fetchone()[0] == 0: #should return 1 if table exists
			print "Nodes table did not exist. Creating now"
			new_node_table()			
		
		try: #try making a new entry
			cur.execute("INSERT INTO Nodes(addr_long, addr, node_identifier, parent_address, status, description) VALUES(?, ?, ?, ?, ?, ?)", 
						(vals['addr_long'], vals['addr'], vals['node_identifier'], vals['parent_address'], status, description))
			print "New node inserted"
		
		except lite.IntegrityError, e: #node already exists. e gives 'column addr_long is not unique'
					# update node with any new vals ('addr' is most likely to change. also checking status)
			
			cur.execute("select * from Nodes where addr_long = ?", (vals['addr_long'],)) # find the matching row
			r= cur.fetchone()
			
			if description == None: #prevent node description from getting overwritten
				vals['description'] = r['description'] 
			
			keys = r.keys()
			keys.remove('addr_long') #addr_long is the primary key so no point updating that
			
			for key in keys:
				if key in vals.keys(): # check for changes first (saves about 6-7 milliseconds if no changes)
					if vals[key] != r[key]:
						cur.execute("UPDATE Nodes SET '%s' = ? WHERE addr_long = ?;" % key,	(vals[key], vals['addr_long']))
						print key, " set to ",vals[key],". ",
		print " Update complete"	
		
		con.commit()
		

def list_nodes():
	pass #list nodes in db		

def new_device_table(): #probably should have called this new_devices_table()
	# create a new Devices table 
	con = lite.connect('xbee.db')
	
	with con:

		con.text_factory = str #sqlite would prefer I use unicode
		cur = con.cursor()
		
		cur.execute("""
			CREATE TABLE IF NOT EXISTS Devices(device_id TEXT NOT NULL, parent_node TEXT NOT NULL, nickname TEXT, parent_id TEXT, 
			poll TEXT, poll_interval INTEGER, alarm TEXT, alarm_action TEXT, last_val REAL, logging TEXT,
			FOREIGN KEY(parent_node) REFERENCES nodes(addr_long), PRIMARY KEY(device_id, parent_node) );
		""") #device_id = device name. parent_node is long addr of parent. Poll, alarm, logging = 'True'/'False'
		
		# create change log for devices. no primary key or foreign key necessary as all entries will be copies of rows from devices table
		cur.execute("""
			CREATE TABLE IF NOT EXISTS Devices_log(device_id TEXT NOT NULL, parent_node TEXT NOT NULL, nickname TEXT, parent_id TEXT, 
			poll TEXT, poll_interval INTEGER, last_val REAL, logging TEXT, time_stamp DATETIME DEFAULT CURRENT_TIMESTAMP); """) 
			
		#create trigger to insert row in devices_log whenever last_val updated
		cur.execute("""
			CREATE TRIGGER IF NOT EXISTS log_device_vals AFTER UPDATE of last_val on Devices 
				BEGIN
				INSERT INTO Devices_log (device_id, parent_node, nickname, parent_id, last_val, logging) VALUES (old.device_id, old.parent_node, old.nickname, old.parent_id, old.last_val, old.logging);
				END;""")
				# to do implement changes on logging and only when logging = 'true'
			
		# consider implementing trigger log_device_changes to catch all changes
		
		con.commit()
		print "Devices table created"

def new_device(device_id, parent_node): 
	#This only creates the device. must call update to add parameters
	# It appears to take approximately 1 to 2 milliseconds
	# call as such: xbeeDB.new_device(device_id = device, parent_node = last_data['source_addr_long'].encode('hex'))
	
	con = lite.connect('xbee.db')
	
	with con:

		con.text_factory = str #sqlite would prefer I use unicode
		con.row_factory = lite.Row #row is now returned as a dict-like row object
		cur = con.cursor()
		
		con.execute("pragma foreign_keys = on") #this will cause exception if parent_node does not exist in table
		
		#check for Devices table. make if not there
		cur.execute("select count(*) from sqlite_master where type = 'table' and name = 'Devices';")
		if cur.fetchone()[0] == 0: #should return 1 if table exists
			print "Devices table did not exist. Creating now"  # There seems to be a bug here as this message prints each time devices list is received
			new_device_table()	
			
		# identify node_identifier of parent node
		cur.execute("select * from Nodes where addr_long = ?", 	(parent_node,))
		parent = cur.fetchone()
		parent_id = parent['node_identifier']
		#print "node_identifier of parent node of new device is ", parent_id
		
		try: #create new device if doesn't exist, otherwise raise exception
			sql = "INSERT INTO Devices(device_id, parent_node, parent_id) values(?,?,?)"
			cur.execute(sql, (device_id, parent_node, parent_id) )
			print "New device - ", device_id," - created for node with addr_long: ", parent_node
		
		except lite.IntegrityError, e: # e will return 'columns device_id, parent_node are not unique
			if "foreign key constraint failed" in e:
				print "parent node - ", parent_node, " - does not exist in nodes table"
				raise Exception("parent node does not exist in nodes table")
				con.close()
				return
			elif "columns device_id, parent_node are not unique" in e:
				print "Device named ", device_id, " already exists for node ",parent_node
				print "---- sqlite integrity error: ", e, 
				raise Exception("Device already exists")
				con.close()
				return
			else:
				print "some sqlite error occurred: ", e
				con.close()
				return
		
		
		con.commit()
			
	# Add code here to also add additional attributes from arguments list.
	# maybe just call update_device() and pass in kwargs?
	# call con.close() first?
			

def update_device(device_id, parent_node, **kwargs):
	"""
		valid keywords: poll, poll_interval, logging, parent_id, nickname
		device_id = device name. parent_node is long addr of parent. Poll, alarm, logging = 'True'/'False'
	"""
	# Appears to take 6 to 10 milliseconds
	# To do: consider enabling logging based on keyword in rf_data
	
	con = lite.connect('xbee.db')
	
	with con:

		con.text_factory = str #sqlite would prefer I use unicode
		con.row_factory = lite.Row #row is now returned as a tuple-like row object
		cur = con.cursor()	
			
		cur.execute("select * from Devices where parent_node = ? and device_id = ?", (parent_node,device_id)) # find the matching row
		
		l= cur.fetchall() #if device exists it should return a list of length 1
		if len(l) == 0:
			raise Exception("Device does not exist")
			return	# replace with call to new_device()
		
		for key in kwargs.keys():
			if key in l[0].keys(): # if key from keywords matches an attribute in the selected row
				cur.execute("UPDATE Devices SET '%s' = ? WHERE parent_node = ? AND device_id = ?;" % key, (kwargs[key], parent_node, device_id) ) 
				# for some reason couldn't use ? before equal sign so resorted to '%s'				
				print key, " set to ",kwargs[key],". ",
		print			
			
		con.commit()

def delete_device(device_id, parent_node):
	pass #

def list_devices():
	# returns a dict containing current row for each device in table
	
	def dict_factory(cursor, row): 
		d = {}
		for idx, col in enumerate(cursor.description):
			d[col[0]] = row[idx]
		return d
	
	con = lite.connect('xbee.db')
	
	with con:

		con.text_factory = str #sqlite would prefer I use unicode
		con.row_factory = dict_factory #row is now returned as a dict
		cur = con.cursor()
		
		try:
			cur.execute("select * from Devices") # raises an error if devices table not created yet.
			l= cur.fetchall()
			return l
		
		except lite.OperationalError, e: #adding this to address problem of starting up with no xbee.db file existing.
			#if "no such table" in e: #seems like this should work but since it doesn't commenting out - works for now
				print e
				new_device_table()
				empty_dict = {}
				return empty_dict # return {} doesn't work
		
	
def list_alarms():
	# in XbeeBoss when message comes in from device check against this list
	pass	

def cleanup_devices():
	# delete all orphaned devices 
	# this would be needed if a node is ever deleted.
	# might also want to implement when inactive (smart) node first reenters network (followed by list_devices msg.)
	#this whole subroutine might be unnecessary if
	# - nodes are never deleted (entirely likely as there won't be that many and id's are unique)
	# - every time a node reenters network coordinator sends a 'devices' query and updates devices (missing devices would be deleted)
	pass 

def new_sys_msg_log():
	pass

def new_sys_msg(): #for system messages like rx_explicit
	pass

def connectDB(): # for interactive mode testing.
				#should move connection and cursor objects outside and pass in
	global con
	con = lite.connect('xbee.db')
	con.text_factory = str #sqlite would prefer I use unicode
	con.row_factory = lite.Row
	global cur
	cur = con.cursor()
		
"""
See sqlite diary for more info

helpful websites:
- sqlite interactive shell tutorial (lists dot commands): http://www.sqlite.org/sqlite.html 
- good overall tutorial: http://pymotw.com/2/sqlite3/ 
"""
