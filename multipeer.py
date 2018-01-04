# -*- coding: utf-8 -*-

'''
# Multipeer Connectivity for Pythonista

This is a [Pythonista](http://omz-software.com/pythonista/) wrapper around iOS [Multipeer Connectivity](https://developer.apple.com/documentation/multipeerconnectivity?language=objc).

Multipeer connectivity allows you to find and exchange information with devices in the same network neighborhood (same wifi or bluetooth), without going through some server.

Here's a minimal usage example, a line-based chat:

    import multipeer

    my_name = input('Name: ')
    
    mc = multipeer.MultipeerConnectivity(display_name=my_name, service_type='chat')
    
    try:
      while True:
        chat_message = input('Message: ')
        mc.send(chat_message)
    finally:
      mc.end_all()

It is functional, even though the prompts and incoming messages tend to get messily mixed up. You can also run the `multipeer.py` file to try out a cleaner Pythonista UI version of the chat.

Here are the things to note when starting to use this library:
peertopeer
message
expected flow
subclass
peer ID

# Details
Autoinvite
Defaults: Secure, reliable, transient
Some memory leaking
Discovery info ignored
No way to kick anyone out
'''

from objc_util import *
import ctypes, re, json

NSBundle.bundle(Path="/System/Library/Frameworks/MultipeerConnectivity.framework").load()
MCPeerID=ObjCClass('MCPeerID')
MCSession=ObjCClass('MCSession')
MCNearbyServiceAdvertiser=ObjCClass('MCNearbyServiceAdvertiser')
MCNearbyServiceBrowser=ObjCClass('MCNearbyServiceBrowser')

# Global variable and a helper function for accessing Python manager object from ObjC functions.
# Dictionary is used to support running more than one MC object simultaneously.

mc_managers = {}

def _get_self(manager_object):
  ''' Expects a 'manager object', i.e. one of session, advertiser or browser, and uses the contained peer ID to locate the right Python manager object. '''
  global mc_managers
  return mc_managers[ObjCInstance(manager_object).myPeerID().hash()]

def session_peer_didChangeState_(_self,_cmd,_session,_peerID,_state):
  peerID = ObjCInstance(_peerID)
  peerID.display_name = str(peerID.displayName())
  self = _get_self(_session)
  #print('session change',peerID,_state)
  if _state == 2:
    self.peer_added(peerID)
  if _state is None:
    self.peer_removed(peerID)

def session_didReceiveData_fromPeer_(_self,_cmd,_session,_data,_peerID):
  self = _get_self(_session)
  peerID = ObjCInstance(_peerID)
  peerID.display_name = str(peerID.displayName())
  decoded_data = nsdata_to_bytes(ObjCInstance(_data)).decode()
  #print('Received data:',decoded_data)
  message = json.loads(decoded_data)
  self.receive(message, peerID)

def session_didReceiveStream_withName_fromPeer_(_self,_cmd,_session,_stream,_streamName,_peerID):
  print('Received stream', _streamName, 'but streams are not currently supported by this API')

try:
  SDelegate = SessionDelegate.alloc().init()
except:
  SessionDelegate = create_objc_class('SessionDelegate',methods=[session_peer_didChangeState_, session_didReceiveData_fromPeer_, session_didReceiveStream_withName_fromPeer_],protocols=['MCSessionDelegate'])
  SDelegate = SessionDelegate.alloc().init()

def browser_didNotStartBrowsingForPeers_(_self,_cmd,_browser,_err):
  print ('ERROR!!!')

def browser_foundPeer_withDiscoveryInfo_(_self, _cmd, _browser, _peerID, _info):
  self = _get_self(_browser)

  peerID = ObjCInstance(_peerID)
  browser = ObjCInstance(_browser)
  browser.invitePeer_toSession_withContext_timeout_(peerID,self.session,None,0)
  #mySession.connectPeer_withNearbyConnectionData_(peerID,None)
  #print('#',peerID,ObjCInstance(_info))

def browser_lostPeer_(_self, _cmd, browser, peer):
  #print ('lost peer')
  pass

