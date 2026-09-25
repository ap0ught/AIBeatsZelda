# 26 — Which way Link faces

**Where we are:** out of Level 9 without a scratch — five rooms, a passage and the entrance wing,
all at seven hearts. Next stop: two heart containers and the Magical Sword, on the other side of
the map. The plan was to ride the recorder's whirlwind, the game's fast travel.

## It failed every attempt
The whirlwind carried Link somewhere every time — just never to Level 1. A frame-by-frame probe
turned one mystery into four:

1. **Notes that did nothing.** Right after a ride Link glides a few pixels; a note played during
   that glide is simply lost.
2. **Knocked into the wrong dungeon.** An enemy beside Level 6's door hit Link while he stood
   playing, and the knockback shoved him straight inside.
3. **The pond.** One stop is Level 7's pond, where the recorder drains the water instead of calling
   the wind. Link stood there playing forever.
4. **The AI's own stopwatch.** It counted a ride as a dud if Link hadn't landed within 360 frames.
   A ride takes about 380. So a later test "failed" eight rides that all actually happened —
   the seventh time this project's instrument, not the game, was the broken thing.

## The real rule
Even with all four fixed, the destinations made no sense: Level 6, 7, 6, 5, 6, 7…

So, research first. The answer: **the wind's destination is a counter, and the direction Link faces
when he plays moves it.** Facing up or right goes forward one level; facing left or down goes back
one. Every ride in both traces fit — after walking down a screen, Link went back a level; after
gliding right, forward.

In practice one ride moves exactly one level, so the AI now plans warps like a route: pick the
shorter way round, avoid landing on the pond or beside Level 6's door, face left or right (never up
— the dungeon door is right above the landing spot), and play one note per ride.

## Result
First warp in the real run: Spectacle Rock to Level 1's door on the first attempt.
