# multipeer

Multipeer connectivity for the Pythonista iOS app

# Multipeer

This is a [Pythonista](http://omz-software.com/pythonista/) wrapper around iOS
[Multipeer Connectivity](https://developer.apple.com/documentation/multipeerconnectivity?language=objc).

Multipeer connectivity allows you to find and exchange information between
2-8 iOS and Mac devices in the same network neighborhood (same wifi or
bluetooth), without going through some server.

Sample use cases include games, chats, file exchange (like AirDrop) and so on.

## Installation

Copy the `multipeer.py` file from Github to your site-packages, or just:
  
    pip install pythonista-multipeer
    
in [Stash](https://github.com/ywangd/stash).

## Usage

Here's a minimal usage example, a line-based chat. You need to be running
the same code on all devices participating in the chat.

    import multipeer

    my_name = input('Name: ')

    mc = multipeer.MultipeerConnectivity(display_name=my_name,
      service_type='chat')

    try:
      while True:
        chat_message = input('Message: ')
        mc.send(chat_message)
    finally:
      mc.end_all()

This example is functional, even though the prompts and incoming messages
tend to get mixed up. You can try it out by running the `multipeer.py` file.
There is also a cleaner Pythonista UI version of the chat in `multipeer_chat`.

Here are the things to note when starting to use this library:

## Peer-to-peer, not client-server

This wrapper around the MC framework makes no assumptions regarding the
relationships between peers. If you need client-server roles, you can build
them on top.

## Expected usage

1. Create a subclass of `MultipeerCommunications` to handle messages from
the framework (see separate topic, below).
2. Instantiate the subclass with your service type, peer display name and
optional initial context data (see the class description).
3. Wait for peers to connect (see the `peer_added` and `get_peers` methods).
4. Optionally, have each participating peer stop accepting further peers,
e.g. for the duration of a game (see the `stop_looking_for_peers` method).
5. Send and receive messages (see a separate topic, below).
6. Potentially react to additions and removal of peers.
7. Optionally, start accepting peers again, e.g. after a previous
game ends (see the `start_looking_for_peers` method).
8. Before your app exits, call the `end_all` method to make sure there are
no lingering connections.

## What's in a message?

Messages passed between peers are UTF-8 encoded text. This wrapper
JSON-serializes the message you give to the `send` method (probably a str or
a dict), then encodes it in bytes. Receiving peers reconstitute the message
and pass it to the `receive` callback.

## Streaming

There are methods to use streaming instead of simple messages. Streamed data
is received in 1024 byte chunks. There is a constructor option
`initialize_streams` that can be used to set up a stream with each connected
peer; otherwise, the streams are initialized when needed.

## Performance

Pythonista forum user `mithrendal` ran some ping tests with very small data
payload and 1000 repeats. Observed average times for a two-way messages were:

* 11.85 ms - `send` method with `reliable=False`
* 11.94 ms - `send` method with `reliable=True` (the default)
* 6.19 ms - `stream` method

Tentative conclusions from these results:

* Connections are likely to be good enough that reliable messaging is not a
performance concern.
* Streaming may be significantly better if
communications delay is an issue.

## What is a peer ID?

Peer IDs passed around by the wrapper have a `display_name` member that
gives you the display name of that peer. There is no guarantee that these
names are unique between peers.

The IDs act also as identifier objects for specific peers, and can be used
to `send` messages to individual peers.

You cannot create peer IDs for remote peers manually.

## Why do I need to subclass?

This wrapper chooses to handle callbacks via subclassing rather than
requiring a separate delegate class. Subclass should define the following
methods; see the API for the method signatures:

* `peer_added`
* `peer_removed`
* `receive`
* `stream_receive`

The versions of these methods in the `MultipeerConnectivity` class just
print out the information received.

Note that if these method update the UI, you should decorate them with
`objc_util.on_main_thread`.

## Additional details

* This implementation uses automatic invite of all peer◊s (until you call
`stop_looking_for_peers`). Future version may include a callback for making
decisions on which peers to accept.
* Related to the previous point, including discovery info while browsing for
peers is not currently supported.
* Also, there is no way to explicitly kick a specific peer out of a session.
This seems to be a limitation of the Apple framework.
* Following defaults are used and are not currently configurable without
resorting to ObjC:
* Secure - Encryption is required on all connections.
* Not secure - A specific security identity cannot be set.

## Version history

* 1.0 - first version submitted to PyPi
* 0.9 - first functional version

# API

* [Class: MultipeerConnectivity](#class-multipeerconnectivity)
  * [Methods](#methods)
* [Functions](#functions)


## Class: MultipeerConnectivity

Multipeer communications. Subclass this class to define how you want
to react to added or removed peers, and to process incoming messages
from peers.

Constructor:

    mc = MultipeerConnectivity(display_name='Peer', service_type='dev-srv')

Arguments:

* `display_name` - This peer's display name (e.g. a player name). Must
not be None or an empty string, and must be at most 63 bytes long
(UTF-8 encoded).
* `service_type` - String that must match with that of the peers in
order for a connection to be established. Must be 1-15 characters in
length and contain only a-z, 0-9, or '-'.
* `initial_data` - Any JSON-serializable data that can be requested by
peers with a call to `get_initial_data()`.
* `initialize_streams` - If True, a stream is set up to any peer that
connects.

Created object will immediately start advertising and browsing for peers.

## Methods


#### `peer_added(self, peer_id)`

  Override handling of new peers in a subclass. 

#### `peer_removed(self, peer_id)`

  Override handling of lost peers in a subclass. 

#### `get_peers(self)`

  Get a list of peers currently connected. 

#### `get_initial_data(self, peer_id)`

  Returns initial context data provided by the peer, or None. 

#### `start_looking_for_peers(self)`

  Start conmecting to available peers. 

#### `stop_looking_for_peers(self)`

  Stop advertising for new connections, e.g. when you have all the
  players and start a game, and do not want new players joining in the
  middle. 

#### `send(self, message, to_peer=None, reliable=True)`

  Send a message to some or all peers.
  
  * `message` - to be sent to the peer(s). Must be JSON-serializable.
  * `to_peer` - receiver peer IDs. Can be a single peer ID, a list of peer
  IDs, or left out (None) for sending to all connected peers.
  * `reliable` - indicates whether delivery of data should be guaranteed
  (enqueueing and retransmitting data as needed, and ensuring in-order
  delivery). Default is True, but can be set to False for performance
  reasons.

#### `stream(self, byte_data, to_peer=None)`

  Stream message string to some or all peers. Stream per receiver will
  be set up on first call. See constructor parameters for the option to have
  streams per peer initialized on connection.
  
  * `byte_data` - data to be sent to the peer(s). If you are sending a
  string, call its `encode()` method and pass the result to this method.
  * `to_peer` - receiver peer IDs. Can be a single peer ID, a list of peer
  IDs, or left out (None) for sending to all connected peers.

#### `receive(self, message, from_peer)`

  Override in a subclass to handle incoming messages. 

#### `stream_receive(self, byte_data, from_peer)`

  Override in a subclass to handle incoming streamed data.
  `byte_data` is a `bytearray`; call its `decode()` method if you expect a
  string.

#### `disconnect(self)`

  End your games or similar sessions by calling this method. 

#### `end_all(self)`

  Disconnects from the multipeer session and removes internal references.
  Further communications will require instantiating a new
  MultipeerCommunications (sub)class. 
# Functions


#### `get_self(manager_object)`

  Expects a 'manager object', i.e. one of session, advertiser or
  browser, and uses the contained peer ID to locate the right Python manager
  object. 
