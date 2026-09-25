-- Plays back a loaded .bk2 (EmuHawk --movie=...) to the end and writes the final state to a file.
local out = io.open("G:/AI World Record/harness/logs/verify_bk2_result.txt", "w")
local function log(s) out:write(tostring(s) .. "\n"); out:flush(); console.log(s) end
log("movie loaded=" .. tostring(movie.isloaded()) .. " length=" .. tostring(movie.length()) .. " mode=" .. tostring(movie.mode()))
local hdr = movie.getheader()
for k, v in pairs(hdr) do log("header " .. tostring(k) .. "=" .. tostring(v)) end
if not movie.isloaded() then log("NO MOVIE"); out:close(); client.exit() end
movie.setreadonly(true)
client.unpause()
local len = movie.length()
while emu.framecount() < len do emu.frameadvance() end
log(string.format("final frame=%d mode=%02x room=%02x x=%d y=%d sword=%d lag=%d",
  emu.framecount(), mainmemory.read_u8(0x12), mainmemory.read_u8(0xEB),
  mainmemory.read_u8(0x70), mainmemory.read_u8(0x84), mainmemory.read_u8(0x657), emu.lagcount()))
log("DONE")
out:close()
client.exit()
