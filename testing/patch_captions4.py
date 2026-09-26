"""Caption for Level 7's 0D now that the block is pushed from the corridor side."""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import pprint
import pathlib

from zelda.captions import CAPTIONS

NEW = {
    "l7_0d_st": ("LEVEL 7 - STAIRS TO AQUAMENTUS",
                 "Five Wallmasters must die before the block will move. Push it LEFT from the corridor: the stairs "
                 "open in the corner right behind Link."),
}
for n, (h, w) in NEW.items():
    assert len(h) <= 40, (n, len(h))
    assert len(w) <= 150, (n, len(w))
CAPTIONS.update(NEW)
p = pathlib.Path("zelda/captions.py")
head = p.read_text(encoding="utf-8").split("CAPTIONS: dict[str, tuple[str, str]] = ", 1)[0]
p.write_text(head + "CAPTIONS: dict[str, tuple[str, str]] = " + pprint.pformat(CAPTIONS, width=118, sort_dicts=False) + "\n",
             encoding="utf-8")
print(f"{len(NEW)} captions updated; {len(CAPTIONS)} total")
