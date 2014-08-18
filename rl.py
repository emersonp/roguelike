import libtcodpy as libtcod
import math
import textwrap

#############################################
# Constants and Big Vars
#############################################

# Testing State
TESTING = True

# Size of the window
SCREEN_WIDTH = 100
SCREEN_HEIGHT = 70

# Size of the Map
MAP_WIDTH = 100
MAP_HEIGHT = 63

# GUI Constants
BAR_WIDTH = 20
PANEL_HEIGHT = 7
PANEL_Y = SCREEN_HEIGHT - PANEL_HEIGHT
MSG_X = BAR_WIDTH + 2
MSG_WIDTH = SCREEN_WIDTH - BAR_WIDTH - 2
MSG_HEIGHT = PANEL_HEIGHT - 1

# Rooms
ROOM_MAX_SIZE = 13
ROOM_MIN_SIZE = 6
MAX_ROOMS = 200
MAX_ROOM_MONSTERS = 3
MAX_ROOM_ITEMS = 2

# Inventory
INVENTORY_WIDTH = 50

# Magic
CONFUSE_NUM_TURNS = 10
CONFUSE_RANGE = 8
FIREBALL_RADIUS = 3
FIREBALL_DAMAGE = 12
HEAL_AMOUNT = 4
LIGHTNING_DAMAGE = 20
LIGHTNING_RANGE = 5

# Field of Vision
FOV_ALGO = 0
FOV_LIGHT_WALLS = True
TORCH_RADIUS = 10

LIMIT_FPS = 20  # 20 frames-per-second maximum

# Colors of Terrain
color_dark_wall = libtcod.Color(0, 0, 100)
color_light_wall = libtcod.Color(130, 110, 50)
color_dark_ground = libtcod.Color(50, 50, 150)
color_light_ground = libtcod.Color(200, 180, 50)

# Python 3 Global Vars
map = []
objects = []
game_msgs = []


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

class ConfusedMonster:
  # AI for a temporarily Confused Monster
  def __init__(self, old_ai, num_turns = CONFUSE_NUM_TURNS):
    self.old_ai = old_ai
    self.num_turns = num_turns

  def take_turn(self):
    if self.num_turns > 0: # Monster still confused
      # Move in a random direction, and decrease num_turns confused.
      self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))
      self.num_turns -= 1
    else: # Restore the previous AI and destroy this one.
      self.owner.ai = self.old_ai
      message('The ' + self.owner.name + ' is no longer confused!')

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
      message(self.owner.name.capitalize() + ' attacks ' + target.name + ' for ' + str(damage) + ' hit points.')
      target.fighter.take_damage(damage)
    else:
      message(self.owner.name.capitalize() + ' attacks ' + target.name + 'but it has no effect!')

  def heal(self, amount):
    # Heal by the given amount, without going over the maximum.
    self.hp += amount
    if self.hp > self.max_hp:
      self.hp = self.max_hp

  def take_damage(self, damage):
    # Apply damage if possible.
    if damage > 0:
      self.hp -= damage
      # Check for death. If there's a death function, call it.
      if self.hp <= 0:
        function = self.death_function
        if function is not None:
          function(self.owner)

class Item:
# An item that can be picked up and used.
  def __init__(self, use_function = None):
    self.use_function = use_function
  def drop(self):
    # Add item to the map @ player's coordinates, and remove from the player's inventory.
    objects.append(self.owner)
    inventory.remove(self.owner)
    self.owner.x = player.x
    self.owner.y = player.y
    message('You dropped a ' + self.owner.name + '.', libtcod.yellow)
  def pick_up(self):
    # Add to the player's inventory and remove from the map.
    if len(inventory) >= 26:
      message('Your inventory is full, cannot pick up ' + self.owner.name + '.', libtcod.red)
    else:
      inventory.append(self.owner)
      objects.remove(self.owner)
      message('You picked up a ' + self.owner.name + '!', libtcod.green)
  def use(self):
    #just call the "use_function" if it is defined
    if self.use_function is None:
      message('The ' + self.owner.name + ' cannot be used.')
    else:
      if self.use_function() != 'cancelled':
        # Destroy after use, unless it was cancelled for some reason.
        inventory.remove(self.owner)

