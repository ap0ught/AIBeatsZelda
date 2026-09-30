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
-- BOSS_TYPES are the ones worth a bar, and the value is the name to print. Names come from the
-- harness's own enemy table (zelda/overworld.py ENEMY_NAMES) so the HUD and the log cannot drift
-- apart. Gleeok's 0x44 neck segments have no name of their own - the fight is the head, the neck is
-- body - so they carry the same one and are counted as "parts" separately.
local BOSS_TYPES = {
  [0x32] = "DODONGO",
  [0x33] = "GOHMA",
  [0x34] = "GOHMA",
  [0x36] = "DIGDOGGER",
  [0x38] = "DIGDOGGER",
  [0x3C] = "MANHANDLA",
  [0x43] = "GLEE0K",
  [0x44] = "GLEE0K",
}

local boss_seen = 0        -- the peak HP a boss has shown, so the bar has a denominator
local hud = { attempt = 0 }  -- set by the Python side, so the HUD can count attempts itself

-- Where boss parts stand, and how much of them is left. Reads the object table directly rather than
-- going through the game: ObjType $34F, ObjHP $485, both indexed by slot.
local function boss_hp()
  local hp, mx = 0, 0
  for i = 1, 11 do
    local t = mainmemory.read_u8(0x34F + i)
    local h = mainmemory.read_u8(0x485 + i)
    if h > 0 and (BOSS_TYPES[t] or t == 0) then
      hp = hp + h
      if hp > mx then mx = hp end
    end
  end
  if hp == 0 then
    boss_seen = 0
    return 0, 0
  end
  -- The peak is remembered rather than recomputed from a table, because the peak is only knowable
  -- from having watched it: a boss that has already been half killed when the recording starts has
  -- no "full" value left to read off anywhere.
  if hp > boss_seen then boss_seen = hp end
  return hp, boss_seen
end

local function boss_hud()
  -- A live read-out in the lower-left of the emulator window, drawn by the client-side Lua that
  -- `--lua=` loads. It exists because the log was not enough: for most of a Gleeok search the only
  -- thing written anywhere was "attempt N: died (4439 frames)", which says how the fight ended and
  -- nothing about the fight. Boss HP, the number of neck segments still standing, and the attempt
  -- counter are the three numbers that turn watching it into reading it.
  --
  -- Drawn here rather than in the Python overlay because this is where the game is actually being
  -- watched during a run. The video overlay (render_overlay.py) is a separate, after-the-fact thing
  -- that only exists once a run has been recorded and traced; this is live.
  local bh, bm = boss_hp()
  if bh == 0 then
    return
  end
  local heads, hp, name = 0, 0, nil
  for i = 1, 11 do
    local t = mainmemory.read_u8(0x34F + i)
    local h = mainmemory.read_u8(0x485 + i)
    if h > 0 and (BOSS_TYPES[t] or t == 0) then
      heads = heads + 1
      hp = hp + h
      -- An untyped slot is neck, and it has no name of its own; the named type wins, so a Gleeok
      -- reads GLEE0K rather than whatever the segments claim.
      if BOSS_TYPES[t] then name = BOSS_TYPES[t] end
    end
  end
  local y = 214
  gui.drawString(4, y, string.format("%s %d/%d", name or "BOSS", hp, bm),
                 0xFFFF4040, 0xFF000000)
  gui.drawString(4, y + 9, string.format("PARTS %d  ATTEMPT %d", heads, hud.attempt),
                 0xFF40C0FF, 0xFF000000)
  -- one tick per remaining part, so the shape of what is left is legible at a glance
  if bm > 0 then
    local w = math.max(2, math.floor(100 * hp / bm))
    gui.drawRectangle(4, y + 18, 4 + w, y + 20, 0xFFFF4040)
  end
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
