# Phase 3: finding Level 3 without a map

**Goal.** The route says Level 3 first. I believed its entrance is on screen 74, three screens
west of the start. The navigator walked west, crossed two screens, and ran into a river with no
bridge. Straight west is not a route. The bot needed to find its own way around.

**How.** Nobody gave it the overworld map. Instead it explores like a person would, but with one
unfair advantage: bookmarks. Standing on a screen, it reads the tile map and works out which edges
it could walk to. Then it saves a bookmark, walks out one exit, notes which screen it landed on and
where, and jumps back to the bookmark to try the next exit. Every screen it visits and every exit
it tries goes into a file, so it never has to rediscover them.

The search is guided: screens closer to the target on the grid get tried first. It expanded
about twenty screens and found a seven-screen route: west, north, west three times, south, east.
Up and around the river.

Bookmarks are only used for looking. The final run will walk that route from power-on with no
bookmarks, and its input log has to replay identically like everything else.

**What it learned on the way.** Every "blocked" note in the video is the bot bumping into
something it did not know was solid: water, several kinds of rock, cliff edges. When only one
unknown tile could be responsible, it writes that tile down as solid for good. Twice it bumped
into something where every tile was supposedly walkable. That is an honest "my model is wrong
here" and it marks that single move impossible instead of guessing.

**What went wrong.** On the third screen it spent fifteen re-plans trying to walk into the river
from different rows before concluding there was no way up that side. Each attempt taught it
nothing new because two unknown tiles were involved each time, so it could not tell which was
the culprit. A smarter version would test one tile in isolation. It got there anyway, just slower.
