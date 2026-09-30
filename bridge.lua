-- bridge.lua : runs inside EmuHawk. Connects to the Python controller over TCP
-- and executes newline-delimited commands, replying one line per command.
--
-- Commands:
--   ping                        -> pong
--   step <n> <buttons>          -> hold <buttons> (comma list or "-") for n frames, reply state
--   state                       -> reply state
--   ram <addr> <len>            -> hex bytes of main RAM
--   save <path> | load <path>   -> savestate to/from file
--   screenshot <path>           -> png
--   fast | normal               -> unthrottle / throttle
--   reset                       -> power-cycle core
--   quit                        -> exit EmuHawk

local socket = require("socket.core")

local port = tonumber(userdata.get("port") or 0)
if not port or port == 0 then
  local f = io.open("G:/AI World Record/harness/.bridge_port", "r")
  if f then port = tonumber(f:read("*l")); f:close() end
end
assert(port and port > 0, "bridge: no port given")

local conn = socket.tcp()
conn:settimeout(15)
local ok, err = conn:connect("127.0.0.1", port)
assert(ok, "bridge: connect failed: " .. tostring(err))
conn:setoption("tcp-nodelay", true)
conn:settimeout(0.05)
console.log("bridge: connected on port " .. port)

-- Ordered list of RAM fields reported in every state line.
local FIELDS = {
  {"mode",     0x12},  -- game mode (5 = normal play, 7 = scrolling, 0xB = cave, ...)
  {"sub",      0x13},  -- routine index / submode
  {"level",    0x10},  -- 0 = overworld, 1-9 dungeon
  {"room",     0xEB},  -- screen id: high nybble row, low nybble col
  {"x",        0x70},  -- Link X
  {"y",        0x84},  -- Link Y
  {"dir",      0x98},  -- Link facing (1 R, 2 L, 4 D, 8 U)
  {"hp",       0x66F}, -- hi nybble = containers-1, lo nybble = full hearts
  {"hpfrac",   0x670},
  {"rupees",   0x66D},
  {"keys",     0x66E},
  {"bombs",    0x658},
  {"sword",    0x657},
  {"bitem",    0x656},
  {"triforce", 0x671},
  {"paused",   0xE0},
  {"scroll",   0xE8},
  {"retroom",  0x526},
  {"anim",     0xAC},
  {"kills",    0x50},
}

local BUTTONS = {"Up","Down","Left","Right","Select","Start","B","A"}
TRACE = false

-- Boss health. ObjType $34F, ObjHP $485, both indexed by object slot (0 = Link), 12 slots.
--
-- A boss is "present" when a slot carries one of the boss object types, or - the awkward part - when
-- a slot has NO type but live HP, which is what a Gleeok neck segment looks like (InitGleeok writes
-- them with object type 0 and the comment "these aren't independent objects in the object slots").
-- Summing both is the only way to get Gleeok's real health: head 10 plus six segments at 10 is 70,
-- not 10.
--
-- The type list is zelda/boss.py's GLEEOK_TYPES, not a guess. That is FOUR UpdateGleeok variants
-- (0x42-0x45, one per head count) plus 0x46, the head that comes loose when its neck is cut and
-- goes on flying and spitting. The first version of this file listed only 0x43 and 0x44, so most
-- of the boss was never counted and the denominator could not match the parts on screen.
--
-- BOSS_TYPES are the ones worth a bar, and the value is the name to print. Names come from the
-- harness's own enemy table (zelda/overworld.py ENEMY_NAMES) so the HUD and the log cannot drift
-- apart. Gleeok's segments have no name of their own - the fight is the head, the neck is body - so
-- they carry the same one and are counted as parts separately.
local GLEE0K = "GLEEOK"     -- an E. The zero in "GLEE0K" was a typo, and it was on screen a lot.
local BOSS_TYPES = {
  [0x32] = "DODONGO",
  [0x33] = "GOHMA",
  [0x34] = "GOHMA",
  [0x36] = "DIGDOGGER",
  [0x38] = "DIGDOGGER",
  [0x3C] = "MANHANDLA",
  [0x42] = GLEE0K,
  [0x43] = GLEE0K,
  [0x44] = GLEE0K,
  [0x45] = GLEE0K,
  [0x46] = GLEE0K,
}
-- UpdateGleeokHead, the loose head. Worth its own colour: it is the only part that chases Link
-- across the room, so "is that amber cell still up" is the question the fight is actually asking.
local LOOSE_HEAD = 0x46

