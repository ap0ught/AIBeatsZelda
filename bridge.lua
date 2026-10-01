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
  [0x46] = GLEE0K,          -- UpdateGleeokHead: the head that comes loose and keeps flying
}

local boss_seen = 0        -- the peak HP a boss has shown, so the total has a denominator

-- Harness-side story state, told to the HUD by the Python side. The head is not in the ROM: see
-- zelda/head.py, which is explicit that nothing in the cartridge knows or cares. It is on the line
-- anyway because the rest of the line is also things you cannot see in a still frame - "L0 R0A" is
-- a room number, not a picture - and a run that is walking a dragon's head home across thirty-one
-- screens is exactly the thing you want to be able to read at a glance while it happens.
local story = { head = 0 }

-- What this window is being used for right now, set by the Python side with `phase <label>`.
-- A scout window shows a SEARCH PHASE (baseline / polish / taking it) and MAIN shows what it is
-- doing with the winner (replay / trim). Four identical-looking windows are otherwise unreadable:
-- from the room alone you cannot tell a search that has never found a line from one that has a line
-- and is trying to beat it, and those two want opposite things from you - the first needs more
-- attempts, the second needs you to leave it alone.
--
-- Drawn right-aligned on the HUD line rather than appended, because the line already carries the
-- room and the boss read-out and they collide. Colour is by phase so four windows can be read at a
-- glance from across the desk.
local phase = ""
-- Colour is keyed on the FIRST WORD, so a numbered label ("POLISH #7") or a staged one
-- ("STAGE 2/5 POLISH #7") colours by what it is, not by its numbering.
local PHASE_COLOUR = {
  BASELINE = 0xFF60FF60,   -- green: nothing found yet, every attempt is still looking for a line
  SEARCH   = 0xFF60FF60,
  POLISH   = 0xFFFFA040,   -- amber: we have a line and are hunting for a faster one
  STAGE    = 0xFFFFA040,
  CONVERGED = 0xFFB0B0B0,  -- grey: decided. The four stop reasons, told apart, because they are
  CAPPED   = 0xFFB0B0B0,   --       four different decisions and all four used to print the same line
  SEARCHED = 0xFFB0B0B0,
  DONE     = 0xFFB0B0B0,
  REPLAY   = 0xFF60C0FF,   -- blue: MAIN is playing a winner in
  TRIM     = 0xFF60C0FF,
  VERIFY   = 0xFF60C0FF,
}

-- One read of the object table, shared by everything that needs it. Returns slot -> {type, hits},
-- the total in hits, and the name to print.
--
-- The two passes are the whole bug this file spent a fight misreporting. Reading "HP is live AND the
-- type is a boss OR untyped" as one condition let a stale byte count as a boss: scanning every
-- checkpoint showed l4_heart - the segment AFTER the Gleeok is dead and the room is cleared - still
-- reading 70 hits across seven untyped slots, and manhandla 15. The game does not clear the health
-- array when an object dies. Because boss_seen only resets when the total reaches zero, those stale
-- reads latched the peak and the HUD then drew through every ordinary fight afterwards - which is
-- what "it shows the boss gui when we battle any creature" was.
--
-- So untyped slots are collected separately and only folded in while a NAMED boss type is actually
-- present in the table. That keeps the one case the catch-all exists for - Gleeok neck segments,
-- written with type 0, which are 60 of the boss's 70 HP - and makes every other untyped byte inert.
local function scan()
  local parts, hits, name, untyped = {}, 0, nil, {}
  for i = 1, 11 do
    local t = mainmemory.read_u8(0x34F + i)
    local h = mainmemory.read_u8(0x485 + i)
    if h > 0 then
      -- HP is stored as a nybble pair: the harness reads ObjHP >> 4 for a hit count, so a $A0 slot
      -- is 10 hits, not 160. The first version of this HUD printed the raw byte and the total came
      -- out "1136/1376" - unreadable, and unauditable, because it was wrong. 1136/16 is 71 and
      -- 1376/16 is 86: whole hit counts, which is the first reason to trust the number at all.
      local n = math.floor(h / 16)
      if n > 0 then
        if BOSS_TYPES[t] then
          parts[i] = { t = t, hp = n }
          hits = hits + n
          -- An untyped slot is neck and has no name of their own; the named type wins, so a Gleeok
          -- reads GLEEOK rather than whatever the segments would claim.
          name = BOSS_TYPES[t]
        elseif t == 0 then
          untyped[i] = n
        end
      end
    end
  end
  if name then
    for i, n in pairs(untyped) do
      parts[i] = { t = 0, hp = n }
      hits = hits + n
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

