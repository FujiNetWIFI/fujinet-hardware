"""Per-process scratch files for the board tools, so parallel routing
variants never share a DRC report or netlist (fixed names in the system temp
directory collided).  The directory goes away when the process exits."""
import atexit, os, shutil, tempfile

_DIR = tempfile.mkdtemp(prefix='fujinet-astrocade-')
atexit.register(shutil.rmtree, _DIR, True)


def tmp(name):
    """A path for scratch file `name` in this process's directory."""
    return os.path.join(_DIR, name)
