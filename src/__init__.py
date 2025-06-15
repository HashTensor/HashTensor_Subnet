from importlib.metadata import version, PackageNotFoundError

PREV_SPEC_VERSION = 419000

try:
    __version__ = version("hashtensor-validator")
except PackageNotFoundError:
    raise ValueError("hashtensor-validator package not found")

version_split = __version__.split(".")

__spec_version__ = (
    (1000 * int(version_split[0]))
    + (10 * int(version_split[1]))
    + (1 * int(version_split[2]))
) + PREV_SPEC_VERSION