try:
  Bdelegate = BrowserDelegate.alloc().init()
except:
  BrowserDelegate = create_objc_class('BrowserDelegate',methods=[browser_foundPeer_withDiscoveryInfo_, browser_lostPeer_, browser_didNotStartBrowsingForPeers_],protocols=['MCNearbyServiceBrowserDelegate'])
  Bdelegate = BrowserDelegate.alloc().init()

class _block_descriptor (Structure):
  _fields_ = [('reserved', c_ulong), ('size', c_ulong), ('copy_helper', c_void_p), ('dispose_helper', c_void_p), ('signature', c_char_p)]
InvokeFuncType = ctypes.CFUNCTYPE(None, *[c_void_p,ctypes.c_bool,c_void_p])
class block_literal(Structure):
  _fields_ = [('isa', c_void_p), ('flags', c_int), ('reserved', c_int), ('invoke', InvokeFuncType), ('descriptor', _block_descriptor)]

# Advertiser Delegate
def advertiser_didReceiveInvitationFromPeer_withContext_invitationHandler_(_self,_cmd,advertiser,peerID,context,invitationHandler):
  self = _get_self(advertiser)
  invitation_handler = ObjCInstance(invitationHandler)
  retain_global(invitation_handler)
  blk=block_literal.from_address(invitationHandler)
  blk.invoke(invitation_handler,True, self.session)

try:
  ADelegate = AdvertiserDelegate.alloc().init()
except:
  f= advertiser_didReceiveInvitationFromPeer_withContext_invitationHandler_
  f.argtypes = [c_void_p]*4
  f.restype = None
  f.encoding = b'v@:@@@@?'
  AdvertiserDelegate = create_objc_class('AdvertiserDelegate',methods=[advertiser_didReceiveInvitationFromPeer_withContext_invitationHandler_])
  ADelegate = AdvertiserDelegate.alloc().init()


class MultipeerConnectivity():
  ''' Multipeer communications. Subclass this class to define how you want to react to added or removed peers, and to process incoming messages from peers.
  
  Constructor:
    
      mc = MultipeerConnectivity(display_name='Peer', service_type='dev-srv')
  
  Arguments:
    
  * `display_name` - This peer's display name (e.g. a player name).
  * `service_type` - String that must match with that of the peers in order for a connection to be established. Must be 1-15 characters in length and contain only a-z, 0-9, or '-'.
  
  Created object will immediately start advertising and browsing for peers.
  '''

  def __init__(self, display_name='Peer', service_type='dev-srv'):
    global mc_managers

    self.service_type = service_type
    check_re = re.compile(r'[^a-z0-9\-.]')
    check_str = check_re.search(self.service_type)
    if len(self.service_type) < 1 or len(self.service_type) > 15 or bool(check_str):
      raise ValueError('service_type must be 1-15 characters long and can contain only ASCII lowercase letters, numbers and hyphens')

    self.my_id = MCPeerID.alloc().initWithDisplayName(display_name)
    self.my_id.display_name = str(self.my_id.displayName())

    mc_managers[self.my_id.hash()] = self

    self.session = MCSession.alloc().initWithPeer_(self.my_id)
    self.session.setDelegate_(SDelegate)

    #print('my ID',self.my_id)

    self.browser = MCNearbyServiceBrowser.alloc().initWithPeer_serviceType_(self.my_id, self.service_type)
    self.browser.setDelegate_(Bdelegate)
    self.browser.startBrowsingForPeers()

    # Create Server and set delegate
    self.advertiser = MCNearbyServiceAdvertiser.alloc().initWithPeer_discoveryInfo_serviceType_(self.my_id, ns({}), self.service_type)
    self.advertiser.setDelegate_(ADelegate)

    # Start Server
    self.advertiser.startAdvertisingPeer()
    #print('Server start, ID is : ',self.my_id)

  def peer_added(self, peerID):
    ''' Override handling of new peers in a subclass. '''
    print('Added peer', peerID.display_name)

  def peer_removed(self, peerID):
    ''' Override handling of lost peers in a subclass. '''
    print('Removed peer', peerID.display_name)

  def get_peers(self):
    ''' Get a list of peers currently connected. '''
    peer_list = []
    for peer in self.session.connectedPeers():
      peer.display_name = str(peer.displayName())
      peer_list.append(peer)
    return peer_list

  def stop_looking_for_peers(self):
    ''' Stop advertising for new connections, e.g. when you have all the players and start a game, and do not want new players joining in the middle. '''
    self.advertiser.stopAdvertisingPeer()
    self.browser.stopBrowsingForPeers()

  def send(self, message, to_peer=None):
    ''' Send a message to some or all peers.

    * `message` - to be sent to the peer(s). Must be JSON-serializable.
    * `to_peer` - receiver peer IDs. Can be a single peer ID, a list of peer IDs, or left out (None) for sending to all connected peers.
    '''
    if type(to_peer) == list:
      peers = to_peer
    elif to_peer is None:
      peers = self.get_peers()
    else:
      peers = [to_peer]
    self.session.sendData_toPeers_withMode_error_(json.dumps(message).encode(), peers, 0, None)

  def receive(self, message, from_peer):
    ''' Override in a subclass to handle incoming messages. '''
    print('Message from', from_peer.display_name, '-' , message)

  def disconnect(self):
    ''' End your games or similar sessions by calling this method. '''
    self.session.disconnect()

  def end_all(self):
    self.stop_looking_for_peers()
    self.disconnect()

