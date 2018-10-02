"""Logic to handle pyupdate."""
import subprocess
import sys


def update():
    """Update this package."""
    subprocess.call([sys.executable,
                     "-m",
                     "pip",
                     "install",
                     "--upgrade",
                     "pyupdate"])
