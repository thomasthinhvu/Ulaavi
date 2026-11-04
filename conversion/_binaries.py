"""
Locate external command line tools (ffmpeg, ffprobe) on Windows, macOS and Linux.

Nuke and other GUI apps often start with a shorter PATH than the terminal has
(for example Homebrew's /opt/homebrew/bin on Apple Silicon), so common install
folders are checked as well. The environment variable ULAAVI_BIN_DIR can name an
extra folder to search first.
"""
import os
import shutil

_COMMON_DIRS = ['/opt/homebrew/bin', '/usr/local/bin', '/opt/local/bin', '/usr/bin']


def find_binary(name: str) -> str:
    """
    Return the full path of an executable, or the bare name if it cannot be found.

    The bare name is returned on purpose: the OS then reports a clear "not found" error
    when the tool is run, instead of this function failing earlier.

    :param name: Executable name, for example 'ffmpeg'.
    :return: Full path to the executable, or `name` if nothing was found.
    """
    found = shutil.which(name)
    if found:
        return found

    extra = os.environ.get('ULAAVI_BIN_DIR', '')
    for folder in [extra] + _COMMON_DIRS:
        if not folder:
            continue
        candidate = os.path.join(folder, name)
        if os.path.isfile(candidate):
            return candidate

    return name