class Object:
  # This object is a generic item in game: player, monster, item, tile feature
  # An object is always represented as a symbol on screen.
  def __init__(self, x, y, char, name, color, blocks = False, fighter = None, ai = None, item = None):
    self.x = x
    self.y = y
    self.char = char
    self.name = name
    self.color = color
    self.blocks = blocks
    # If there's a fighter component, set parent for component.
    self.fighter = fighter
    if self.fighter:
      self.fighter.owner = self
    # If there's an AI component, set parent for component.
    self.ai = ai
    if self.ai:
      self.ai.owner = self
    # If there's an Item component, set parent for component.
    self.item = item
    if self.item:
      self.item.owner = self

  def clear(self):
    # Erase the character that represents this object.
    libtcod.console_put_char(con, self.x, self.y, ' ', libtcod.BKGND_NONE)

  def distance(self, x, y):
    # Return the distance to some coordinates.
    return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)

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

def cast_confuse():
  # Ask the player for a target to confuse.
  message('Left-click an enemy to confuse it, or right-click to cancel.', libtcod.light_cyan)
  monster = target_monster(CONFUSE_RANGE)
  if monster is None:
    return 'cancelled'
  # Replace the monster's AI with a "confused" one; after some turns it will restore the old AI.
  old_ai = monster.ai
  monster.ai = ConfusedMonster(old_ai)
  monster.ai.owner = monster # Tell the new component who owns it.
  message('The eyes of the ' + monster.name + ' look vacant, as it starts to stumble around!', libtcod.light_green)

def cast_fireball():
  # Ask the player for a target tile to throw a fireball at.
  message('Left-click a target tile for the fireball, or right-click to cancel.', libtcod.light_cyan)
  (x, y) = target_tile()
  if x is None:
    return 'cancelled'
  message('The fireball explodes, burning everything within ' + str(FIREBALL_RADIUS) + ' tiles!', libtcod.orange)
  # Damage every fighter-object in range, including the player.
  for obj in objects:
    if obj.distance(x, y) <= FIREBALL_RADIUS and obj.fighter:
      message('The ' + obj.name + ' gets burned for ' + str(FIREBALL_DAMAGE) + ' hit points.', libtcod.orange)
      obj.fighter.take_damage(FIREBALL_DAMAGE)

def cast_heal():
  # Heal the player
  if player.fighter.hp == player.fighter.max_hp:
    message('You are already at full health.', libtcod.red)
    return 'cancelled'
  message('Your wounds start to feel better!', libtcod.light_violet)
  player.fighter.heal(HEAL_AMOUNT)

def cast_lightning():
  # Find closest enemy (inside a maximum range) and damage it.
  monster = closest_monster(LIGHTNING_RANGE)
  if monster is None:  # No enemy found within maximum range.
    message('No enemy is close enough to strike.', libtcod.red)
    return 'cancelled'
  # Zap it!
  message('A lighting bolt strikes the ' + monster.name + ' with a loud thunder! The damage is ' + str(LIGHTNING_DAMAGE) + ' hit points.', libtcod.light_blue)
  monster.fighter.take_damage(LIGHTNING_DAMAGE)

def closest_monster(max_range):
  # Find closest enemy, up to a maximum range, and in the player's FOV.
  closest_enemy = None
  closest_dist = max_range + 1 # Start with (slightly more than) maximum range.
  for object in objects:
    if object.fighter and not object == player and libtcod.map_is_in_fov(fov_map, object.x, object.y):
      # Calculate distance between this object and the player.
      dist = player.distance_to(object)
      if dist < closest_dist:  # It's closer, so remember it.
        closest_enemy = object
        closest_dist = dist
  return closest_enemy

def create_h_tunnel(x1, x2, y):
  global map
  for x in range(min(x1, x2), max(x1, x2) + 1):
    map[x][y].blocked = False
    map[x][y].block_sight = False

def create_room(room):
  global map, objects
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

def get_names_under_mouse():
  global mouse

  # Return a string with the names of all objects under the mouse
  (x, y) = (mouse.cx, mouse.cy)
  # Create a list with the names of all objects at the mouse's coordinates and in FOV.
  names = [obj.name for obj in objects
    if obj.x == x and obj.y == y and libtcod.map_is_in_fov(fov_map, obj.x, obj.y)]

  names = ', '.join(names)  # Join the names, separated by commas.
  return names.capitalize()

