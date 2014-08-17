import libtcodpy as libtcod
import math

#############################################
# Constants and Big Vars
#############################################

# Size of the window
SCREEN_WIDTH = 110
SCREEN_HEIGHT = 80

# Size of the Map
MAP_WIDTH = 110
MAP_HEIGHT = 75

# Rooms
ROOM_MAX_SIZE = 13
ROOM_MIN_SIZE = 6
MAX_ROOMS = 200
MAX_ROOM_MONSTERS = 3

# Field of Vision
FOV_ALGO = 0
FOV_LIGHT_WALLS = True
TORCH_RADIUS = 10

# Colors of Terrain
color_dark_wall = libtcod.Color(0, 0, 100)
color_light_wall = libtcod.Color(130, 110, 50)
color_dark_ground = libtcod.Color(50, 50, 150)
color_light_ground = libtcod.Color(200, 180, 50)

map = []

#############################################
# Classes
#############################################

class BasicMonster:
  # AI for a Basic Monster
  def take_turn(self):
    # A basic monster takes its turn. If you can see it, it can see you.
    monster = self.owner
    if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):
      # Move towards player if non-adjacent.
      if monster.distance_to(player) >= 2:
        monster.move_towards(player.x, player.y)
      # Adjacent? Attack if the player is still alive.
      elif player.fighter.hp > 0:
        monster.fighter.attack(player)

class Fighter:
  # A composite class for combat-related properties.
  def __init__(self, hp, defense, power, death_function = None):
    self.max_hp = hp
    self.hp = hp
    self.defense = defense
    self.power = power
    self.death_function = death_function

  def attack(self, target):
    # A simple formula for attack damage.
    damage = self.power - target.fighter.defense
    if damage > 0:
      # Make the target take some damage.
      print(self.owner.name.capitalize(), 'attacks', target.name, 'for', str(damage), 'hit points.')
      target.fighter.take_damage(damage)
    else:
      print(self.owner.name.capitalize(), 'attacks', target.name, 'but it has no effect!')

  def take_damage(self, damage):
    # Apply damage if possible.
    if damage > 0:
      self.hp -= damage
      # Check for death. If there's a death function, call it.
      if self.hp <= 0:
        function = self.death_function
        if function is not None:
          function(self.owner)

class Object:
  # This object is a generic item in game: player, monster, item, tile feature
  # An object is always represented as a symbol on screen.
  def __init__(self, x, y, char, name, color, blocks=False, fighter=None, ai=None):
    self.x = x
    self.y = y
    self.char = char
    self.name = name
    self.color = color
    self.blocks = blocks
    self.fighter = fighter
    if self.fighter: # If there's a fighter component, set parent for component.
      self.fighter.owner = self
    self.ai = ai
    if self.ai: # If there's an AI component, set parent for component.
      self.ai.owner = self

  def clear(self):
    # Erase the character that represents this object
    libtcod.console_put_char(con, self.x, self.y, ' ', libtcod.BKGND_NONE)

  def distance_to(self, other):
    # Return the distance between self and another object.
    dx = other.x - self.x
    dy = other.y - self.y
    return math.sqrt(dx ** 2 + dy ** 2)

  def draw(self):
    # Check to see if the object is in the player's FOV
    if libtcod.map_is_in_fov(fov_map, self.x, self.y):
      # Set the color and then draw the corresponding character of the object in that color.
      libtcod.console_set_default_foreground(con, self.color)
      libtcod.console_put_char(con, self.x, self.y, self.char, libtcod.BKGND_NONE)

  def move(self, dx, dy):
    # Move object by the param amount.
    global map
    if not is_blocked(self.x + dx, self.y + dy):
      self.x += dx
      self.y += dy

  def move_towards(self, target_x, target_y):
    # Generate vector from this object to the target, and distance.
    dx = target_x - self.x
    dy = target_y - self.y
    distance = math.sqrt(dx ** 2 + dy ** 2)
    # Normalize distance to length 1 (preserving direction), then round it and convert it to integer so the movement is restricted to the map grid
    dx = int(round(dx / distance))
    dy = int(round(dy / distance))
    self.move(dx, dy)

  def send_to_back(self):
    # Make this object be drawn first, so all others appear above it if they're in the same tile.
    global objects
    objects.remove(self)
    objects.insert(0, self)

class Rect:
  # A rectangle used on a map, namely for the creation of rooms.
  def __init__(self, x, y, w, h):
    self.x1 = x
    self.y1 = y
    self.x2 = x + w
    self.y2 = y + h

  def center(self):
    # Returns the center of the Rect object.
    center_x = (self.x1 + self.x2) // 2
    center_y = (self.y1 + self.y2) // 2
    return center_x, center_y

  def intersect(self, other):
    # Returns True if this rect intersects with another one.
    return (self.x1 <= other.x2 and self.x2 >= other.x1 and self.y1 <= other.y2 and self.y2 >= other.y1)

