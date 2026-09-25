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

local function state_str()
  local p = {"frame=" .. emu.framecount()}
  for _, f in ipairs(FIELDS) do
    p[#p+1] = f[1] .. "=" .. mainmemory.read_u8(f[2])
  end
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
