"""PyInstaller entry shim for the slideshow-gen sidecar.

`slideshow_gen.cli` uses relative imports (`from .config import …`),
so PyInstaller can't run it as a top-level script. This shim imports
the package's CLI group and dispatches to it — same effect as the
installed `slideshow-gen` console script defined in pyproject.toml.
"""

from slideshow_gen.cli import cli

if __name__ == "__main__":
    cli()
