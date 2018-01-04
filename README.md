# Multipeer Connectivity for Pythonista

This is a Pythonista wrapper around iOS [Multipeer Connectivity](https://developer.apple.com/documentation/multipeerconnectivity?language=objc).

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

# API

* [Class: _block_descriptor](#class-block-descriptor)
* [Class: block_literal](#class-block-literal)
* [Class: MultipeerConnectivity](#class-multipeerconnectivity)
  * [Methods](#methods)
* [Functions](#functions)


## Class: _block_descriptor

## Class: block_literal

## Class: MultipeerConnectivity

Multipeer communications. Subclass this class to define how you want to react to added or removed peers, and to process incoming messages from peers.

Constructor:
  
    mc = MultipeerConnectivity(display_name='Peer', service_type='dev-srv')

Arguments:
  
* `display_name` - This peer's display name (e.g. a player name).
* `service_type` - String that must match with that of the peers in order for a connection to be established. Must be 1-15 characters in length and contain only a-z, 0-9, or '-'.

Created object will immediately start advertising and browsing for peers.

## Methods


#### `peer_added(self, peerID)`

  Override handling of new peers in a subclass. 

#### `peer_removed(self, peerID)`

  Override handling of lost peers in a subclass. 

#### `get_peers(self)`

  Get a list of peers currently connected. 

#### `stop_looking_for_peers(self)`

  Stop advertising for new connections, e.g. when you have all the players and start a game, and do not want new players joining in the middle. 

#### `send(self, message, to_peer=None)`

  Send a message to some or all peers.
  
  * `message` - to be sent to the peer(s). Must be JSON-serializable.
  * `to_peer` - receiver peer IDs. Can be a single peer ID, a list of peer IDs, or left out (None) for sending to all connected peers.

#### `receive(self, message, from_peer)`

  Override in a subclass to handle incoming messages. 

#### `disconnect(self)`

  End your games or similar sessions by calling this method. 

#### `end_all(self)`

# Functions


#### `session_peer_didChangeState_(_self,_cmd,_session,_peerID,_state)`


#### `session_didReceiveData_fromPeer_(_self,_cmd,_session,_data,_peerID)`


#### `session_didReceiveStream_withName_fromPeer_(_self,_cmd,_session,_stream,_streamName,_peerID)`


#### `browser_didNotStartBrowsingForPeers_(_self,_cmd,_browser,_err)`


#### `browser_foundPeer_withDiscoveryInfo_(_self, _cmd, _browser, _peerID, _info)`


#### `browser_lostPeer_(_self, _cmd, browser, peer)`


#### `advertiser_didReceiveInvitationFromPeer_withContext_invitationHandler_(_self,_cmd,advertiser,peerID,context,invitationHandler)`

