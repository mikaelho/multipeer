#coding: utf-8
from objc_util import *

import ctypes, re, time

NSBundle.bundle(Path="/System/Library/Frameworks/MultipeerConnectivity.framework").load()
MCPeerID = ObjCClass('MCPeerID')
MCSession = ObjCClass('MCSession')
MCNearbyServiceAdvertiser = ObjCClass('MCNearbyServiceAdvertiser')
MCNearbyServiceBrowser = ObjCClass('MCNearbyServiceBrowser')

class _block_descriptor (Structure):
  _fields_ = [
    ('reserved', c_ulong), ('size', c_ulong), ('copy_helper', c_void_p), ('dispose_helper', c_void_p), ('signature', c_char_p)
  ]

InvokeFuncType = ctypes.CFUNCTYPE(None, *[c_void_p,ctypes.c_bool,c_void_p])

class block_literal(Structure):
  _fields_ = [
    ('isa', c_void_p), ('flags', c_int), ('reserved', c_int), ('invoke', InvokeFuncType), ('descriptor', _block_descriptor)
  ]

class MultipeerConnectivity():

  myID = None
  service_name = 'dev-srv'

  def __init__(self, display_name='Peer', service_name=None):
    if service_name is not None:
      if len(service_name) < 1 or len(service_name) > 15: raise ValueError('service_name must be 1-15 characters long')
      check_re = re.compile(r'[^a-z0-9\-.]')
      check_str = check_re.search(service_name)
      if bool(check_str): raise ValueError('service_name can contain only ASCII lowercase letters, numbers and hyphens')
      self.service_name = service_name
    self.myID = MCPeerID.alloc().initWithDisplayName(display_name)

    def session_peer_didChangeState_(_self, _cmd, _session, _peerID, _state):
      print('session change',self.service_name, _peerID,_session,_state)

    def session_didReceiveData_fromPeer_(_self, _cmd, _session, _data, _peerID):
      print('Received Data',_data)

    def session_didReceiveStream_withName_fromPeer_(_self, _cmd, _session, _stream, _streamName, _peerID):
      print('Received Stream....',_streamName)

    SessionDelegate = create_objc_class('SessionDelegate',methods=[
      session_peer_didChangeState_, session_didReceiveData_fromPeer_, session_didReceiveStream_withName_fromPeer_
    ],protocols=['MCSessionDelegate'])
    session_delegate = SessionDelegate.alloc().init()

    self.session = MCSession.alloc().initWithPeer_(self.myID)
    self.session.setDelegate_(session_delegate)

class MultipeerAdvertiser(MultipeerConnectivity):

  def ready_to_provide_service(self):
    def advertiser_didReceiveInvitationFromPeer_withContext_invitationHandler_(_self, _cmd, advertiser, peerID, context, invitationHandler):
      print('invitation')
      blk = block_literal.from_address(invitationHandler)
      blk.invoke(ObjCInstance(invitationHandler), True, ObjCInstance(self.session))

    f =  advertiser_didReceiveInvitationFromPeer_withContext_invitationHandler_
    f.argtypes = [c_void_p]*4
    f.restype = None
    f.encoding = b'v@:@@@@?'
    # also, try f.encoding=b'v@:@@@@'
    AdvertiserDelegate = create_objc_class('AdvertiserDelegate', methods=[
      advertiser_didReceiveInvitationFromPeer_withContext_invitationHandler_
    ])
    advertiser_delegate = AdvertiserDelegate.alloc().init()

    self.advertiser = MCNearbyServiceAdvertiser.alloc().initWithPeer_discoveryInfo_serviceType_(self.myID, None, self.service_name)

  def no_more_accepted(self):
    self.advertiser.stopAdvertisingPeer()

class MultipeerBrowser(MultipeerConnectivity):

  def start_finding_peers(self):
    def browser_didNotStartBrowsingForPeers_(_self,_cmd,_browser,_err):
      print('ERROR!!!')

    def browser_foundPeer_withDiscoveryInfo_(_self, _cmd, _browser, _peerID, _info):
      print('found peer')
      peerID = ObjCInstance(_peerID)
      self.browser.invitePeer_toSession_withContext_timeout_(peerID, self.session, None, 0)

      print('#',peerID,ObjCInstance(_info))

    def browser_lostPeer_(_self, _cmd, browser, peer):
      print('lost peer')

    BrowserDelegate = create_objc_class('BrowserDelegate',methods=[
      browser_foundPeer_withDiscoveryInfo_, browser_lostPeer_, browser_didNotStartBrowsingForPeers_
    ],protocols=['MCNearbyServiceBrowserDelegate'])
    browser_delegate = BrowserDelegate.alloc().init()

    self.browser = MCNearbyServiceBrowser.alloc().initWithPeer_serviceType_(self.myID, self.service_name)
    self.browser.setDelegate_(browser_delegate)
    self.browser.startBrowsingForPeers()

  def stop_finding_peers(self):
    self.browser.stopBrowsingForPeers()

  def join_session(self, game_id):
    pass

  def get_participants(self, game_id):
    pass

  def send_to(self, recipient_id, msg, verify=False):
    pass

  def broadcast(self, msg, verify=False):
    pass

  def set_message_callback(self, callback, verify=False):
    pass

  def set_new_id(self, display_name):
    self.myID = MCPeerID.alloc().initWithDisplayName(display_name)


if __name__ == '__main__':
  s = MultipeerAdvertiser(display_name='Server')
  print(s.myID)
  c = MultipeerBrowser(display_name='Client')
  print(c.myID)

  s.ready_to_provide_service()
  c.start_finding_peers()

  try:
    while True:
      time.sleep(0.1)
  except KeyboardInterrupt:
    print('Close...')
    c.stop_finding_peers()
    s.no_more_accepted()
  except:
    raise

