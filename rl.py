import libtcodpy as libtcod

#############################################
# Constants and Big Vars
#############################################

# Size of the window
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50

# Size of the Map
MAP_WIDTH = 80
MAP_HEIGHT = 45

# Colors of Terrain
color_dark_wall = libtcod.Color(0, 0, 100)
color_dark_ground = libtcod.Color(50, 50, 150)

map = []
#############################################
# Classes
#############################################

class Object:
  # This object is a generic item in game: player, monster, item, tile feature
  # An object is always represented as a symbol on screen.
  def __init__(self, x, y, char, color):
    self.x = x
    self.y = y
    self.char = char
    self.color = color

  def move(self, dx, dy):
    # Move object by the param amount
    self.x += dx
    self.y += dy

  def draw(self):
    # Set the color and then draw the corresponding character of the object in that color.
    libtcod.console_set_default_foreground(con, self.color)
    libtcod.console_put_char(con, self.x, self.y, self.char, libtcod.BKGND_NONE)

  def clear(self):
    # Erase the character that represents this object
    libtcod.console_put_char(con, self.x, self.y, ' ', libtcod.BKGND_NONE)

class Tile:
  # A tile on the map
  def __init__(self, blocked, block_sight = None):
    self.blocked = blocked
    # By default, if a tile is blocked, it also blocks sight.
    if block_sight == None:
      block_sight = blocked
    self.block_sight = block_sight


#############################################
# Functions
#############################################

def handle_keys():
  global playerx, playery

  #key = libtcod.console_check_for_keypress()  #real-time
  key = libtcod.console_wait_for_keypress(True)  #turn-based

  if key.vk == libtcod.KEY_ENTER and key.lalt:
    #Alt+Enter: toggle fullscreen
    libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

  elif key.vk == libtcod.KEY_ESCAPE:
    return True  #exit game

  #movement keys
  if libtcod.console_is_key_pressed(libtcod.KEY_UP):
    player.move(0, -1)
  elif libtcod.console_is_key_pressed(libtcod.KEY_DOWN):
    player.move(0, 1)
  elif libtcod.console_is_key_pressed(libtcod.KEY_LEFT):
    player.move(-1, 0)
  elif libtcod.console_is_key_pressed(libtcod.KEY_RIGHT):
    player.move(1, 0)

def make_map():
  global map

  # Fill the map with "unblocked" tiles.
  for x in range(MAP_WIDTH):
    map.append([])
    for y in range(MAP_HEIGHT):
      map[x].append(Tile(False))

  #map = [[ Tile(False)
  #  for y in range(MAP_HEIGHT) ]
  #    for x in range(MAP_WIDTH) ]

  # Place to Test Pillars to test the map.
  map[30][22].blocked = True
  map[30][22].block_sight = True
  map[40][22].blocked = True
  map[40][22].block_sight = True

def render_all():
  global color_dark_ground
  global color_dark_wall
  global map

  for y in range(MAP_HEIGHT):
    for x in range(MAP_WIDTH):
      wall = map[x][y].block_sight
      if wall:
        libtcod.console_set_char_background(con, x, y, color_dark_wall, libtcod.BKGND_SET)
      else:
        libtcod.console_set_char_background(con, x, y, color_dark_ground, libtcod.BKGND_SET)

  # Draw all objects in the object list.
  for object in objects:
    object.draw()

  # Blit the contents of 'con' to the root console.
  libtcod.console_blit(con, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)


#############################################
# Initialization & Main Loop
#############################################

libtcod.console_set_custom_font(b'arial10x10.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, b'python/libtcod tutorial', False)
con = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)

# Create the Player
player = Object(SCREEN_WIDTH//2, SCREEN_HEIGHT//2, '@', libtcod.white)

# Create an NPC
npc = Object(SCREEN_WIDTH//2 - 5, SCREEN_HEIGHT//2, '@', libtcod.yellow)

# The List of Objects
objects = [npc, player]

# Make the Map
make_map()

while not libtcod.console_is_window_closed():
  # Render the screen.
  render_all()

  libtcod.console_flush()

  for object in objects:
    object.clear()

  #handle keys and exit game if needed
  exit = handle_keys()
  if exit:
    break