-- One line: where Link is, and - only when there is one - what is hitting him.
--
-- The room was added to the boss read-out rather than put beside it. The owner's reason was
-- practical: the log says "L4 room=13" and the window said "GLEEOK: 40/70", so talking about a
-- fight meant holding two sources in the head at once. Same convention as the log on purpose -
-- "L4 R13" is exactly the `L4 room=13` the search report prints, so the two can be read against
-- each other without translating.
--
-- Because the room is the part that is always true, the line is drawn on every step and not only
-- during a boss fight. That is the whole point of it: the boss read-out used to appear and vanish
-- with the fight, which made the screen useless for the far more common question of simply being
-- lost.
local function hud()
  -- The framebuffer is 256x224 - not the 256x240 this was written against for years - and the
  -- geometry has been wrong more times than the format has, which is the whole lesson of it.
  --
  -- 1. First attempt: strip at y=226, 14 rows of bar, text at y=245. Five rows BELOW the screen.
  --    The emulator renders those happily into the frame buffer; nobody ever sees them.
  -- 2. Second: everything moved up, text at 232-239. Inside the screen this time, and still
  --    invisible - the cells drew and the text did not. A 7px line flush against the last row is
  --    one clipping quirk from gone, and it spends the entire fight on the window edge.
  -- 3. Third: the text became a filled band, and the eleven cells became the main event. That was
  --    a strip of segmented health, and it was worse: the owner could read the room but not the
  --    fight. "That HUD is not good at all." A per-slot cell is the wrong granularity for a fight
  --    watched at speed - eleven positions to decode, each a different question.
  -- 4. Back to one line, name and health over total, and nothing else.
  -- 5. Then the room came back, on the same line.
  --
  -- It sits at row 57, which is the first row of the playfield. The status bar is a solid black
  -- block across rows 0-55 (measured off the emulator framebuffer), so this is the one band that is
  -- always on screen, always the same place, and never over the fight - the Gleeok works rows
  -- 90-150. At 216 it was three rows off the bottom and under the emulator's own save-slot bar.
  local TEXT_Y, TEXT_H = 57, 13
  local _, hits, name = scan()
  if hits > 0 and hits > boss_seen then
    boss_seen = hits                       -- latched here as well, so the denominator holds without
  end                                      -- depending on state_str() having run this frame
  local line = string.format("L%d R%02X", mainmemory.read_u8(0x10), mainmemory.read_u8(0xEB))
  if hits > 0 then
    line = line .. string.format("  %s: %d/%d", name or "BOSS", hits, boss_seen)
  end
  if story.head == 1 then
    line = line .. "  +HEAD"
  elseif story.head == 2 then
    line = line .. "  HEAD DOWN"
  end

  -- drawRectangle takes (x, y, WIDTH, HEIGHT, line, background) - every earlier version of this
  -- passed a bottom-row coordinate where the height goes, so the "filled band" was a 255x225
  -- rectangle outline with no fill, which is why the text kept vanishing into the floor tiles. Both
  -- colour arguments have to be given for it to be solid.
  gui.drawRectangle(0, TEXT_Y, 256, TEXT_H, 0xFF000000, 0xFF000000)
  gui.drawString(4, TEXT_Y + 1, line, 0xFF40C0FF, 0xFF000000)
  if phase ~= "" then
    -- Right-aligned: the room line grows to the right as the boss read-out is added, and a phase
    -- label in the middle of that would be overwritten on exactly the segments where the phase is
    -- most interesting. 8 px per cell is the built-in font's fixed width, and the sender caps the
    -- label at 14 cells (112 px), so it starts no further left than column 17.
    --
    -- On a boss segment the boss read-out is the longest line there is ("L3 R59  GLEEOK: 12/14", 22
    -- cells) and the phase label's opaque background does cover the last three characters of it.
    -- That is the trade: on a boss the phase is BASELINE until the kill and DONE after it, and the
    -- attempt number behind it is the part worth reading.
    local label = string.upper(phase)
    local colour = nil
    for w in label:gmatch("%S+") do            -- "S2/5 POLISH #7" colours by POLISH, not "S2/5"
      colour = PHASE_COLOUR[w] or colour
    end
    gui.drawString(252 - 8 * #label, TEXT_Y + 1, label, colour or PHASE_COLOUR.DONE, 0xFF000000)
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
    hud()
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
  elseif cmd == "story" then
    -- "story head 0|1|2": none, carried, delivered. A cosmetic read-out, so an emulator on an
    -- older bridge (or a bridge that has gone away entirely) must not cost the run anything - the
    -- Python side wraps this in a try, and an unknown command would otherwise answer "err" into a
    -- search that was working perfectly well.
    local what, v = rest:match("^(%S+)%s*(%d+)$")
    if what == "head" then
      story.head = tonumber(v) or 0
    end
    send("ok")
  elseif cmd == "attempt" then
    -- The Python side still sends this once per attempt (search.py:309), and the HUD no longer draws
    -- a counter, so the value is accepted and dropped rather than the command erroring: removing the
    -- command would make the sender's reply "err unknown command" on every attempt, for no gain.
    send("ok")
  elseif cmd == "phase" then
    -- `phase <label>` or `phase` alone to clear it. Cosmetic, like `story head`: an emulator on an
    -- older bridge must not cost the run anything, so the Python side wraps this in a try. Capped at
    -- 14 cells to match what the HUD draws, so a longer label is cut rather than run off the row.
    phase = rest:sub(1, 14)
    -- Draw it now rather than waiting for the next `step`. The HUD is painted from the step handler
    -- because there is no idle frame loop to paint from, which means a label set while the window is
    -- parked - which is exactly when the search has just finished and told every scout "done" -
    -- would not appear until that window was stepped again, i.e. probably never. A status light that
    -- only lights up when something else happens is not a status light.
    pcall(function() gui.clearGraphics(); hud() end)
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
