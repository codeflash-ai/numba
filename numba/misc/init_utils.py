"""Collection of miscellaneous initialization utilities."""

from collections import namedtuple

version_info = namedtuple(
    "version_info", ("major minor patch short full " "string tuple git_revision")
)


def generate_version_info(version):
    """Process a version string into a structured version_info object.

    Parameters
    ----------
    version: str
        a string describing the current version

    Returns
    -------
    version_info: tuple
        structured version information

    See also
    --------
    Look at the definition of 'version_info' in this module for details.

    """
    parts = version.split(".")
    # Inline try_int for reduced overhead and allocate all at once
    plen = len(parts)
    try:
        major = int(parts[0]) if plen >= 1 else None
    except ValueError:
        major = None
    try:
        minor = int(parts[1]) if plen >= 2 else None
    except ValueError:
        minor = None
    try:
        patch = int(parts[2]) if plen >= 3 else None
    except ValueError:
        patch = None
    short = (major, minor)
    full = (major, minor, patch)
    string = version
    tup = tuple(parts)
    git_revision = tup[3] if plen >= 4 else None
    return version_info(major, minor, patch, short, full, string, tup, git_revision)
