"""Smoke test: boot, run 300 frames, read state, take a screenshot, quit."""
import time
from zelda import BizHawk

t0 = time.time()
with BizHawk(log_name="smoke.log") as emu:
    print("connected in %.1fs" % (time.time() - t0))
    s = emu.state()
    print("boot:", s)
    t1 = time.time()
    s = emu.wait(300)
    dt = time.time() - t1
    print("after 300 frames:", s, " (%.0f fps)" % (300 / dt))
    print("ram 0x10..0x1f:", emu.ram(0x10, 16).hex())
    print("shot:", emu.screenshot("smoke_title"))
    t1 = time.time()
    for _ in range(200):
        emu.step((), 1)
    dt = time.time() - t1
    print("200 single-frame round trips: %.0f fps" % (200 / dt))
    print("inputs logged:", len(emu.inputs))
print("done in %.1fs" % (time.time() - t0))
