"""Shots per script section for build_v3.py: section title (as in SCRIPT_v3.md headings) -> clips in order.
A clip spec: {"clip": path relative to youtube/, "in": s, "out": s}. A section longer than its clips holds the last
frame, so every long section gets enough picture: the built visual first, then real footage of the run (with the AI
panel) for the stretch it talks about. No clip appears twice."""
C = "clips_v3/"
SHOTS = {
    "preamble": [{"clip": C + "intro.mp4"}],
    "0. Three in the morning": [{"clip": C + "wall_r8_3f.mp4", "in": 0, "out": 34}],
    "1. It doesn't play the game. It built a player.": [{"clip": C + "architecture.mp4"}, {"clip": C + "terminal_search.mp4"}],
    "2. Eyes": [{"clip": C + "ramvision.mp4"}, {"clip": C + "tilelearn.mp4"}, {"clip": C + "run6_walk_to_L3.mp4"}],
    "3. Legs": [{"clip": C + "explore_graph.mp4"}, {"clip": C + "run6_northeast_walk.mp4"}, {"clip": C + "run6_whirlwind.mp4"}],
    "4. Practice": [{"clip": C + "wall_r8_3f.mp4", "in": 34}, {"clip": C + "mosaic_day2.mp4"}, {"clip": C + "terminal_match.mp4"}],
    "4b. Things that broke": [{"clip": C + "broke_wall.mp4"}],
    "5. Fighting: one second ahead": [{"clip": C + "mind_59_fight.mp4"}, {"clip": C + "lookahead.mp4"}, {"clip": C + "run6_wallmasters.mp4"},
                                      {"clip": C + "run6_L5_recorder_room.mp4"}, {"clip": C + "run6_L8_keyroom.mp4"}, {"clip": C + "run6_L6_wizzrobes.mp4"}],
    "6. Measuring the monsters": [{"clip": C + "monsters.mp4"}],
    "7. Reading the cartridge": [{"clip": C + "tenth_kill.mp4"}, {"clip": C + "disasm.mp4"}, {"clip": C + "run6_L4_ring.mp4"},
                                 {"clip": C + "map_reveal.mp4"}],
    "8. Routing": [{"clip": C + "map_route4.mp4"}, {"clip": C + "run6_L9_entry.mp4"}],
    "9. The sword that went sideways": [{"clip": C + "run4_circling.mp4"}, {"clip": C + "decisions_scroll.mp4"},
                                        {"clip": C + "sideways.mp4"}, {"clip": C + "run5_fixed_room.mp4"}],
    "10. Six runs": [{"clip": C + "race.mp4"}],
    "11. Where it stands": [{"clip": C + "stands.mp4"}, {"clip": C + "run6_death_mountain.mp4"}, {"clip": C + "run6_L9_hub.mp4"},
                            {"clip": C + "run6_L9_wizzrobes.mp4"}, {"clip": C + "handoff.mp4"}],
    "outro": [{"clip": C + "map_route4.mp4"}],
}
