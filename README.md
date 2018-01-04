# Multipeer Connectivity for Pythonista

This is a [Pythonista](http://omz-software.com/pythonista/) wrapper around iOS [Multipeer Connectivity](https://developer.apple.com/documentation/multipeerconnectivity?language=objc).

Multipeer connectivity allows you to find and exchange information between 2-8 devices in the same network neighborhood (same wifi or bluetooth), without going through some server.

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

It is functional, even though the prompts and incoming messages tend to get mixed up. You can also run the `multipeer.py` file to try out a cleaner Pythonista UI version of the chat.

Here are the things to note when starting to use this library:
  
## Peer-to-peer, not client-server

This wrapper around the MC framework makes no assumptions regarding the relationships between peers. If you need client-server roles, you can build them on top.

## Expected usage

1. Create a subclass of `MultipeerCommunications` to handle messages from the framework (see separate topic, below).
2. Instantiate the subclass with your service type and peer display name (see the class description).
3. Wait for peers to connect (see the `peer_added` and `get_peers` methods).
4. Optionally, have each participating peer stop accepting further peers, e.g. for the duration of a game (see the `stop_looking_for_peers` method).
5. Send and receive messages (see a separate topic, below).
6. Potentially react to additions and removal of peers.
7. Optionally, start accepting peers again, e.g. after a previous game ends (see the `start_looking_for_peers` method).
8. Before your app exits, call the `end_all` method to make sure there are no lingering connections.

## What's in a message?

Messages passed between peers are UTF-8 encoded text. This wrapper JSON-serializes the message you give to the `send` method (probably a str or a dict), then encodes it in bytes. Receiving peers reconstitute the message and pass it to the `receive` callback.

## What is a peer ID?

Peer IDs passed around by the wrapper have a `display_name` member that gives you the display name of that peer. There is no guarantee that these names are unique between peers.

The IDs act also as identifier objects for specific peers, and can be used to `send` messages to individual peers.

You cannot create peer IDs for remote peers manually.

## Why do I need to subclass?

This wrapper chooses to handle callbacks via subclassing rather than requiring a separate delegate class. Subclass should define the following methods; see the API for the method signatures:
  
* `peer_added`
* `peer_removed`
* `receive`

The versions of these methods in the `MultipeerConnectivity` class just print out the information received.

## Additional details

* This implementation uses automatic invite of all peers (until you call `stop_looking_for_peers`). Future version may include a callback for making decisions on which peers to accept.
* Related to the previous point, including discovery info while browsing for peers is not currently supported.
* Also, there is no way to explicitly kick a specific peer out of a session. This seems to be a limitation of the Apple framework.
* Following defaults are used and are not currently configurable without resorting to ObjC:
  * Secure - Encryption is required on all connections.
  * Not secure - A specific security identity cannot be set.
  * Reliable - When sending data to other peers, framework tries to guarantee delivery of each message, enqueueing and retransmitting data as needed, and ensuring in-order delivery.

# API

* [Class: MultipeerConnectivity](#class-multipeerconnectivity)
  * [Methods](#methods)


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

#### `start_looking_for_peers(self)`

  Start conmecting to available peers. 

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

  Disconnects from the multipeer session and removes internal references.
  Further communications will require instantiating a new MultipeerCommunications (sub)class. 