if __name__ == '__main__':

  import ui
  
  class ChatPeer(MultipeerConnectivity):
    
    def peer_added(self, peer):
      peer_list = self.get_peers()
      as_text = 'Chatting with:\n' +  '\n'.join([peer.display_name for peer in peer_list])
      peers.text = as_text
      
    def peer_removed(self, peer):
      self.peer_added(peer)
      
    def receive(self, message, from_peer):
      msg = from_peer.display_name + ': ' + message['text'] + ' (#' + str(message['count']) + ')\n'
      received_messages.text += msg
  
  class ChatView(ui.View):
    
    def __init__(self, **kwargs):
      super().__init__(**kwargs)
      self.message_count = 0
    
    def start_chat(self, sender):
      chat_name = name_field.text
      if len(chat_name) > 0:
        sender.touch_enabled = False
        name_field.end_editing()
        name_field.editable = False
        message_entry.touch_enabled = True
        send_button.touch_enabled = True
        peers.text = 'Looking for peers'
        
        self.mc = ChatPeer(service_type='chat-demo', display_name=chat_name)
        
    def send_message(self, sender):
      self.message_count += 1
      message = {
        'text': message_entry.text,
        'count': self.message_count
      }
      self.mc.send(message)
      self.mc.receive(message, self.mc.my_id)
      message_entry.text = ''
      
    def will_close(self):
      self.mc.end_all()
  
  chat = ChatView(background_color=(.8, .92, 1.0))
  chat.present()
  
  (w,h) = chat.width, chat.height
  
  name_field = ui.TextField(placeholder='Your display name', frame=(20,20,w-80, 40), flex='W')
  go_button = ui.Button(title='Go', frame=(0.9*w,20,80,80), flex='W', background_color='grey', tint_color='white')
  name_field.action = go_button.action = chat.start_chat
  
  peers = ui.TextView(text='Enter your name first', editable=False, frame=(20, 80, w-40, 80), flex='WH')
  
  message_entry = ui.TextField(placeholder='Your message', frame=(20,180,w-80,40), flex='W', touch_enabled=False)
  send_button = ui.Button(title='Send', frame=(w-60,80,40,40), flex='W', background_color='grey', tint_color='white', touch_enabled=False)
  message_entry.action = send_button.action = chat.send_message
  
  received_messages = ui.TextView(editable=False, frame=(20,240,w-40,h-260), flex='WH')
  
  chat.add_subview(name_field)
  chat.add_subview(go_button)
  chat.add_subview(peers)
  chat.add_subview(message_entry)
  chat.add_subview(send_button)
  chat.add_subview(received_messages)
  go_button.frame=(w-60,20,40,40)
  send_button.frame=(w-60,180,40,40)
