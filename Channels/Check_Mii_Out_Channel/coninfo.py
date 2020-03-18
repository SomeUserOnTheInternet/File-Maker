from cmoc import ConInfo, Prepare
import MySQLdb
from json import load
from time import mktime
from datetime import datetime
from subprocess import call

with open("/var/rc24/File-Maker/Channels/Check_Mii_Out_Channel/config.json", "r") as f:
        config = load(f)
        
def setRankings(id): #once voting is concluded, rank miis from 1 to 10
	cursor.execute('SELECT entryno FROM conmiis WHERE contest = %s ORDER BY likes ASC', [id])
	miis = cursor.fetchall()
	miiCount = len(miis)
	for i in range(miiCount):
		percentile = round((i/10)/miiCount*90) + 1 #idk how this works, but it does
		cursor.execute('UPDATE conmiis SET `rank` = %s WHERE entryno = %s', (percentile, miis[i][0]))

currentTime = int(mktime(datetime.utcnow().timetuple())) - 946684800
db = MySQLdb.connect('localhost', config['dbuser'], config['dbpass'], 'cmoc', charset='utf8mb4')
cursor = db.cursor()
ci = ConInfo()
pr = Prepare()

cursor.execute('SELECT id, start, end, status, description FROM contests WHERE status != \'closed\'')
for con in cursor.fetchall():
	id = con[0]
	start = con[1]
	end = con[2]
	status = con[3]

	if status == 'waiting' and start <= currentTime and end >= currentTime: #contest is ready to be opened
		#print('waiting:', con[4])
		cursor.execute('UPDATE contests SET status = \'open\' WHERE id = %s', [id])

	elif start <= currentTime and end <= currentTime: #contest is ready to move to its next status
		endTime = int(end + (15 * 24 * 60 * 60)) #end time is increased by 15 days unless contest closes
		if status == 'open':
			#print('open:', con[4])
			cursor.execute('SELECT COUNT(*) FROM conmiis WHERE contest = %s', [id])
			cursor.execute('UPDATE contests SET status = \'judging\', end = %s, entrycount = %s WHERE id = %s', (endTime, cursor.fetchone()[0], id))

		elif status == 'judging': #run entrylist.py
			#print('judging:', con[4])
			call(["python", "/var/rc24/File-Maker/Channels/Check_Mii_Out_Channel/entrylist.py"])
			cursor.execute('UPDATE contests SET status = \'results\', end = %s WHERE id = %s', (endTime, id))
			setRankings(id)

		if status == 'results': #run bestlist.py
			#print('results:', con[4])
			call(["python", "/var/rc24/File-Maker/Channels/Check_Mii_Out_Channel/bestlist.py"])
			cursor.execute('UPDATE contests SET status = \'closed\' WHERE id = %s', [id])

	else:
		cursor.execute('SELECT COUNT(*) FROM conmiis WHERE contest = %s', [id])
		#print('nothing:', con[4])

db.commit()

cursor.execute('SELECT id, status FROM contests WHERE status != \'closed\' AND status != \'waiting\'')
contests = cursor.fetchall()

data = ci.build(contests)

with open('{}/150/con_info.ces'.format(config['miicontest_path']), 'wb') as file:
	file.write(pr.prepare(data))

with open('decfiles/con_info.dec', 'wb') as file:
	file.write(data)

db.close()

call(["python", "/var/rc24/File-Maker/Channels/Check_Mii_Out_Channel/condetail.py"])