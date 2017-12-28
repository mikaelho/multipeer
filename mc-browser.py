
# -*- coding: utf-8 -*-

from objc_util import *
import ctypes,time,os

cnt = 0

NSBundle.bundle(Path="/System/Library/Frameworks/MultipeerConnectivity.framework").load()
MCPeerID=ObjCClass('MCPeerID')
MCSession=ObjCClass('MCSession')
MCNearbyServiceAdvertiser=ObjCClass('MCNearbyServiceAdvertiser')
MCNearbyServiceBrowser=ObjCClass('MCNearbyServiceBrowser')

def session_peer_didChangeState_(_self,_cmd,_session,_peerID,_state):
    print('session change',ObjCInstance(_peerID),_state)

def session_didReceiveData_fromPeer_(_self,_cmd,_session,_data,_peerID):
    print('Received Data',_data)

def session_didReceiveStream_withName_fromPeer_(_self,_cmd,_session,_stream,_streamName,_peerID):
    print('Received Stream....',_streamName) 
    
SessionDelegate = create_objc_class('SessionDelegate',methods=[session_peer_didChangeState_, session_didReceiveData_fromPeer_, session_didReceiveStream_withName_fromPeer_],protocols=['MCSessionDelegate'])
SDelegate = SessionDelegate.alloc().init()

def browser_didNotStartBrowsingForPeers_(_self,_cmd,_browser,_err):
    print ('ERROR!!!')

def browser_foundPeer_withDiscoveryInfo_(_self, _cmd, _browser, _peerID, _info):
    global aBr,mySession
    
    peerID = ObjCInstance(_peerID)
    aBr.invitePeer_toSession_withContext_timeout_(peerID,mySession,None,0)
    #mySession.connectPeer_withNearbyConnectionData_(peerID,None)
    print('#',peerID,ObjCInstance(_info))
    
def browser_lostPeer_(_self, _cmd, browser, peer):
    print ('lost peer')

BrowserDelegate = create_objc_class('BrowserDelegate',methods=[browser_foundPeer_withDiscoveryInfo_, browser_lostPeer_, browser_didNotStartBrowsingForPeers_],protocols=['MCNearbyServiceBrowserDelegate'])
Bdelegate = BrowserDelegate.alloc().init()

myID = MCPeerID.alloc().initWithDisplayName('wolf_client')
mySession = MCSession.alloc().initWithPeer_(myID)
mySession.setDelegate_(SDelegate)

print('my ID',myID)
aBr = MCNearbyServiceBrowser.alloc().initWithPeer_serviceType_(myID,'audio-srv1')
aBr.setDelegate_(Bdelegate)
aBr.startBrowsingForPeers()

try:
    while 1:
        time.sleep(0.1)
except KeyboardInterrupt:
    print('Close...')
    aBr.stopBrowsingForPeers()  
except:            
    raise

