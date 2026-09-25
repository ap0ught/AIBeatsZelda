"""Which overworld screens will actually hand over money? 0x0F (the plan's 100-rupee hope) is
unreachable - screen 0x0D's east side is solid mountain. So sweep the screens the route already
crosses, using late checkpoints so Link has the Red Candle for burn attempts. Each sweep works off
in-memory snapshots: no bombs and no game time are really spent."""
from zelda.emulator import BizHawk
from zelda.overworld import Navigator
from zelda import secrets

CANDIDATES = [                       # (checkpoint, screen, what the community map claims)
    ("ckpt_fullgame_w8_62",  0x62, "100 rupees (7C) - canyon, crossed 5x by the route"),
    ("ckpt_fullgame_w8_67",  0x67, "30 rupees (7H) - already on the route"),
    ("ckpt_fullgame_h9_28",  0x28, "30 rupees (3I)"),
    ("ckpt_fullgame_h9_48",  0x48, "30 rupees (5I)"),
    ("ckpt_fullgame_hc_b3d", 0x3D, "30 rupees (4N) - Armos"),
    ("ckpt_fullgame_n9_1a",  0x1A, "open cave per the ROM table (0x03)"),
]
emu = BizHawk(log_name="probe_money.log", clean_sram=False)
nav = Navigator(emu)
for ckpt, screen, claim in CANDIDATES:
    try:
        s = emu.load(ckpt); s = emu.wait(4)
    except Exception as e:
        print(f"== {screen:02X}: cannot load {ckpt}: {str(e)[:60]}", flush=True)
        continue
    if s.room != screen or s.level:
        print(f"== {screen:02X}: {ckpt} stands on {s.room:02X} level {s.level}, skipping", flush=True)
        continue
    print(f"\n== SCREEN {screen:02X} ({claim}) from {ckpt}: {s} candle={emu.byte(0x65B)}", flush=True)
    try:
        found = secrets.sweep(emu, nav)
        print(f"   sweep -> {found}", flush=True)
    except Exception as e:
        print(f"   sweep raised: {type(e).__name__}: {str(e)[:110]}", flush=True)
emu.close()
