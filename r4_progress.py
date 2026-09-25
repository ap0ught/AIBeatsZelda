"""Route 4 run against the planner's own prediction (minutes of game time at each milestone)."""
import glob, json, os
MODEL = [("L3_done", 3.23), ("h2c_heart", 4.53), ("cave_0f", 5.11), ("candle_leave", 5.72), ("white_sword", 6.32),
         ("L1_done", 9.10), ("h47_heart", 9.53), ("L4_done", 13.71), ("cave_6b", 14.55), ("L8_done", 17.86),
         ("L2_done", 19.69), ("L5_done", 24.65), ("shop_leave", 25.35), ("food_leave", 25.65), ("L7_done", 29.44),
         ("ms_sword", 30.49), ("L6_done", 32.97), ("g9_zelda", 39.10)]
ck = {}
for f in glob.glob("logs/checkpoints/fullgame_*.json"):
    d = json.load(open(f)); ck[os.path.basename(f)[9:-5]] = d
last = max(ck.values(), key=lambda d: d["frames"])
print(f"now: {last['frames']} frames = {last['frames']/3606:.2f} min; hearts {last.get('hearts')} keys {last.get('keys')} bombs {last.get('bombs')}  ({last['state']})")
for name, m in MODEL:
    if name in ck:
        t = ck[name]["frames"] / 3606
        print(f"   {name:13s} model {m:6.2f}  run {t:6.2f}  {t - m:+.2f} min   hearts {ck[name].get('hearts')} bombs {ck[name].get('bombs')} keys {ck[name].get('keys')}")
