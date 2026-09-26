"""RAM addresses for The Legend of Zelda (NES). Sources: Data Crystal, ROM Detectives.

The encoding notes matter more than the addresses. Several of these bytes are not
what their name suggests:
  $0656 selected item SLOT (a cursor, not an acquisition - do not treat it as one)
  $0657 sword level       0/1/2/3
  $0658 bombs             a real count
  $0659 arrow STATUS      0 none / 1 arrow / 2 silver arrow
  $065B candle STATUS     0 none / 1 blue / 2 red
  $065D bait              Data Crystal: "Food in Inventory"; a count
  $0662 ring STATUS       0 none / 1 blue / 2 red
  $0667 compass           one bit PER LEVEL, not a 0/1 flag
  $0668 map               one bit PER LEVEL, not a 0/1 flag
  $066F hearts            low nybble = hearts filled, high nybble = containers - 1
  $0670 partial heart     $00 empty / $01-$7F half / $80-$FF full
  $0671 Triforce          one bit per piece

https://datacrystal.tcrf.net/wiki/The_Legend_of_Zelda/RAM_map is Cloudflare-gated
for scripted access; a readable snapshot:
http://web.archive.org/web/20251116061046/https://datacrystal.tcrf.net/wiki/The_Legend_of_Zelda/RAM_map
"""

GAME_MODE      = 0x12   # see MODE_* below
SUBMODE        = 0x13
LEVEL          = 0x10   # 0 overworld, 1..9 dungeons
FRAME_COUNTER  = 0x15
ROOM           = 0xEB   # screen id, row in high nybble, column in low nybble
ROOM_DEST      = 0xEC
LINK_X         = 0x70
LINK_Y         = 0x84
LINK_DIR       = 0x98   # 1 right, 2 left, 4 down, 8 up
ENEMY_X        = 0x71   # 0x71..0x7B
ENEMY_Y        = 0x85   # 0x85..0x8F
ENEMY_TYPES    = 0x350  # 0x350..0x35B
ENEMY_HP       = 0x485  # 0x485..0x48F (high nybble)
LINK_ANIM      = 0xAC
SWORD_STATE    = 0xB9
PAUSED         = 0xE0
SCROLL_DIR     = 0xE8
KILL_TALLY     = 0x50
RETURN_ROOM    = 0x526

B_ITEM         = 0x656
SWORD          = 0x657  # 0 none, 1 wood, 2 white, 3 magical
BOMBS          = 0x658
ARROWS         = 0x659   # 0 none / 1 arrow / 2 silver arrow - a status, not a count
BOW            = 0x65A
CANDLE         = 0x65B   # 0 none / 1 blue / 2 red
WHISTLE        = 0x65C
BAIT           = 0x65D   # Data Crystal calls this "Food in Inventory"
POTION         = 0x65E
ROD            = 0x65F
RAFT           = 0x660
BOOK           = 0x661
RING           = 0x662
LADDER         = 0x663
MAGIC_KEY      = 0x664
BRACELET       = 0x665
LETTER         = 0x666
COMPASS        = 0x667   # one bit per level, not a 0/1 flag
MAP            = 0x668   # one bit per level, not a 0/1 flag
COMPASS_L9     = 0x669   # level-9 compass and map are separate bytes
MAP_L9         = 0x66A
CLOCK          = 0x66C
RUPEES         = 0x66D
KEYS           = 0x66E
HEARTS         = 0x66F  # high nybble = containers - 1, low nybble = full hearts
HEART_FRAC     = 0x670
TRIFORCE       = 0x671  # bit flags, one per dungeon
BOOMERANG      = 0x674
MAGIC_BOOMERANG= 0x675
MAGIC_SHIELD   = 0x676
MAX_BOMBS      = 0x67C

MODE_TITLE      = 0x00
MODE_SELECT     = 0x01
MODE_TRANSITION = 0x02
MODE_WIPE       = 0x03
MODE_STAIRS_OUT = 0x04
MODE_NORMAL     = 0x05
MODE_PRE_SCROLL = 0x06
MODE_SCROLLING  = 0x07
MODE_GROTTO_EXIT= 0x0A
MODE_GROTTO     = 0x0B
MODE_REGISTER   = 0x0E  # observed: register-your-name screen (Data Crystal lists these two swapped)
MODE_ELIMINATION= 0x0F
MODE_STAIRS_IN  = 0x10

DIR_RIGHT, DIR_LEFT, DIR_DOWN, DIR_UP = 1, 2, 4, 8

START_ROOM = 0x77