local boss_seen = 0        -- the peak HP a boss has shown, so the bar has a denominator
local hud = { attempt = 0 }  -- set by the Python side, so the HUD can count attempts itself

-- One read of the object table, shared by everything that needs it. This was duplicated: boss_hud()
-- scanned the table for the cells and then called boss_hp() to scan it again for the total, so the
-- bar and the number beside it could disagree within one frame, and the table was read 22 times a
-- frame instead of 11. Returns slot -> {type, hits}, the total in hits, and the name to print.
local function scan()
  local parts, hits, name = {}, 0, nil
  for i = 1, 11 do
    local t = mainmemory.read_u8(0x34F + i)
    local h = mainmemory.read_u8(0x485 + i)
    if h > 0 and (BOSS_TYPES[t] or t == 0) then
      -- HP is stored as a nybble pair: the harness reads ObjHP >> 4 for a hit count, so a $A0 slot
      -- is 10 hits, not 160. The first version of this HUD printed the raw byte and the total came
      -- out "1136/1376" - unreadable, and unauditable, because it was wrong. 1136/16 is 71 and
      -- 1376/16 is 86: whole hit counts, which is the first reason to trust the number at all.
      local n = math.floor(h / 16)
      if n > 0 then
        parts[i] = { t = t, hp = n }
        hits = hits + n
        -- An untyped slot is neck and has no name of its own; the named type wins, so a Gleeok reads
        -- GLEEOK rather than whatever the segments would claim.
        if BOSS_TYPES[t] then name = BOSS_TYPES[t] end
      end
    end
  end
  return parts, hits, name
end

-- Where boss parts stand, and how much of them is left. ObjType $34F, ObjHP $485, indexed by slot.
local function boss_hp()
  local _, hits = scan()
  if hits == 0 then
    boss_seen = 0
    return 0, 0
  end
  -- The peak is remembered rather than recomputed, because a boss that is already half killed when
  -- the window opened has no "full" value left to read off anywhere. It is remembered in HITS, and
  -- it only clears when the room has no boss part left at all - which is what made the first version
  -- read 1280, 1376 and 1312 in three windows at the same moment: each scout's denominator was set
  -- by whichever frame that particular window happened to open on.
  if hits > boss_seen then boss_seen = hits end
  return hits, boss_seen
end

