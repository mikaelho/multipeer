# -*- coding: utf-8 -*-

"""
Multipeer connectivity for the Pythonista iOS app

# Multipeer

This is a [Pythonista](http://omz-software.com/pythonista/) wrapper around iOS
[Multipeer Connectivity](https://developer.apple.com/documentation
/multipeerconnectivity?language=objc).

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
"""

__version__ = '1.0.1'

from objc_util import *
import ctypes, re, json, heapq

# MC framework classes
NSBundle.bundle(Path="/System/Library/Frameworks/MultipeerConnectivity"
                     ".framework").load()
MCPeerID = ObjCClass('MCPeerID')
MCSession = ObjCClass('MCSession')
MCNearbyServiceAdvertiser = ObjCClass('MCNearbyServiceAdvertiser')
MCNearbyServiceBrowser = ObjCClass('MCNearbyServiceBrowser')
NSRunLoop = ObjCClass('NSRunLoop')
NSDefaultRunLoopMode = ObjCInstance(c_void_p.in_dll(c, "NSDefaultRunLoopMode"))

# Global variable and a helper function for accessing Python manager object
# from ObjC functions. Dictionary is used to support running more than one
# MC object simultaneously.

mc_managers = {}
mc_inputstream_managers = {}

def get_self(manager_object):
    """ Expects a 'manager object', i.e. one of session, advertiser or
    browser, and uses the contained peer ID to locate the right Python manager
    object. """
    global mc_managers
    return mc_managers.get(
        ObjCInstance(manager_object).myPeerID().hash(),
        None)

# MC Framework delegate definitions

def session_peer_didChangeState_(_self,_cmd,_session,_peerID,_state):
    self = get_self(_session)
    if self is None: return
    peerID = ObjCInstance(_peerID)
    peerID.display_name = str(peerID.displayName())
    if _state == 2:
        self._peer_collector(peerID)
    if (_state is None or _state == 0):
        self.peer_removed(peerID)


def session_didReceiveData_fromPeer_(_self, _cmd, _session, _data, _peerID):
    self = get_self(_session)
    if self is None: return
    peer_id = ObjCInstance(_peerID)
    peer_id.display_name = str(peer_id.displayName())
    decoded_data = nsdata_to_bytes(ObjCInstance(_data)).decode()
    message = json.loads(decoded_data)
    self.receive(message, peer_id)


def session_didReceiveStream_withName_fromPeer_(_self, _cmd, _session, _stream,
        _streamName, _peerID):
    self = get_self(_session)
    if self is None: return
    stream = ObjCInstance(_stream)
    peer_id = ObjCInstance(_peerID)
    stream.setDelegate_(ObjCInstance(_self))
    mc_inputstream_managers[stream] = self
    self.peer_per_inputstream[stream] = peer_id
    stream.scheduleInRunLoop_forMode_(NSRunLoop.mainRunLoop(),
        NSDefaultRunLoopMode)
    stream.open()


def stream_handleEvent_(_self, _cmd, _stream, _event):
    if _event == 2:  # hasBytesAvailable
        buffer = ctypes.create_string_buffer(1024)
        stream = ObjCInstance(_stream)
        read_len = stream.read_maxLength_(buffer, 1024)
        if read_len > 0:
            content = bytearray(buffer[:read_len])
            self = mc_inputstream_managers[stream]
            peer_id = self.peer_per_inputstream[stream]
            self.stream_receive(content, peer_id)


SessionDelegate = create_objc_class('SessionDelegate',
    methods=[session_peer_didChangeState_, session_didReceiveData_fromPeer_,
             session_didReceiveStream_withName_fromPeer_, stream_handleEvent_],
    protocols=['MCSessionDelegate', 'NSStreamDelegate'])
SDelegate = SessionDelegate.alloc().init()


def browser_didNotStartBrowsingForPeers_(_self, _cmd, _browser, _err):
    print('MultipeerConnectivity framework error')


def browser_foundPeer_withDiscoveryInfo_(_self, _cmd, _browser, _peerID,
        _info):
    self = get_self(_browser)
    if self is None: return

    peerID = ObjCInstance(_peerID)
    browser = ObjCInstance(_browser)
    context = json.dumps(
        self.initial_data).encode() if self.initial_data is not None else None
    browser.invitePeer_toSession_withContext_timeout_(peerID, self.session,
        context, 0)


def browser_lostPeer_(_self, _cmd, browser, peer):
    # print ('lost peer')
    pass


BrowserDelegate = create_objc_class('BrowserDelegate',
    methods=[browser_foundPeer_withDiscoveryInfo_, browser_lostPeer_,
             browser_didNotStartBrowsingForPeers_],
    protocols=['MCNearbyServiceBrowserDelegate'])
