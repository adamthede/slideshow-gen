"""PyInstaller entry shim for the slideshow-gen sidecar.

`slideshow_gen.cli` uses relative imports (`from .config import …`),
so PyInstaller can't run it as a top-level script. This shim imports
the package's CLI group and dispatches to it — same effect as the
installed `slideshow-gen` console script defined in pyproject.toml.

`multiprocessing.freeze_support()` MUST run before anything else.
The engine uses `ProcessPoolExecutor` for parallel image rendering;
on macOS, multiprocessing spawns helper processes (resource_tracker,
pool workers) by re-invoking `sys.executable` with internal flags like
`-B` and `--multiprocessing-fork`. In a PyInstaller-frozen build,
`sys.executable` IS this binary — without `freeze_support()`, Click
sees those flags as unknown CLI options and the helper processes
crashloop. (See PyInstaller docs: "Run-time information / Freezing
multiprocess apps".)
"""

import multiprocessing

if __name__ == "__main__":
    multiprocessing.freeze_support()

    from slideshow_gen.cli import cli
    cli()
