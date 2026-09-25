# Phase 2: teaching it to see walls

**Goal.** Milestone 1 walked to the cave using coordinates I typed in by hand. That does not
scale to 128 overworld screens and 9 dungeons. The bot has to read the map itself and find its
own way.

**How.** The game decodes each screen into a grid of 8x8 pattern tiles in cartridge memory,
32 across by 22 down. I found that block by dumping memory and comparing it to a screenshot: the
tree tiles, the ground, and the cave entrance all lined up. So the map is free. What the map does
not say is which tiles Link can walk on.

I measured that by pushing Link into things. Walk up at a known column until he stops, record
where he stopped, repeat for every tile type on the screen. Two facts fell out:

- Link's body for collision purposes is a 16x16 box that starts 3 pixels below the y value the
  game stores. That odd offset explains every stopping position.
- Collision happens per 8x8 tile, not per 16x16 tile. The "dark ground" at the edge of a tree
  line is walkable even though it is drawn as part of the tree, and one tree tile is solid on top
  and walkable on the bottom.

**The learning loop.** The bot keeps a small knowledge base: tile ids it knows are walkable, tile
ids it knows are solid. Anything else is unknown. To move, it plans a path with breadth-first
search over 8-pixel steps, optimistically assuming unknown tiles are fine. Then it executes one
step at a time, watching Link's position. If a step fails, it looks at which tiles that step
would have entered. If exactly one of them was unknown, it now knows that tile is solid, saves
that, and re-plans. The knowledge base is a file, so what it learns on one screen carries to
every later screen and every later run.

**What went wrong.** My first stall detector flagged Link as stuck at x=193 with open ground
ahead. He wasn't stuck; he pauses for a frame when turning, and six paused frames looked like a
wall. I spent a probe run chasing a phantom obstacle.