Bdelegate = BrowserDelegate.alloc().init()


class _block_descriptor(Structure):
    _fields_ = [('reserved', c_ulong), ('size', c_ulong),
                ('copy_helper', c_void_p), ('dispose_helper', c_void_p),
                ('signature', c_char_p)]


InvokeFuncType = ctypes.CFUNCTYPE(None, *[c_void_p, ctypes.c_bool, c_void_p])


class _block_literal(Structure):
    _fields_ = [('isa', c_void_p), ('flags', c_int), ('reserved', c_int),
                ('invoke', InvokeFuncType), ('descriptor', _block_descriptor)]


# Advertiser Delegate
def advertiser_didReceiveInvitationFromPeer_withContext_invitationHandler_(
        _self, _cmd, _advertiser, _peerID, _context, _invitationHandler):
    self = get_self(_advertiser)
    if self is None: return
    peer_id = ObjCInstance(_peerID)
    if _context is not None:
        decoded_data = nsdata_to_bytes(ObjCInstance(_context)).decode()
        initial_data = json.loads(decoded_data)
        self.initial_peer_data[peer_id.hash()] = initial_data
    peer_id.display_name = str(peer_id.displayName())
    self._peer_collector(peer_id)
    invitation_handler = ObjCInstance(_invitationHandler)
    retain_global(invitation_handler)
    blk = _block_literal.from_address(_invitationHandler)
    blk.invoke(invitation_handler, True, self.session)


f = advertiser_didReceiveInvitationFromPeer_withContext_invitationHandler_
f.argtypes = [c_void_p] * 4
f.restype = None
f.encoding = b'v@:@@@@?'
AdvertiserDelegate = create_objc_class('AdvertiserDelegate', methods=[
    advertiser_didReceiveInvitationFromPeer_withContext_invitationHandler_])
ADelegate = AdvertiserDelegate.alloc().init()

  
  # Wrapper class
  
