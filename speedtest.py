import ui
#from .BaseDelegate import BaseDelegate
import multipeer
import objc_util
import console
from objc_util import *
from timeit import default_timer as timer

UIDevice = ObjCClass('UIDevice')

class c64Peer(multipeer.MultipeerConnectivity):
	pingcount=0
	durchschnitt=0
	def __init__(self, parent):
		dn=UIDevice.currentDevice().name()
		super().__init__(service_type='speedtest',display_name=str(dn), initialize_streams=True)
		self.parent = parent
		self.parent.log('>peer created:'+str(dn))
				
	def peer_added(self, peer):
		self.parent.log('>peer added:'+peer.display_name)
		console.hud_alert('>peer added:'+peer.display_name)
		
		peercount=len(self.get_peers())
		self.parent.view['labelConnections'].text = 'connections: '+str( peercount)
		self.parent.view['btn_ping'].enabled = peercount > 0
		
	def peer_removed(self, peer):
		self.parent.log('>peer removed:'+peer.display_name)
		console.hud_alert('>peer removed:'+peer.display_name)

		peercount=len(self.get_peers())
		self.parent.view['labelConnections'].text = 'connections: '+str( peercount)
		self.parent.view['btn_ping'].enabled = peercount > 0
				
		
	def receive(self, message, from_peer):
		msg = from_peer.display_name + ': ' + message['cmd']
		self.parent.writein('received>'+msg)
		
		cmd = message['cmd']
		if cmd == 'ping':
			self.send({'cmd': 'reping'}, reliable=self.parent.reliablemode)
		elif cmd == 'reping':
			echoTime=self.parent.view['echoTime']
			pingend = timer()
			time_in_ms=1000*(pingend-self.parent.pingstart)
			echoTime.text= str(time_in_ms) + 'ms'
			self.durchschnitt +=time_in_ms
			print(echoTime.text)
			if self.pingcount == 0:				
				self.parent.pingstart=None
				echoTime.text= str(self.durchschnitt/1000) + 'ms durchschnitt'
				self.durchschnitt=0
			else:
				self.parent.pingstart=timer()
				self.send({'cmd': 'ping'}, reliable=self.parent.reliablemode)			
				self.pingcount -= 1;
		else:
			self.parent.deleg(cmd,notify=False)

	def stream_receive(self, byte_data, peer_id):
		cmd=byte_data.decode()
		#msg = peer_id + ': ' + cmd
		#self.parent.writein('streamreceived>'+msg)
		if cmd == 'ping':
			packet = ('reping').encode()
			self.stream(packet, peer_id) #send back to sending peer
		elif cmd == 'reping':
			echoTime=self.parent.view['echoTime']
			pingend = timer()
			time_in_ms=1000*(pingend-self.parent.pingstart)
			echoTime.text= str(time_in_ms) + 'ms'
			self.durchschnitt +=time_in_ms
			print(echoTime.text+' stream')
			if self.pingcount == 0:				
				self.parent.pingstart=None
				echoTime.text= str(self.durchschnitt/1000) + 'ms durchschnitt'
				self.durchschnitt=0
			else:
				self.parent.pingstart=timer()
				packet = ('ping').encode()
				self.stream(packet, peer_id) #send back to sending peer
				self.pingcount -= 1;
		else:
			self.parent.deleg(cmd,notify=False)		


class Multiplayer:
	mc=None
	pingstart=None
	reliablemode=True
	def __init__(self):
		
		self.view = ui.load_view('speedtest')
		self.view.name = 'speedtest'
		self.view.present(hide_title_bar=True)
		self.view['btn_ping'].enabled= False
		

	def becomes_visible(self):
		pass
		
	def willClose(self):
		if self.mc != None:
			self.mc.end_all()
			self.mc = None
			print('multi ends all')

	@ui.in_background
	def btn_ping(self,sender):
		if self.mc != None and self.pingstart==None:
			echoTime=self.view['echoTime']
			echoTime.text='wait'
			self.pingstart = timer()
			if self.view['useStreams'].value:
				print('stream ping')
				self.mc.pingcount=1000
				self.mc.stream('ping'.encode())
			else:
				print('send ping')
				self.mc.pingcount=1000
				self.mc.send({'cmd': 'ping'}, reliable=self.reliablemode)
			
	@ui.in_background
	def setReliable(self,sender):
		self.reliablemode = sender.value
	
	@ui.in_background
	def enableout(self,sender):
		if sender.value:
			if self.mc == None:
				self.mc = c64Peer(parent=self)
		else:
				self.writeout('>peer closed...')
				if self.mc != None:
					self.mc.end_all()
					self.mc = None
		
	def log(self, msg):
		t=self.view['outview']['textview']
		t.text = t.text +' ' + msg +'\n'

	def logright(self, msg):
		t=self.view['inview']['textview']
		t.text = t.text +' ' + msg +'\n'
				
	def writeout(self, sCmd):
		#t=self.view['outview']['textview']
		#t.text = t.text +' ' + sCmd +'\n'
		
		if self.view['sendout'].value:
			if self.mc != None:
				if self.view['useStreams'].value:
					self.mc.stream(sCmd.encode())
				else:		
					message = {'cmd': sCmd}
					self.mc.send(message, reliable=self.reliablemode)
		
	def writein(self, sCmd):
		#t=self.view['inview']['textview']
		#t.text = t.text +' ' + sCmd +'\n'
		pass

if __name__ == '__main__':
	mc=Multiplayer()