def handle_keys():
  global fov_recompute
  global inventory
  global key
  global player

  if key.vk == libtcod.KEY_ENTER and key.lalt:
    #Alt + Enter: Toggle Fullscreen
    libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

  elif key.vk == libtcod.KEY_ESCAPE:
    return 'exit'  # Exit Game

  # Game State Keys
  if game_state == 'playing':
    # Movement keys
    if key.vk == libtcod.KEY_UP:
      player_move_or_attack(0, -1)
    elif key.vk == libtcod.KEY_DOWN:
      player_move_or_attack(0, 1)
    elif key.vk == libtcod.KEY_LEFT:
      player_move_or_attack(-1, 0)
    elif key.vk == libtcod.KEY_RIGHT:
      player_move_or_attack(1, 0)
    else:
      # Test for other keys.
      key_char = chr(key.c)
      # Pick up an item.
      if key_char == 'g':
        # Look for an item in the player's tile.
        for object in objects:
          if object.x == player.x and object.y == player.y and object.item:
            object.item.pick_up()
            break
      if key_char == 'i':
      # Show the inventory.
        chosen_item = inventory_menu('Press the key next to an item to use it, or any other to cancel.\n')
        if chosen_item is not None:
          chosen_item.use()
      if key_char == 'd':
        # sShow the inventory; if an item is selected, drop it.
        chosen_item = inventory_menu('Press the key next to an item to drop it, or any other to cancel.\n')
        if chosen_item is not None:
          chosen_item.drop()

      return 'didnt-take-turn'

def initialize_fov():
  global fov_recompute, fov_map
  fov_recompute = True
  # Create the FOV map, in accordance with the established Map
  fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
  for y in range(MAP_HEIGHT):
    for x in range(MAP_WIDTH):
      libtcod.map_set_properties(fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked)
  # Clear Console
  libtcod.console_clear(con)

def inventory_menu(header):
  # Show a menu with each item of the inventory as an option.
  if len(inventory) == 0:
    options = ['Inventory is empty.']
  else:
    options = [item.name for item in inventory]
  index = menu(header, options, INVENTORY_WIDTH)
  # If an item was chosen, return it.
  if index is None or len(inventory) == 0:
    return None
  return inventory[index].item

def is_blocked(x, y):
  global objects
  # First, test if the map tile is blocking.
  if map[x][y].blocked:
    return True
  # Now check to see if there are any blocking objects.
  for object in objects:
    if object.blocks and object.x == x and object.y == y:
      return True
  # Otherwise, not blocked.
  return False

