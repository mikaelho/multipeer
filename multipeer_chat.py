#coding: utf-8

if __name__ == '__main__':

  # Peer chat UI as a demonstration

  import ui
  import multipeer
  from objc_util import *
  
  class ChatPeer(multipeer.MultipeerConnectivity):
    
    @on_main_thread
    def peer_added(self, peer):
      self.show_updated_peer_list()
      
    @on_main_thread
    def peer_removed(self, peer):
      self.show_updated_peer_list()
      
    def show_updated_peer_list(self):
      peer_list = self.get_peers()
      as_text = 'Chatting with:\n' +  '\n'.join([peer.display_name for peer in peer_list])
      peers.text = as_text
      
    @on_main_thread
    def receive(self, message, from_peer):
      msg = from_peer.display_name + ': ' + message['text'] + ' (#' + str(message['count']) + ')\n'
      received_messages.text += msg
  
  class ChatView(ui.View):
    
    def __init__(self, **kwargs):
      super().__init__(**kwargs)
      self.message_count = 0
      self.mc = None
    
    def trigger_start_chat(self, sender):
      name_field.end_editing()
    
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
      if self.mc != None:
        self.mc.end_all()
  
  chat = ChatView(background_color=(.8, .92, 1.0))
  chat.present()
  
  (w,h) = chat.width, chat.height
  
  name_field = ui.TextField(placeholder='Your display name', frame=(20,20,w-80, 40), flex='W')
  go_button = ui.Button(title='Go', frame=(0.9*w,20,80,80), flex='W', background_color='grey', tint_color='white')
  name_field.action = chat.start_chat
  go_button.action = chat.trigger_start_chat
  
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