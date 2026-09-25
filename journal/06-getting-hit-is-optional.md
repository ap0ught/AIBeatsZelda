# Phase 6: getting hit is optional

**The correction.** I had started writing notes like "Link is too hurt to win this room." The
human on the project pushed back, and he was right: a perfect player finishes this game without
taking a single hit. Link is never too weak. The bot is getting hit, and every hit is a mistake
it could have avoided. That reframing changes what the search optimizes for.

**What the bot had been doing.** Exploring the dungeon on whatever health it stumbled in with,
dying, reloading, dying again. It reached a five-Darknut room on one heart and a randomized
crossing failed sixty times in a row. Also, those rooms are shutter rooms: the doors stay shut
until every Darknut is dead, so there is no crossing to find. They have to be fought.

**The new shape.** Each room is a segment. From the bookmark at its door, the bot runs dozens of
randomized attempts of the right behavior for that room: dodge across, grab the item, or kill
everything. Attempts are scored by hearts remaining first and frames second, so a slower clean
clear beats a faster one that took a hit. The winner's inputs are saved, its end state becomes
the next room's bookmark, and the chain moves on. This is the same machine that will later shave
frames off the whole run, pointed first at survival.

**Sword lessons folded in.** Darknuts block frontal blows, so the fighter now reads which way
each one faces and refuses to swing into a shield. Blade traps cannot be killed; their rows and
columns are cost bands the planner avoids unless forced through.

**A viewer's fix, again.** The five-second pause every time the emulator closed was a
"Really quit? You are recording A/V" dialog waiting for a click nobody gave. The launcher now
answers it, and recorded sessions close in half a second with intact video.

**Research.** Most enemy wikis block automated reading, so the playbook in
`knowledge/playbook.md` leans on the Speed Demos Archive run notes and the TAS author's notes,
plus the bot's own measurements. It grows as sources open up and as fights teach it.