def main_menu():
  img = libtcod.image_load(b'menu_background1.png')
  while not libtcod.console_is_window_closed():
    # Show the background image at twice the regular resolution.
    libtcod.image_blit_2x(img, 0, 0, 0)
    # Show the game's title and credits.
    libtcod.console_set_default_foreground(0, libtcod.light_yellow)
    libtcod.console_print_ex(0, SCREEN_WIDTH//2, SCREEN_HEIGHT//2-4, libtcod.BKGND_NONE, libtcod.CENTER, 'TOMBS OF NEW BEGINNINGS')
    libtcod.console_print_ex(0, SCREEN_WIDTH//2, SCREEN_HEIGHT-2, libtcod.BKGND_NONE, libtcod.CENTER, 'By Parker Harris Emerson')
    # Show options and wait for the player's choice.
    choice = menu('', ['Play a new game', 'Continue last game', 'Quit'], 24)
    if choice == 0: # New Game
      new_game()
      play_game()
    elif choice == 2: # Quit
      break

def make_map():
  global map, player, objects
  # The List of Objects
  objects = [player]
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
        if TESTING:
          message('Player: ' + str(new_x) + '/' + str(new_y))
          message('Room UL: ' + str(new_room.x1) + '/' + str(new_room.y1))
          message('Room LR: ' + str(new_room.x2) + '/' + str(new_room.y2))
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

def message(new_msg, color = libtcod.white):
  # Split the message along multiple lines if necessary.
  new_msg_lines = textwrap.wrap(new_msg, MSG_WIDTH)
  for line in new_msg_lines:
  # If the buffer is full, remove the first line to make room for the new one
    if len(game_msgs) == MSG_HEIGHT:
      del game_msgs[0]
    # Add the new line as a tuple, with the text and the color.
    game_msgs.append( (line, color) )

def monster_death(monster):
  # Transform monster into a corpse! Corpses don't block, can't be attacked and don't move.
  message(monster.name.capitalize() + ' is dead!', libtcod.orange)
  monster.char = '%'
  monster.color = libtcod.dark_red
  monster.blocks = False
  monster.fighter = None
  monster.ai = None
  monster.name = 'remains of ' + monster.name
  monster.send_to_back()

def menu(header, options, width):
  if len(options) > 26:
    raise ValueError('Cannot have a menu with more than 26 options.')
  # calculate total height for the header (after auto-wrap) WITH one line per option.
  header_height = libtcod.console_get_height_rect(con, 0, 0, width, SCREEN_HEIGHT, header)
  if header == '':
        header_height = 0
  height = len(options) + header_height
  # Create an off-screen console that represents the menu's window.
  window = libtcod.console_new(width, height)
  # Print the header, with auto-wrap
  libtcod.console_set_default_foreground(window, libtcod.white)
  libtcod.console_print_rect_ex(window, 0, 0, width, height, libtcod.BKGND_NONE, libtcod.LEFT, header)
  # Print all the options.
  y = header_height
  letter_index = ord('a')
  for option_text in options:
    text = '(' + chr(letter_index) + ') ' + option_text
    libtcod.console_print_ex(window, 0, y, libtcod.BKGND_NONE, libtcod.LEFT, text)
    y += 1
    letter_index += 1
  # Blit the contents of "window" to the root console.
  x = SCREEN_WIDTH//2 - width//2
  y = SCREEN_HEIGHT//2 - height//2
  libtcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 0.7)
  # Present the root console to the player and wait for a key-press.
  libtcod.console_flush()
  key = libtcod.console_wait_for_keypress(True)
  if key.vk == libtcod.KEY_ENTER and key.lalt:  #(special case) Alt+Enter: toggle fullscreen
    libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
  # Convert the ASCII code to an index; if it corresponds to an option, return it.
  index = key.c - ord('a')
  if index >= 0 and index < len(options):
    return index
  return None

def new_game():
  global game_msgs, game_state
  global inventory
  global player
  # Create the Player
  fighter_component = Fighter(hp = 30, defense = 2, power = 5, death_function = player_death)
  player = Object(0, 0, '@', 'player', libtcod.white, blocks=True, fighter = fighter_component)
  # Make the Map
  make_map()
  initialize_fov()
  # Set Game State
  game_state = 'playing'
  # Create Inventory
  inventory = []
  # Create a list of game messages and their color.
  game_msgs = []
  # A warm welcoming message!
  message('Welcome stranger! Prepare to perish in the Tombs of New Beginnings.', libtcod.red)

def place_objects(room):
  global objects
  # Choose a random number of monsters.
  num_monsters = libtcod.random_get_int(0, 0, MAX_ROOM_MONSTERS)

  for i in range(num_monsters):
    # Choose a random spot for each given monster.
    x = libtcod.random_get_int(0, room.x1 + 1, room.x2 - 1)
    y = libtcod.random_get_int(0, room.y1 + 1, room.y2 - 1)

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

  # Choose random number of items.
  num_items = libtcod.random_get_int(0, 0, MAX_ROOM_ITEMS)
  for i in range(num_items):
    # Choose random spot for this item.
    x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
    y = libtcod.random_get_int(0, room.y1+1, room.y2-1)
    # Only place it if the tile is not blocked.
    if not is_blocked(x, y):
      item_dice = libtcod.random_get_int(0, 0, 100)
      if item_dice < 70:
        # Create a healing potion.
        item_component = Item(use_function = cast_heal)
        item = Object(x, y, '!', 'healing potion', libtcod.violet, item = item_component)
      elif item_dice < 70 + 10:
        # Create a lightning bolt scroll.
        item_component = Item(use_function = cast_lightning)
        item = Object(x, y, '#', 'scroll of lightning bolt', libtcod.light_yellow, item = item_component)
      elif item_dice < 70 + 20:
        # Create a confuse scroll.
        item_component = Item(use_function = cast_confuse)
        item = Object(x, y, '#', 'scroll of confusion', libtcod.light_yellow, item=item_component)
      else:
        # Create a fireball scroll.
        item_component = Item(use_function = cast_fireball)
        item = Object(x, y, '#', 'scroll of fireball', libtcod.light_yellow, item=item_component)
      # Add item to all objects on map.
      objects.append(item)
      item.send_to_back()  # Items appear below other objects.

def play_game():
  global key, mouse, objects
  player_action = None
  mouse = libtcod.Mouse()
  key = libtcod.Key()
  # Play Game
  while not libtcod.console_is_window_closed():
    # Render the screen.
    libtcod.sys_check_for_event( libtcod.EVENT_KEY_PRESS | libtcod.EVENT_MOUSE, key, mouse)
    render_all()
    libtcod.console_flush()
    for object in objects:
      object.clear()
    # Handle key input and exit game if needed.
    player_action = handle_keys()
    if player_action == 'exit':
      break
    # Let the monsters take their turn.
    if game_state == 'playing' and player_action != 'didnt-take-turn':
      for object in objects:
        if object.ai:
          object.ai.take_turn()

def player_death(player):
  # Player dead. The game ended!
  global game_state
  message('You died!', libtcod.red)
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

  # Prepare to render the GUI panel.
  libtcod.console_set_default_background(panel, libtcod.black)
  libtcod.console_clear(panel)

  # Print the game messages, one line at a time.
  y = 1
  for (line, color) in game_msgs:
    libtcod.console_set_default_foreground(panel, color)
    libtcod.console_print_ex(panel, MSG_X, y, libtcod.BKGND_NONE, libtcod.LEFT, line)
    y += 1

  # Show the player's stats.
  render_bar(1, 1, BAR_WIDTH, 'HP', player.fighter.hp, player.fighter.max_hp, libtcod.light_red, libtcod.darker_red)

  # Display names of objects under the mouse.
  libtcod.console_set_default_foreground(panel, libtcod.light_gray)
  libtcod.console_print_ex(panel, 1, 0, libtcod.BKGND_NONE, libtcod.LEFT, get_names_under_mouse())

  # Blit the contents of "panel" to the root console.
  libtcod.console_blit(panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)

def render_bar(x, y, total_width, name, value, maximum, bar_color, back_color):
  # Render a bar (e.g., HP, experience, etc). First; calculate the width of the bar:
  bar_width = int(float(value) / maximum * total_width)
  # Render the background color.
  libtcod.console_set_default_background(panel, back_color)
  libtcod.console_rect(panel, x, y, total_width, 1, False, libtcod.BKGND_SCREEN)
  # Now render the bar on top.
  libtcod.console_set_default_background(panel, bar_color)
  if bar_width > 0:
    libtcod.console_rect(panel, x, y, bar_width, 1, False, libtcod.BKGND_SCREEN)
  # Then, centered text with current and max values.
  libtcod.console_set_default_foreground(panel, libtcod.white)
  libtcod.console_print_ex(panel, x + total_width // 2, y, libtcod.BKGND_NONE, libtcod.CENTER, name + ': ' + str(value) + '/' + str(maximum))

def target_monster(max_range = None):
  # Returns a clicked monster within FOV and within a range, or None if right-clicked.
  while True:
    (x, y) = target_tile(max_range)
    if x is None: # Player cancelled
      return None
    # Return first clicked monster, otherwise keep looping.
    for obj in objects:
      if obj.x == x and obj.y == y and obj.fighter and obj != player:
        return obj

def target_tile(max_range = None):
  # Return the position of a tile left-clicked in player's FOV (optionally in a range), or (None, None) if right-clicked.
  global key, mouse
  while True:
    # Render the screen. This erases the inventory and shows the names of objects under the mouse.
    libtcod.console_flush()
    libtcod.sys_check_for_event( libtcod.EVENT_KEY_PRESS | libtcod.EVENT_MOUSE, key, mouse)
    render_all()
    (x, y) = (mouse.cx, mouse.cy)

    # Cancel if the player right-clicked or pressed Escape.
    if mouse.rbutton_pressed or key.vk == libtcod.KEY_ESCAPE:
      return (None, None)

    # Accept if the player clicked in FOV, and in range if applicable.
    if (mouse.lbutton_pressed and libtcod.map_is_in_fov(fov_map, x, y) and (max_range is None or player.distance(x, y) <= max_range)):
      return (x, y)

#############################################
# Initialization of Main Loop
#############################################

libtcod.console_set_custom_font(b'arial12x12.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, b'python/libtcod tutorial', False)
libtcod.sys_set_fps(LIMIT_FPS)
con = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)
panel = libtcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)

main_menu()
