"""Run a chain of policies from a saved state (no reloads inside the chain), several seeds.
usage: python probe_chain.py <chain name> [seeds]"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import random, sys
import fullgame as fg
from zelda import runner
from zelda.emulator import BizHawk
from zelda.lookahead import Goal
from zelda.overworld import Navigator, LinkDied, read_enemies, enemy_name
from zelda.search import Recorder, make_cross_policy
from zelda.segments import make_lafight_policy, make_lareach_policy, make_grab_policy, make_clear_grab_policy, make_cross_at_policy

C = {
 "l4_short": ("ckpt_fullgame_l4_10", [
    ("dash-bomb E 10->11", lambda nav: fg.dash_bomb_policy(nav, "Right", 0x11), lambda s: s.room == 0x11),
    ("dash-bomb E 11->12", lambda nav: fg.dash_bomb_policy(nav, "Right", 0x12), lambda s: s.room == 0x12),
    ("12->13 fight",  lambda nav: make_lafight_policy(nav, "Right"), lambda s: s.room == 0x13)]),
 "l8_north": ("ckpt_fullgame_l8_5e", [
    ("clear 5E, up to 4E", lambda nav: make_lafight_policy(nav, "Up"), lambda s: s.room == 0x4E),
    ("4E -> 3E (locked)", lambda nav: make_cross_policy(nav, "Up"), lambda s: s.room == 0x3E)]),
 "l8_boss": ("ckpt_fullgame_r8_pass", [
    ("dash-bomb N 4C->3C", lambda nav: fg.dash_bomb_policy(nav, "Up", 0x3C), lambda s: s.room == 0x3C)]),
 "l6_short": ("ckpt_fullgame_l6_28", [
    ("dash-bomb E 28->29", lambda nav: fg.dash_bomb_policy(nav, "Right", 0x29), lambda s: s.room == 0x29),
    ("grab 29 key, down to 39", lambda nav: make_grab_policy(nav, "Down"), lambda s: s.room == 0x39)]),
 "l7_no3a": ("ckpt_fullgame_l7_39", [
    ("39 -> 38", lambda nav: make_cross_policy(nav, "Left"), lambda s: s.room == 0x38),
    ("38 -> 28 (locked)", lambda nav: make_cross_policy(nav, "Up"), lambda s: s.room == 0x28)]),
 "l5_start": ("ckpt_fullgame_l5_66", [
    ("grab 66 floor key", lambda nav: make_grab_policy(nav, None), lambda s: s.room == 0x66),
    ("dash-bomb W 66->65", lambda nav: fg.dash_bomb_policy(nav, "Left", 0x65), lambda s: s.room == 0x65),
    ("dash-bomb W 65->64", lambda nav: fg.dash_bomb_policy(nav, "Left", 0x64), lambda s: s.room == 0x64)]),
 "l4_keys": ("ckpt_fullgame_l4_51", [
    ("grab 51 floor key, left", lambda nav: make_grab_policy(nav, "Left"), lambda s: s.room == 0x50),
    ("50 -> 40", lambda nav: make_cross_policy(nav, "Up"), lambda s: s.room == 0x40),
    ("grab 40 floor key, up", lambda nav: make_grab_policy(nav, "Up"), lambda s: s.room == 0x30)]),
 "l1_bomb": ("ckpt_fullgame_l1_53_key", [
    ("bomb N 53->43", lambda nav: fg.bomb_policy(nav, "Up", 0x43), lambda s: s.room == 0x43)]),
 "l1_45": ("ckpt_fullgame_l1_44_boom", [
    ("grab 45 floor key, up", lambda nav: make_grab_policy(nav, "Up"), lambda s: s.room == 0x35)]),
 "p7_whirl": ("ckpt_fullgame_warp_L6", [
    ("whirlwind to L3's door", lambda nav: fg.whirl_to_policy(nav, 0x74), lambda s: s.room == 0x74 and s.level == 0),
    ("74 -> 73", lambda nav: make_cross_policy(nav, "Left"), lambda s: s.room == 0x73),
    ("73 -> 63", lambda nav: make_cross_policy(nav, "Up"), lambda s: s.room == 0x63),
    ("63 -> 62", lambda nav: make_cross_policy(nav, "Left"), lambda s: s.room == 0x62),
    ("62 -> 52", lambda nav: make_cross_policy(nav, "Up"), lambda s: s.room == 0x52),
    ("52 -> 42", lambda nav: make_cross_policy(nav, "Up"), lambda s: s.room == 0x42)]),
 "l6_east": ("ckpt_fullgame_food_leave", [
    ("34 -> 33", lambda nav: make_cross_policy(nav, "Left"), lambda s: s.room == 0x33),
    ("33 -> 32", lambda nav: make_cross_policy(nav, "Left"), lambda s: s.room == 0x32),
    ("32 -> 22", lambda nav: make_cross_policy(nav, "Up"), lambda s: s.room == 0x22)]),
 "l6_east2": ("ckpt_fullgame_bait_44", [
    ("44 -> 43", lambda nav: make_cross_policy(nav, "Left"), lambda s: s.room == 0x43),
    ("43 -> 33", lambda nav: make_cross_policy(nav, "Up"), lambda s: s.room == 0x33),
    ("33 -> 32", lambda nav: make_cross_policy(nav, "Left"), lambda s: s.room == 0x32),
    ("32 -> 22", lambda nav: make_cross_policy(nav, "Up"), lambda s: s.room == 0x22)]),
 "row2_west": ("ckpt_fullgame_l4w06_27", [
    ("27 -> 26", lambda nav: make_cross_policy(nav, "Left"), lambda s: s.room == 0x26),
    ("26 -> 25", lambda nav: make_cross_policy(nav, "Left"), lambda s: s.room == 0x25),
    ("25 -> 24", lambda nav: make_cross_policy(nav, "Left"), lambda s: s.room == 0x24),
    ("24 -> 23", lambda nav: make_cross_policy(nav, "Left"), lambda s: s.room == 0x23),
    ("23 -> 22", lambda nav: make_cross_policy(nav, "Left"), lambda s: s.room == 0x22)]),
 "l4_north": ("ckpt_fullgame_l4_b31", [
    ("31 -N(locked)-> 21", lambda nav: make_cross_policy(nav, "Up"), lambda s: s.room == 0x21),
    ("21 -N(bomb)-> 11", lambda nav: fg.dash_bomb_policy(nav, "Up", 0x11), lambda s: s.room == 0x11)]),
 "l4_ring": ("ckpt_fullgame_l4_20", [
    ("20 -E(open)-> 21", lambda nav: make_cross_policy(nav, "Right"), lambda s: s.room == 0x21),
    ("21 -N(bomb)-> 11", lambda nav: fg.dash_bomb_policy(nav, "Up", 0x11), lambda s: s.room == 0x11)]),
 "l8_7f": ("ckpt_fullgame_l8_7f", [
    ("grab 7F floor key, left", lambda nav: make_grab_policy(nav, "Left"), lambda s: s.room == 0x7E)]),
}
name = sys.argv[1]; seeds = int(sys.argv[2]) if len(sys.argv) > 2 else 3
state, steps = C[name]
emu = BizHawk(log_name=f"probe_chain_{name}.log", clean_sram=False); nav = Navigator(emu)
for seed in range(seeds):
    s0 = emu.load(state); runner.SEG_START = s0
    print(f"[{name}] seed {seed}: room {s0.room:02X} hearts {s0.hearts} keys {s0.keys} bombs {s0.bombs}", flush=True)
    total = 0
    for label, make, good in steps:
        runner.SEG_START = emu.state()
        rec = Recorder(emu); rec.step((), 2); nav.blocked = {}
        h0 = emu.state().hearts
        try:
            out = make(nav)(emu, rec, random.Random(1000 + seed), 3000)
        except LinkDied:
            out = "died"
        except Exception as e:
            out = f"{type(e).__name__}: {str(e)[:40]}"
        s = emu.state(); total += len(rec.inputs)
        ok = s.hearts > 0 and good(s) and s.mode == 5
        ens = sorted({enemy_name(e[1]) for e in read_enemies(emu)})
        print(f"   {label:26s} {str(out)[:24]:26s} -> {s.room:02X} {len(rec.inputs):5d} fr hearts {h0}->{s.hearts} keys {s.keys} bombs {s.bombs} "
              f"{'OK' if ok else 'WRONG'}  now sees: {ens}", flush=True)
        if not ok:
            print("   shot:", emu.screenshot(f"chain_{name}_{seed}"), flush=True); break
    else:
        print(f"   CHAIN OK {total} frames", flush=True)
emu.close()