local function boss_hud()
  -- A strip across the WHOLE bottom of the screen, one cell per boss object slot, rather than
  -- numbers in a corner. The owner tried the text version and could not read it: "the numbers and
  -- the high speed makes it hard to see." That is the right objection - a fight is watched
  -- peripherally, and a number you have to read is a number you miss. A shape you count at a glance
  -- is not.
  --
  -- So: the bottom of the screen is divided into eleven cells, one per object slot, and each cell
  -- fills left to right with the health of the part standing in it. The strip empties as the neck
  -- comes apart, which is the shape of the fight, and the attempt counter rides underneath it where
  -- there is no room to miss it.
  --
  -- Colour carries the state so the strip is readable without reading: red is a live part, amber is
  -- the loose head, near-black is a slot with nothing in it.
  --
  -- The geometry is deliberate and was wrong twice. The NES screen is 256x240; the first attempt
  -- started the strip at y=226 with 14 rows of bar plus a text line, which put the text at y=245 -
  -- five rows below the bottom of the screen, where the emulator happily renders into the frame
  -- buffer and nobody ever sees it. So the whole thing is laid out from the top down against 240:
  -- bar at 218 (10 rows, ending 228), the total-width line at 230, text at 232. 11 cells of 23px
  -- is 253, so it spans the width without running off the right edge.
  local SLOTS, W, H, Y = 11, 23, 10, 218
  local parts, hits, name = scan()
  if hits == 0 then
    return
  end
  if hits > boss_seen then boss_seen = hits end
  local seen = boss_seen

  -- A part fills its cell relative to the fullest part alive, not relative to the whole boss, so
  -- the cells stay comparable to each other as the fight goes on.
  local full = 1
  for _, p in pairs(parts) do
    if p.hp > full then full = p.hp end
  end

  for i = 1, SLOTS do
    local x = (i - 1) * W
    local p = parts[i]
    if p then
      local w = math.max(2, math.floor((W - 3) * p.hp / full))
      local col = (p.t == LOOSE_HEAD) and 0xFFFFA030 or 0xFFFF3030
      gui.drawRectangle(x, Y, x + W - 3, Y + H - 1, 0xFF201820)
      gui.drawRectangle(x + 1, Y + 1, x + 1 + w, Y + H - 1, col)
      -- a white pip on a part that is nearly dead, so "almost" is visible and not just "shorter"
      if p.hp * 2 <= full then
        gui.drawRectangle(x + 1 + w, Y + 1, x + 1 + w + 1, Y + H - 1, 0xFFFFFFFF)
      end
    else
      gui.drawRectangle(x, Y, x + W - 3, Y + H - 1, 0xFF182038)
    end
  end
  -- total remaining, as a width under the strip: the one number worth having, in the one place it
  -- can be read without looking away from the fight
  local frac = seen > 0 and (hits / seen) or 0
  local w = math.max(1, math.floor(255 * frac))
  gui.drawRectangle(0, Y + H + 1, w, Y + H + 2, 0xFF40C0FF)
  gui.drawString(2, Y + H + 4,
                 string.format("%s  ATT %d  %d/%d", name or "BOSS", hud.attempt, hits, seen),
                 0xFF40C0FF, 0xFF000000)
end

