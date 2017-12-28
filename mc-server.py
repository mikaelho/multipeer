# -*- coding: utf-8 -*-

from objc_util import *
import ctypes,time,os

NSBundle.bundle(Path="/System/Library/Frameworks/MultipeerConnectivity.framework").load()
MCPeerID=ObjCClass('MCPeerID')
MCSession=ObjCClass('MCSession')
MCNearbyServiceAdvertiser=ObjCClass('MCNearbyServiceAdvertiser')
MCNearbyServiceBrowser=ObjCClass('MCNearbyServiceBrowser')

# Session Delegate
def session_peer_didChangeState_(_self,_cmd,_session,_peerID,_state):
  print('session change',_peerID,_session,_state)

def session_didReceiveData_fromPeer_(_self,_cmd,_session,_data,_peerID):
  print('Received Data',_data)

def session_didReceiveStream_withName_fromPeer_(_self,_cmd,_session,_stream,_streamName,_peerID):
  print('Received Stream....',_streamName)

try:
  SDelegate = SessionDelegate.alloc().init()
except:
  SessionDelegate = create_objc_class('SessionDelegate',methods=[session_peer_didChangeState_, session_didReceiveData_fromPeer_, session_didReceiveStream_withName_fromPeer_],protocols=['MCSessionDelegate'])
  SDelegate = SessionDelegate.alloc().init()

class _block_descriptor (Structure):
   _fields_ = [('reserved', c_ulong), ('size', c_ulong), ('copy_helper', c_void_p), ('dispose_helper', c_void_p), ('signature', c_char_p)]
InvokeFuncType = ctypes.CFUNCTYPE(None, *[c_void_p,ctypes.c_bool,c_void_p])
class block_literal(Structure):
    _fields_ = [('isa', c_void_p), ('flags', c_int), ('reserved', c_int), ('invoke', InvokeFuncType), ('descriptor', _block_descriptor)]

# Advertiser Delegate
def advertiser_didReceiveInvitationFromPeer_withContext_invitationHandler_(_self,_cmd,advertiser,peerID,context,invitationHandler):
  print('invitation',peerID)
  blk=block_literal.from_address(invitationHandler)
  blk.invoke(ObjCInstance(invitationHandler),True, ObjCInstance(mySession))
  
try:
  ADelegate = AdvertiserDelegate.alloc().init()
except:
  f= advertiser_didReceiveInvitationFromPeer_withContext_invitationHandler_
  f.argtypes  =[c_void_p]*4
  f.restype = None
  f.encoding=b'v@:@@@@?'
  # also, try f.encoding=b'v@:@@@@'
  AdvertiserDelegate = create_objc_class('AdvertiserDelegate',methods=[advertiser_didReceiveInvitationFromPeer_withContext_invitationHandler_])
  ADelegate = AdvertiserDelegate.alloc().init()


# init PeerID
myID = MCPeerID.alloc().initWithDisplayName('wolf_srv')
# init Session and delegate
mySession = MCSession.alloc().initWithPeer_(myID)
mySession.setDelegate_(SDelegate)


'''
    Server
'''
# Create Server and set delegate
aSrv = MCNearbyServiceAdvertiser.alloc().initWithPeer_discoveryInfo_serviceType_(myID,ns({'player.name':'apple'}),'audio-srv1')
aSrv.setDelegate_(ADelegate)

# Start Server
aSrv.startAdvertisingPeer()
print('Server start, ID is : ',myID)

try:
  while 1:
    time.sleep(0.1)
except KeyboardInterrupt:
  print('Server Stop...')
  aSrv.stopAdvertisingPeer()
  mySession.disconnect()
except:
  raise


