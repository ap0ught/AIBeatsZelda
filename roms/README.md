# The cartridge goes here

Put your own dump of the game in this directory as:

```
Legend of Zelda, The (USA) (Rev 1).nes
```

It is looked for here first, and this is where `setup_linux.sh` installs it. The
file is **never committed** — `.gitignore` excludes `*.nes` — because Nintendo
does not license the ROM and neither do we. Only the name and the hash below are
in the repository.

## The hash is not optional

```
md5  614fb3085826e62f3be3a3fe0b931689
```

That is the No-Intro `The Legend of Zelda (USA) (Rev 1)`. The harness works on
that dump and only that dump. The ROM collections people actually own tend to
have several dumps of the same game side by side, differing only in filename:

| file | works? |
|---|---|
| `Legend of Zelda, The (USA) (Rev 1).nes` | yes — this one |
| `Legend of Zelda, The (USA).nes` | no |
| `Legend of Zelda, The (USA) (Rev A).nes` | no |
| `Legend of Zelda, The (Europe).nes` | no |

A Rev A or European dump does not fail loudly. It boots, the bridge connects, the
harness searches, and the run is subtly wrong — different code layout, different
memory map assumptions, a different ending. `setup_linux.sh` checks the md5 and
refuses to install a ROM that does not match, which is worth more than a README
warning:

```
$ ./setup_linux.sh "/path/to/Legend of Zelda, The (USA).nes"
ROM md5 mismatch: got 337bd6f1a1163df31bf2633665589ab0, want
614fb3085826e62f3be3a3fe0b931689 (No-Intro USA Rev 1)
The harness and the shipped run only work on that exact dump.
```

To check what you have:

```
md5sum "Legend of Zelda, The (USA) (Rev 1).nes"
```

## Overriding the location

If you keep the ROM somewhere else entirely, point the harness at it rather than
copying it:

```
ZELDA_ROM=/path/to/zelda.nes python3 smoke_test.py
```

`zelda/emulator.py` resolves the ROM in this order: `ZELDA_ROM`, then this
directory, then the BizHawk folder, and falls back to this path in error
messages so a missing cartridge points somewhere sensible.

## Why the ROM is not in the repository

The project's own `.gitignore` has led with `*.nes` and `# never: the game` since
the first commit, and that is the right call. Committing it would make the
repository unusable for anyone without a legally obtained dump, and would put a
copyrighted Nintendo ROM in git history where it cannot be cleanly removed. A
`.gitignore`d file that is nonetheless present in the working tree is the right
arrangement: the path is part of the interface, the bytes are not.