class Tile:
  # A tile on the map
  def __init__(self, blocked, block_sight = None):
    self.blocked = blocked
    # By default, if a tile is blocked, it also blocks sight.
    if block_sight == None:
      block_sight = blocked
    self.block_sight = block_sight
    self.explored = False


#############################################
# Functions
#############################################

def create_h_tunnel(x1, x2, y):
  global map
  for x in range(min(x1, x2), max(x1, x2) + 1):
    map[x][y].blocked = False
    map[x][y].block_sight = False

def create_room(room):
  global map
  # Create passable areas in rooms, carved out via rects from map.
  for x in range(room.x1 + 1, room.x2):
    for y in range(room.y1 + 1, room.y2):
      map[x][y].blocked = False
      map[x][y].block_sight = False

def create_v_tunnel(y1, y2, x):
  global map
  for y in range(min(y1, y2), max(y1, y2) + 1):
    map[x][y].blocked = False
    map[x][y].block_sight = False

def handle_keys():
  global fov_recompute
  global player

  key = libtcod.console_wait_for_keypress(True)  # turn-based

  if key.vk == libtcod.KEY_ENTER and key.lalt:
    #Alt + Enter: Toggle Fullscreen
    libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

  elif key.vk == libtcod.KEY_ESCAPE:
    return 'exit'  # Exit Game

  # Game State Keys
  if game_state == 'playing':
    # Movement keys
    if libtcod.console_is_key_pressed(libtcod.KEY_UP):
      player_move_or_attack(0, -1)
    elif libtcod.console_is_key_pressed(libtcod.KEY_DOWN):
      player_move_or_attack(0, 1)
    elif libtcod.console_is_key_pressed(libtcod.KEY_LEFT):
      player_move_or_attack(-1, 0)
    elif libtcod.console_is_key_pressed(libtcod.KEY_RIGHT):
      player_move_or_attack(1, 0)
    else:
      return 'didnt-take-turn'

def is_blocked(x, y):
  # First, test if the map tile is blocking.
  if map[x][y].blocked:
    return True
  # Now check to see if there are any blocking objects.
  for object in objects:
    if object.blocks and object.x == x and object.y == y:
      return True
  # Otherwise, not blocked.
  return False

def make_map():
  global map, player

  # Fill the map with "blocked" tiles.
  map = [[ Tile(True)
    for y in range(MAP_HEIGHT) ]
      for x in range(MAP_WIDTH) ]

  rooms = []
  num_rooms = 0

  for r in range(MAX_ROOMS):
    # Random width and height for rooms.
    w = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
    h = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
    # Random position without going out of the boundaries of the map.
    x = libtcod.random_get_int(0, 0, MAP_WIDTH - w - 1)
    y = libtcod.random_get_int(0, 0, MAP_HEIGHT - h - 1)

    new_room = Rect(x, y, w, h)

    # Run through the other rooms and see if they intersect with the new_room.
    room_failed = False
    for other_room in rooms:
      if new_room.intersect(other_room):
        room_failed = True
        break

    if not room_failed:
      # There are no intersections, so this new_room is valid.
      create_room(new_room)

      # Create and place some objects / monsters!
      place_objects(new_room)

      # Center coordinates of new room.
      new_x, new_y = new_room.center()

      if num_rooms == 0:
        # If first room, initiate player at center tuple.
        player.x = new_x
        player.y = new_y
      else: # If not the first room, make some tunnels.
        # Center coordinates of previous room.
        prev_x, prev_y = rooms[num_rooms - 1].center()

        # Random 50/50 (random number that is either 0 or 1)
        if libtcod.random_get_int(0, 0, 1) == 1:
          # First move horizontally, then vertically.
          create_h_tunnel(prev_x, new_x, prev_y)
          create_v_tunnel(prev_y, new_y, new_x)
        else:
          # First move vertically, then horizontally.
          create_v_tunnel(prev_y, new_y, prev_x)
          create_h_tunnel(prev_x, new_x, new_y)

        # Append the new room to the list of rooms.
      rooms.append(new_room)
      num_rooms += 1

  #place the player inside the first room
  player.x = 25
  player.y = 23

def monster_death(monster):
  # Transform monster into a corpse! Corpses don't block, can't be attacked and don't move.
  print(monster.name.capitalize(), 'is dead!')
  monster.char = '%'
  monster.color = libtcod.dark_red
  monster.blocks = False
  monster.fighter = None
  monster.ai = None
  monster.name = 'remains of ' + monster.name
  monster.send_to_back()

