#coding: utf-8
import random, uuid, math, json, time
from collections import deque

from ui import *
from objc_util import on_main_thread
import sound

from scripter import *
import multipeer


def log_this(msg):
  with open('log.txt', 'a') as f:
    f.write(msg + '\n')

class Grid(View):
  
  size = 300 # multiple of 3
  gap = 20
  
  def __init__(self, game, **kwargs):
    super().__init__(**kwargs)
    self.game = game
    self.m_size = self.size//3
    self.matrix = [[0] * (self.m_size) for i in range(self.m_size)]
    for i in range(self.m_size):
      self.matrix[i][0] = 1
      self.matrix[i][-1] = 1
      self.matrix[0][i] = 1
      self.matrix[-1][i] = 1
    
    start_gap = 4*self.m_size // len(game.players)
    for i, id in enumerate(game.player_ids):
      player = game.players[id]
      run_length = start_gap//3 + i*start_gap
      player.direction = side = int((run_length // self.m_size) % 4)
      side_pos = run_length % self.m_size
      maxi = self.m_size-1
      if side == 0:
        pos = (int(maxi-side_pos),int(maxi))
      elif side == 1:
        pos = (0,int(maxi-side_pos))
      elif side == 2:
        pos = (int(side_pos), 0)
      else:
        pos = (int(maxi), int(side_pos))
      player.track.append(pos)
  
  def draw(self):
    set_color('blue')
    set_shadow('white',0,0,3)
    self.game.start_x = self.start_x = (self.width-300)/2
    self.game.start_y = self.start_y = (self.height-300)/2
    p = Path()
    for i in range(0, self.size+1, self.gap):
      p.move_to(self.start_x+i, self.start_y)
      p.line_to(self.start_x+i, self.start_y+self.size)
    for i in range(0, self.size+1, self.gap):
      p.move_to(self.start_x, self.start_y+i)
      p.line_to(self.start_x+self.size, self.start_y+i)
    p.stroke()
    
  def touch_ended(self, touch):
    self.game.add_turn(-1 if touch.location[0] < self.width/2 else 1)

class Player():
  
  directions = ((0, -1), (1, 0), (0, 1), (-1, 0))
  colors = ((1.0, .42, .19), 'orange', 'yellow', 'lightgreen', 'cyan', (.0, .57, 1.0), (.68, .26, 1.0), 'violet')
  
  def __init__(self, color, id=None):
    self.id = id or str(uuid.uuid4())
    color = parse_color(color)
    self.color = tuple([component for component in color[:3]])
    self.track = []
    self.direction = 0
    self.committed = False
    
  def move_in(self, direction):
    current = self.track[-1]
    delta = self.directions[direction]
    self.track.append((
      current[0] + delta[0],
      current[1] + delta[1]
    ))
    self.direction = direction
    
  def get_next_turn(self, game):
    direction = self.direction
    turn = 0
    tq = game.touch_queues.setdefault(self.id, deque())
    if len(tq) > 0:
      turn = tq.popleft()
      direction += turn
    if direction == 4:
      direction = 0
    if direction == -1:
      direction = 3
    self.move_in(direction)
    return self.track[-1]

    
class Robot(Player):
  
  def get_next_turn(self, game):
    direction = self.direction
    threshold = 0.02
    open_directions = [direction for direction in range(4) if self.open(game, direction)]
    if self.direction not in open_directions or random.random() < threshold:
      if len(open_directions) > 0:
        direction = random.choice(open_directions)
    self.move_in(direction)
    return self.track[-1]
    
  def open(self, game, direction):
    current = self.track[-1]
    delta = self.directions[direction]
    try:
      isopen = game.grid.matrix[current[0] + delta[0]][current[1] + delta[1]] == 0
      return isopen
    except:
      return False


class Game(View):
  '''
  Game object contains information about the players and the state of the game.
  
  Different subclasses of the game provide AI and local network opponents. Future expansion could add Internet-based opponents, although latency would need more careful management there.
  
  This object takes a `delegate` argument. Delegate should have some or all of the callback methods:
    
      def player_found(self, player):
        # Called with information about a player.
        pass
        
      def player_committed(self, player):
        # Called when player is ready to start a game.
        pass
        
      def player_lost(self, player):
        # Called with information about an removed player.
        pass
  '''
  
  def __init__(self, player, delegate, **kwargs):
    super().__init__(**kwargs)
    self.delegate = delegate
    self.players = { player.id: player }
    self.local_player = player
    self.touch_enabled = False
    self.intro_counter = None
    self.intro_distance = 10
    self.derezzes = []
    self.master = True
    self.touch_queues = {}
    
  @property
  def player_list(self):
    return list(self.players.values())
    
  def player_found(self, player):
    self.players[player.id] = player
    self._callback('player_found', player)
    
  def player_committed(self, id):
    player = self.players[id]
    player.committed = True
    self._callback('player_committed', player)
    if all([p.committed for p in self.players.values()]):
      self.all_players_committed()
    
  def finalize_players(self):
    self.player_ids = sorted(list(self.players.keys()))
    
  def all_players_committed(self):
    self.finalize_players()
    self.touch_queues[self.local_player.id] = deque()
    self.start_time = time.time() + 2.0
    #seed = sum([id.int for id in self.player_ids])
    #random.seed(seed)
    self._callback('all_players_committed')
    
  def add_turn(self, turn):
    self.touch_queues[self.local_player.id].append(turn)
    
  @script
  def loop(self):
    
    # Show player arriving
    self.intro_counter = 1 
    duration = self.start_time - time.time()
    slide_value(self, 'intro_counter', self.intro_distance, duration=duration, side_func=self.set_needs_display)
    yield
    self.intro_counter = None
    
    if self.master:
    
      next_tick_at = time.time() + 0.08
      # Main loop
      while len(self.players) > 1 or len(self.derezzes) > 0:       
        for player in self.players.values():
          player.get_next_turn(self)
        delta_to_next_tick = next_tick_at - time.time()
        yield delta_to_next_tick
        next_tick_at += 0.1
        to_be_removed = set()
        for player in self.players.values():
          while len(player.track) < len(self.local_player.track):
            yield 0.01
          pos = player.track[-1] 
          #get_next_turn(self)
          
          # Collision detection
          try:
            collision =  self.grid.matrix[pos[0]][pos[1]] == 1
          except:
            print('ex', pos)
            collision = True
          if collision:
            to_be_removed.add((player.id, pos))
          else:
            self.grid.matrix[pos[0]][pos[1]] = 1
        for id, pos in to_be_removed:
          self.remove_player(id, pos)
        self.update_display()
    else:
      self.receive_loop()
    yield 1
    self._callback('winner_exit')
    
  def update_display(self):
    self.set_needs_display()
    
  def remove_player(self, id, pos):
    self.derezzes.append([0,*pos, self.players[id].color])
    sound.play_effect('arcade:Powerup_1')
    for (i,j) in self.players[id].track[1:]:
      self.grid.matrix[i][j] = 0
    del self.players[id]
    self.player_ids.remove(id)
    
  def draw(self):
    sx = self.start_x
    sy = self.start_y
    if self.intro_counter is not None:
      set_color(self.local_player.color)
      fx,fy = self.local_player.track[0]
      direction = Player.directions[self.local_player.direction]
      dx, dy = -direction[0]*self.intro_distance, -direction[1]*self.intro_distance
      cx, cy = dx+direction[0]*self.intro_counter, dy+direction[1]*self.intro_counter
      p = Path()
      p.move_to(sx+(fx+dx)*3, sy+(fy+dy)*3)
      p.line_to(sx+(fx+cx)*3, sy+(fy+cy)*3)
      p.stroke()
    else:
      for player in self.players.values():
        track = player.track
        if len(track) < 2: return
        set_color(player.color)
        p = Path()
        p.line_width = 2
        p.move_to(sx+track[0][0]*3, sy+track[0][1]*3)
        for point in track[1:-1]:
          p.line_to(sx+point[0]*3, sy+point[1]*3)
        p.stroke()
        set_color('white')
        p = Path()
        p.move_to(sx+track[-2][0]*3, sy+track[-2][1]*3)
        p.line_to(sx+track[-1][0]*3, sy+track[-1][1]*3)
        p.line_width = 3
        p.stroke()
      for derez in self.derezzes:
        derez[0] += 1
        radius, x, y, color = derez
        p = Path.oval(sx+(x-radius)*3,sy+(y-radius)*3,6*radius,6*radius)
        set_color(color + (1.0-radius/6,))
        p.fill()
          
      self.derezzes = [ derez for derez in self.derezzes if derez[0] < 6]
        
  def end_game(self):
    pass
    
  def _callback(self, func_name, *args, **kwargs):
    func = getattr(self.delegate, func_name, None)
    if func is not None:
      func(*args, **kwargs)
  
  def start_robots(self, no_of_robots):
    colors = random.sample(Player.colors, no_of_robots)
    for i in range(no_of_robots):
      robot = Robot(colors[i])
      self.player_found(robot)
      
      
class PeerComms(multipeer.MultipeerConnectivity):
  
  def __init__(self, game, player):
    self.game = game
    initial_data = json.dumps({
      'id': player.id,
      'color': player.color
    })
    self.mc_to_game_id = {}
    self.game_to_mc_id = {}
    super().__init__(display_name='Contender', service_type='lightcycle', initial_data=initial_data, initialize_streams=True)
  
  @on_main_thread
  def peer_added(self, peer_id):
    data = json.loads(self.get_initial_data(peer_id))
    self.mc_to_game_id[peer_id.hash()] = data['id']
    self.game_to_mc_id[data['id']] = peer_id
    player = Player(tuple(data['color']), data['id'])
    self.game.player_found(player)
    
  @on_main_thread
  def receive(self, msg, from_peer):
    if msg['action'] == 'commit':
      self.game.player_committed(msg['id'])
    elif msg['action'] == 'move':
      self.game.add_remote_move(msg['id'], msg['pos'])
    elif msg['action'] == 'sync':
      self.game.start_game(msg['time'])
    else:
      print('Unknown action', msg)
      
  def stream_receive(self, byte_data, peer_id):
    id = self.mc_to_game_id[peer_id.hash()]
    while len(byte_data) > 0:
      if self.game.master:
        # Getting turns from slaves
        turn = int(byte_data)
        self.game.add_remote_turn(id, turn)
        byte_data = byte_data[2:]
      else:
        # From master...
        self.game.incoming.append(byte_data[0])
        byte_data = byte_data[1:]
      
  def send_commit(self, id):
    self.send({
      'action': 'commit',
      'id': id
    })
    
  def send_sync(self, start_time):
    self.send({
      'action': 'sync',
      'time': start_time
    })
    
  def send_turn(self, master_id, turn):
    peer_id = self.game_to_mc_id[master_id]
    packet = ('+' + str(turn))[-2:].encode()
    self.stream(packet, peer_id)
    
  def send_removal(self, id, pos):
    # 1 + 36 + 2 = 39
    packet = chr(111) + id + chr(pos[0]) + chr(pos[1])
    packet = packet.encode()
    self.stream(packet)
    
  def send_poss(self, poss):
    packet = chr(1)
    for pos in poss:
      packet += chr(pos[0]) + chr(pos[1])
    packet = packet.encode()
    self.stream(packet)

      
class PeerGame(Game):
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.mc = PeerComms(self, self.local_player)
    self.mc.start_looking_for_peers()
    self.incoming = deque()
    
  @script
  def receive_loop(self):
    self.buffer = bytearray()
    while len(self.players) > 1 or len(self.derezzes) > 0:
      self._read_n()
      yield
      if self.buffer[0] == 111: # ... Removal
        self._read_n(38)
        yield
        id = self.buffer[:36].decode()
        pos = (self.buffer[36], self.buffer[37])
        self.remote_remove_player(id, pos)
      else: # ... Positions
        poss = []
        for _ in range(len(self.players)):
          self._read_n(2)
          yield
          poss.append((self.buffer[0], self.buffer[1]))
        self.add_remote_poss(poss)
    yield 1
    self._callback('winner_exit')
  
  @script
  def _read_n(self, n=1):
    self.buffer = bytearray()
    for _ in range(n-len(self.buffer)):
      while len(self.incoming) == 0:
        yield
      self.buffer.append(self.incoming.popleft())
    
  def player_committed(self, id):
    if id == self.local_player.id:
      self.mc.send_commit(id)
    super().player_committed(id)
    
  def all_players_committed(self):
    self.mc.stop_looking_for_peers()
    self.finalize_players()
    self.master = self.player_ids[0] == self.local_player.id
    if self.master:
      self.start_time = time.time() + 2.0
      self.mc.send_sync(self.start_time)
      self._callback('all_players_committed')

  def start_game(self, timestamp):
    ''' Master is telling us when the game starts '''
    self.start_time = timestamp
    self._callback('all_players_committed')
    
  def add_turn(self, turn):
    if self.master:
      super().add_turn(turn)
    else:
      self.mc.send_turn(self.player_ids[0], turn)
      
  # Master
  def add_remote_turn(self, id, turn):
    self.touch_queues.setdefault(id, deque()).append(turn)
    
  # Spoke
  def add_remote_poss(self, poss):
    for i, id in enumerate(self.player_ids):
      self.players[id].track.append(poss[i])
    super().update_display()
    
  # Master
  def update_display(self):
    poss = [ player.track[-1] for player in [ self.players[id] for id in self.player_ids ]]
    self.mc.send_poss(poss)
    super().update_display()
    
  # Master
  def remove_player(self, id, pos):
    self.mc.send_removal(id, pos)
    super().remove_player(id, pos)

  # Spoke
  def remote_remove_player(self, id, pos):
    super().remove_player(id, pos)
    
  def end_game(self):
    self.mc.end_all()
      
class MenuBike(View):
  
  def __init__(self, color='cyan', **kwargs):
    super().__init__(**kwargs)
    self.frame = (-2050, 100, 2050, 30)
    self.bounds = (-2000, 0, 2050, 30)
    self.color = color
    self.selected = False
    self.moving = False
    
  def draw(self):
    set_color(self.color)
    set_shadow(self.color, 0, 0, 16)
    p = Path()
    p.append_path(Path.oval(10,10,10,10))
    p.append_path(Path.oval(26,10,10,10))
    p.move_to(15,10)
    p.add_arc(23,15,10,math.radians(210),math.radians(330))
    p.stroke()
    
    p = Path()
    p.move_to(13,5)
    p.add_arc(15,15,10,math.radians(260),math.radians(150), False)
    p.line_to(-2000,20)
    p.line_to(-2000,5)
    p.line_to(13,5)
    p.fill()
    
  def touch_ended(self, touch):
    if hasattr(self, 'action') and callable(self.action):
      self.action(self)
      
  @script
  def move_forward(self):
    move_by(self, self.superview.width/3, 0)
    yield
    move_by(self, -self.superview.width/3/2, 0, duration=1.0)
    self.selected = True
    
  @script
  def fade_to_back(self):
    move_by(self, -self.superview.width/3, 0, duration=1.0)

    
class StartMenu(View):

  @script
  def show_menu(self):
    self.bike_views = [MenuBike(color) for color in Player.colors]
    self.start = 100
    self.gap = (self.height-2*self.start)/(len(Player.colors)-1)
    for i, bike_view in enumerate(self.bike_views):
      bike_view.y = self.start+i*self.gap
      bike_view.action = self.select_color
      self.add_subview(bike_view)
      bike_view.moving = True
      move_by(bike_view, self.width/3, 0)
    yield
    for bike_view in self.bike_views:
      bike_view.moving = False
  
  @script  
  def select_color(self, sender):
    if sender.moving: return
    if not sender.selected:
      self.player = Player(sender.color)
      self.player.menu_bike = sender
      player_index = Player.colors.index(sender.color)
      self.available_slots = list(range(len(Player.colors)))
      del self.available_slots[player_index]
      for i, view in enumerate(self.bike_views):
        if i == player_index:
          view.move_forward()
        else:
          view.fade_to_back()
      self.game = game_type(
        player=self.player,
        delegate=self
      )
      self.game.start_robots(no_of_robots)
    else:
      move_by(self.player.menu_bike, self.width, 0)
      yield
      self.game.player_committed(self.player.id)
  
  @script  
  def player_found(self, player):
    player_slot = random.choice(self.available_slots)
    self.available_slots.remove(player_slot)
    player.menu_bike = MenuBike(player.color)
    player.menu_bike.y = self.start + player_slot*self.gap
    self.add_subview(player.menu_bike)
    move_by(player.menu_bike, self.width/3, 0)
    if type(player) == Robot:
      yield random.random()*2.5
      self.game.player_committed(player.id)
    
  def player_committed(self, player):
    move_by(player.menu_bike, self.width, 0)
  
  @script
  def all_players_committed(self):
    self.grid = Grid(self.game, frame=self.bounds, background_color='black', alpha=0.0)
    self.add_subview(self.grid)
    show(self.grid)
    yield
    self.game.grid = self.grid
    self.game.frame=self.bounds
    self.add_subview(self.game)
    
    # Rotate board so that local player always starts from the bottom
    rotate_game = -self.game.local_player.direction*90
    self.game.transform = Transform.rotation(math.radians(rotate_game))
    yield 0.5
    self.game.loop()
    
  @script
  def winner_exit(self):
    # Celebratory winner transformation
    starting_transform = self.game.transform
    slide_value(self.game, 'transform', 5, start_value=1, map_func=lambda r: starting_transform.concat(Transform.scale(r,r).concat(Transform.rotation(r-1.0))), duration=2)
    hide(self.game, duration=2)
    #sound.play_effect('digital:PowerUp3')
    yield 0.5
    #hide(self.grid)
    for view in self.subviews:
      view.alpha = 0.0
    
  def will_close(self):
    if hasattr(self, 'game'):
      self.game.end_game()

if __name__ == '__main__':
  
  game_type = PeerGame
  #game_type = Game
  no_of_robots = 0
  
  v = StartMenu()
  v.background_color = 'black'
  v.present(hide_title_bar=True)
  v.show_menu()


