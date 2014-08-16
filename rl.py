# Copyright (c) 2014 Parker Harris Emerson
# My first roguelike

# Imports
import libtcodpy as libtcod

# Constants
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50
LIMIT_FPS = 20

# Set Font
libtcod.console_set_custom_font(b'arial10x10.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)

# Initialize Window
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, b'Roguelike!', False)



# Main Loop of Game
while not libtcod.console_is_window_closed():
  libtcod.console_set_default_foreground(0, libtcod.white)
  libtcod.console_put_char(0, 1, 1, '@', libtcod.BKGND_NONE)
  libtcod.console_flush()