class MultipeerConnectivity():
    """ Multipeer communications. Subclass this class to define how you want
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
    """


    def __init__(self, display_name='Peer', service_type='dev-srv',
            initial_data=None, initialize_streams=False):
        global mc_managers
    
        if display_name is None or display_name == '' or len(
                display_name.encode()) > 63:
            raise ValueError(
                'display_name must not be None or empty string, and must be at '
                'most 63 bytes long (UTF-8 encoded)', display_name)
    
        self.service_type = service_type
        check_re = re.compile(r'[^a-z0-9\-.]')
        check_str = check_re.search(self.service_type)
        if len(self.service_type) < 1 or len(self.service_type) > 15 or bool(
                check_str):
            raise ValueError(
                'service_type must be 1-15 characters long and can contain only '
                'ASCII lowercase letters, numbers and hyphens', service_type)
    
        self.my_id = MCPeerID.alloc().initWithDisplayName(display_name)
        self.my_id.display_name = str(self.my_id.displayName())
    
        self.initial_data = initial_data
        self.initial_peer_data = {}
        self._peer_connection_hit_count = {}
    
        mc_managers[self.my_id.hash()] = self
    
        self.initialize_streams = initialize_streams
        self.outputstream_per_peer = {}
        self.peer_per_inputstream = {}
    
        self.session = MCSession.alloc().initWithPeer_(self.my_id)
        self.session.setDelegate_(SDelegate)
    
        # Create browser and set delegate
        self.browser = MCNearbyServiceBrowser.alloc().initWithPeer_serviceType_(
            self.my_id, self.service_type)
        self.browser.setDelegate_(Bdelegate)
    
        # Create advertiser and set delegate
        self.advertiser = MCNearbyServiceAdvertiser.alloc().\
            initWithPeer_discoveryInfo_serviceType_(
                self.my_id, ns({}), self.service_type)
        self.advertiser.setDelegate_(ADelegate)
    
        self.start_looking_for_peers()
    
    
    def peer_added(self, peer_id):
        """ Override handling of new peers in a subclass. """
        print('Added peer', peer_id.display_name)
        print('Initial data:', self.get_initial_data(peer_id))
    
    
    def peer_removed(self, peer_id):
        """ Override handling of lost peers in a subclass. """
        print('Removed peer', peer_id.display_name)
    
    
    def get_peers(self):
        ''' Get a list of peers currently connected. '''
        peer_list = []
        for peer in self.session.connectedPeers():
            peer.display_name = str(peer.displayName())
            peer_list.append(peer)
        return peer_list
    
    
    def get_initial_data(self, peer_id):
        """ Returns initial context data provided by the peer, or None. """
        return self.initial_peer_data.get(peer_id.hash(), None)
    
    
    def start_looking_for_peers(self):
        """ Start conmecting to available peers. """
        self.browser.startBrowsingForPeers()
        self.advertiser.startAdvertisingPeer()
    
    
    def stop_looking_for_peers(self):
        """ Stop advertising for new connections, e.g. when you have all the
        players and start a game, and do not want new players joining in the
        middle. """
        self.advertiser.stopAdvertisingPeer()
        self.browser.stopBrowsingForPeers()
    
    
    def send(self, message, to_peer=None, reliable=True):
        """ Send a message to some or all peers.
    
        * `message` - to be sent to the peer(s). Must be JSON-serializable.
        * `to_peer` - receiver peer IDs. Can be a single peer ID, a list of peer
        IDs, or left out (None) for sending to all connected peers.
        * `reliable` - indicates whether delivery of data should be guaranteed
        (enqueueing and retransmitting data as needed, and ensuring in-order
        delivery). Default is True, but can be set to False for performance
        reasons.
        """
        if type(to_peer) == list:
            peers = to_peer
        elif to_peer is None:
            peers = self.get_peers()
        else:
            peers = [to_peer]
    
        message = json.dumps(message)
        message = message.encode()
    
        send_mode = 0 if reliable else 1
        self.session.sendData_toPeers_withMode_error_(message, peers, send_mode,
            None)
    
    
    def stream(self, byte_data, to_peer=None):
        """ Stream message string to some or all peers. Stream per receiver will
        be set up on first call. See constructor parameters for the option to have
        streams per peer initialized on connection.
    
        * `byte_data` - data to be sent to the peer(s). If you are sending a
        string, call its `encode()` method and pass the result to this method.
        * `to_peer` - receiver peer IDs. Can be a single peer ID, a list of peer
        IDs, or left out (None) for sending to all connected peers.
        """
        if type(to_peer) == list:
            peers = to_peer
        elif to_peer is None:
            peers = self.get_peers()
        else:
            peers = [to_peer]
        for peer_id in peers:
            peer_id = ObjCInstance(peer_id)
            stream = self.outputstream_per_peer.get(peer_id.hash(), None)
            if stream is None:
                stream = self._set_up_stream(peer_id)
            data_len = len(byte_data)
            wrote_len = stream.write_maxLength_(byte_data, data_len)
            if wrote_len != data_len:
                print(f'Error writing data, wrote {wrote_len}/{data_len} bytes')
    
    
    def _set_up_stream(self, to_peer):
        output_stream = ObjCInstance(
            self.session.startStreamWithName_toPeer_error_('stream', to_peer,
                None))
        output_stream.setDelegate_(SDelegate)
        output_stream.scheduleInRunLoop_forMode_(NSRunLoop.mainRunLoop(),
            NSDefaultRunLoopMode)
    
        output_stream.open()
        self.outputstream_per_peer[to_peer.hash()] = output_stream
        return output_stream
    
    
    def receive(self, message, from_peer):
        """ Override in a subclass to handle incoming messages. """
        print('Message from', from_peer.display_name, '-', message)
    
    
    def stream_receive(self, byte_data, from_peer):
        """ Override in a subclass to handle incoming streamed data.
        `byte_data` is a `bytearray`; call its `decode()` method if you expect a
        string."""
        print('Message from', from_peer.display_name, '-', byte_data.decode())
    
    
    def disconnect(self):
        """ End your games or similar sessions by calling this method. """
        self.session.disconnect()
    
    
    def end_all(self):
        """ Disconnects from the multipeer session and removes internal references.
        Further communications will require instantiating a new
        MultipeerCommunications (sub)class. """
        self.stop_looking_for_peers()
        self.disconnect()
    
        del mc_managers[self.my_id.hash()]
    
    
    def _peer_collector(self, peer_id):
        """ Makes sure that `peer_added` is only called after the full "two-way
        handshake" is complete and the initial context info has been captured.
        Also sets up a stream to peer if requested by the constructor argument. """
        peer_hash = peer_id.hash()
        self._peer_connection_hit_count.setdefault(peer_hash, 0)
        self._peer_connection_hit_count[peer_hash] += 1
        if self._peer_connection_hit_count[peer_hash] > 1:
            if (self.initialize_streams and peer_hash not in
                    self.outputstream_per_peer):
                self._set_up_stream(peer_id)
            self.peer_added(peer_id)


if __name__ == '__main__':

    # Simple chat peer to demonstrate basic functionality

    import platform

    my_name = input('Name: ')

    mc = MultipeerConnectivity(display_name=my_name, service_type='chat',
        initial_data=platform.platform())

    try:
        while True:
            chat_message = input('Message: ')
            mc.send(chat_message)
    finally:
        mc.end_all()