local function state_str()
  local p = {"frame=" .. emu.framecount()}
  for _, f in ipairs(FIELDS) do
    p[#p+1] = f[1] .. "=" .. mainmemory.read_u8(f[2])
  end
  -- Boss health, as a fraction of the whole thing rather than one object's HP, because most bosses
  -- are more than one object. Gleeok is the case that forces it: the head is 10 HP in a normal slot,
  -- and six neck segments are 10 HP each in slots whose object TYPE is 0 - which is why read_enemies
  -- in the Python side never saw them, and why the whole fight was modelled as a 10 HP boss.
  -- So: sum the HP of the live boss slots, divide by what was there when the boss appeared.
  --
  -- bhp/bmax are 0 when no boss is present. They are emitted for the recording trace only, so this
  -- costs two reads a frame and does not touch the live run's stepping.
  local bh, bm = boss_hp()
  p[#p+1] = "bhp=" .. bh
  p[#p+1] = "bmax=" .. bm
  p[#p+1] = "lag=" .. emu.lagcount()
  return table.concat(p, " ")
end

local function parse_buttons(s)
  local t = {}
  for _, b in ipairs(BUTTONS) do t[b] = false end
  if s and s ~= "-" then
    for b in string.gmatch(s, "[^,]+") do t[b] = true end
  end
  return t
end

local function tohex(arr)
  local out = {}
  for i = 0, #arr do
    if arr[i] ~= nil then out[#out+1] = string.format("%02x", arr[i]) end
  end
  return table.concat(out)
end

local function send(line)
  conn:settimeout(5)
  conn:send(line .. "\n")
  conn:settimeout(0.05)
end

local function handle(line)
  local cmd, rest = line:match("^(%S+)%s*(.*)$")
  if cmd == "ping" then
    send("pong")
  elseif cmd == "step" then
    local n, btn = rest:match("^(%d+)%s*(%S*)$")
    n = tonumber(n) or 1
    local t = parse_buttons(btn)
    -- Redraw the boss read-out on every step. The bridge holds the main thread waiting for
    -- commands, so there is no idle frame loop to draw from; `step` is the heartbeat - the Python
    -- side calls it constantly during a run and not at all when idle, which is exactly the cadence
    -- wanted. gui.clearGraphics first, because without it the previous frame's text stays put and
    -- the counter turns into a smear.
    gui.clearGraphics()
    boss_hud()
    if TRACE then
      local lines = {}
      for _ = 1, n do
        joypad.set(t, 1)
        emu.frameadvance()
        lines[#lines+1] = state_str()
      end
      send(table.concat(lines, ";"))
    else
      for _ = 1, n do
        joypad.set(t, 1)
        emu.frameadvance()
      end
      send(state_str())
    end
  elseif cmd == "trace" then
    TRACE = (rest == "on"); send("ok")
  elseif cmd == "state" then
    send(state_str())
  elseif cmd == "attempt" then
    -- The Python side sets this when a segment starts searching, so the in-emulator HUD can count
    -- attempts without the log having to be read. Sent per attempt rather than polled, because the
    -- search is the thing that is invisible while it is happening.
    hud.attempt = tonumber(rest) or 0
    send("ok")
  elseif cmd == "ram" then
    local a, l = rest:match("^(%d+)%s+(%d+)$")
    local arr = mainmemory.read_bytes_as_array(tonumber(a), tonumber(l))
    send(tohex(arr))
  elseif cmd == "ramd" then
    local dom, a, l = rest:match("^(%S+)%s+(%d+)%s+(%d+)$")
    local arr = memory.read_bytes_as_array(tonumber(a), tonumber(l), dom)
    send(tohex(arr))
  elseif cmd == "msave" then
    send(memorysavestate.savecorestate())                    -- in-RAM state, fast
  elseif cmd == "mload" then
    memorysavestate.loadcorestate(rest); send("ok")
  elseif cmd == "mfree" then
    memorysavestate.removestate(rest); send("ok")
  elseif cmd == "save" then
    savestate.save(rest, true); send("ok")
  elseif cmd == "load" then
    local r = savestate.load(rest, true); send(r and "ok" or "fail")
  elseif cmd == "screenshot" then
    client.screenshot(rest); send("ok")
  elseif cmd == "fast" then
    emu.limitframerate(false); client.SetSoundOn(false); send("ok")
  elseif cmd == "normal" then
    -- speed and sound are one switch here: fast() turns sound off to keep the
    -- search loop cheap, so coming back to realtime has to turn it on again or
    -- the run plays silent.
    emu.limitframerate(true); client.SetSoundOn(true); send("ok")
  elseif cmd == "sound" then
    client.SetSoundOn(rest == "1"); send("ok")
  elseif cmd == "frameskip" then
    -- draw only every Nth frame while searching: the emulation itself is untouched
    client.frameskip(tonumber(rest) or 0); send("ok")
  elseif cmd == "apikeys" then
    local names = {}
    for k, _ in pairs(_G[rest] or {}) do names[#names+1] = k end
    table.sort(names); send(table.concat(names, ","))
  elseif cmd == "reset" then
    client.reboot_core(); send(state_str())
  elseif cmd == "quit" then
    send("bye"); conn:close(); client.exit()
  else
    send("err unknown command: " .. tostring(cmd))
  end
end

client.unpause()
-- Block for commands. Yielding while idle lets the emulator free-run (frames advanced with no
-- input from us and broke replay determinism), so the script holds the main thread instead.
conn:settimeout(nil)
while true do
  local line, e = conn:receive("*l")
  if line then
    local okh, herr = pcall(handle, line)
    if not okh then send("err " .. tostring(herr)) end
  elseif e == "closed" then
    console.log("bridge: connection closed, exiting")
    client.exit()
    break
  end
end