def place_objects(room):
  global objects
  # Choose a random number of monsters.
  num_monsters = libtcod.random_get_int(0, 0, MAX_ROOM_MONSTERS)

  for i in range(num_monsters):
    # Choose a random spot for each given monster.
    x = libtcod.random_get_int(0, room.x1, room.x2)
    y = libtcod.random_get_int(0, room.y1, room.y2)

    # Only place object if x, y is not blocked.
    if not is_blocked(x, y):
      if libtcod.random_get_int(0, 0, 100) < 80: # 80% chance of getting an orc.
        # Create an orc.
        fighter_component = Fighter(hp = 10, defense = 0, power = 3, death_function = monster_death)
        ai_component = BasicMonster()
        monster = Object(x, y, 'o', 'orc', libtcod.desaturated_green, blocks = True, fighter = fighter_component, ai = ai_component)
      else:
        # Create a troll.
        fighter_component = Fighter(hp = 16, defense = 1, power = 4, death_function = monster_death)
        ai_component = BasicMonster()
        monster = Object(x, y, 'T', 'troll', libtcod.darker_green, blocks = True, fighter = fighter_component, ai = ai_component)
      objects.append(monster)

def player_death(player):
  # Player dead. The game ended!
  global game_state
  print('You died!')
  game_state = 'dead'
  # For added effect, transform the player into a corpse.
  player.char = '%'
  player.color = libtcod.dark_red

def player_move_or_attack(dx, dy):
  global fov_recompute
  # The coordinates the player is attempting to move to / attack.
  x = player.x + dx
  y = player.y + dy
  # Check for attackable object at coordinates.
  target = None
  for chk_object in objects:
    if chk_object.x == x and chk_object.y == y and chk_object.fighter:
      target = chk_object
      break
  # Attack the target if found, otherwise move player.
  if target is not None:
    player.fighter.attack(target)
  else:
    player.move(dx, dy)
    fov_recompute = True

def render_all():
  global color_light_ground, color_light_wall
  global color_dark_ground, color_dark_wall
  global fov_recompute
  global fov_map, map

  if fov_recompute:
    # Recompute the FOV if needed (the player moved or something has changed the FOV)
    fov_recompute = False
    libtcod.map_compute_fov(fov_map, player.x, player.y, TORCH_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)

  for y in range(MAP_HEIGHT):
    for x in range(MAP_WIDTH):
      visible = libtcod.map_is_in_fov(fov_map, x, y)
      wall = map[x][y].block_sight
      if not visible:
        # This means it's outside of the player's FOV
        if map[x][y].explored:
          # Only render tiles outside FOV if they've been explored.
          if wall:
            libtcod.console_set_char_background(con, x, y, color_dark_wall, libtcod.BKGND_SET)
          else:
            libtcod.console_set_char_background(con, x, y, color_dark_ground, libtcod.BKGND_SET)
      else:
        # This means it's visible
        if wall:
          libtcod.console_set_char_background(con, x, y, color_light_wall, libtcod.BKGND_SET)
        else:
          libtcod.console_set_char_background(con, x, y, color_light_ground, libtcod.BKGND_SET)
        # It is visible, and as such, has been explored.
        map[x][y].explored = True

  # Draw all objects in the object list.
  for object in objects:
    if object != player:
      object.draw()
    player.draw()

  # Blit the contents of 'con' to the root console.
  libtcod.console_blit(con, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)

  # Show the Player's stats
  libtcod.console_set_default_foreground(con, libtcod.white)
  libtcod.console_print_ex(0, 1, SCREEN_HEIGHT - 2, libtcod.BKGND_NONE, libtcod.LEFT,
        'HP: ' + str(player.fighter.hp) + '/' + str(player.fighter.max_hp))


#############################################
# Initialization & Main Loop
#############################################

libtcod.console_set_custom_font(b'arial10x10.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, b'python/libtcod tutorial', False)
con = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)

# Create the Player
fighter_component = Fighter(hp = 30, defense = 2, power = 5, death_function = player_death)
player = Object(0, 0, '@', 'player', libtcod.white, blocks=True, fighter = fighter_component)

# The List of Objects
objects = [player]

# Make the Map
make_map()

# Create the FOV map, in accordance with the established Map
fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
for y in range(MAP_HEIGHT):
  for x in range(MAP_WIDTH):
    libtcod.map_set_properties(fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked)

# Some initialization variables.
fov_recompute = True
game_state = 'playing'
player_action = None

while not libtcod.console_is_window_closed():
  # Render the screen.
  render_all()

  libtcod.console_flush()

  for object in objects:
    object.clear()

  #handle keys and exit game if needed
  player_action = handle_keys()
  if player_action == 'exit':
    break

  #let monsters take their turn
  if game_state == 'playing' and player_action != 'didnt-take-turn':
    for object in objects:
      if object.ai:
        object.ai.take_turn()
