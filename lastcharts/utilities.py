import string

"""Various utility functions"""


def valid_filename(filename: str) -> str:
    """Removes illegal characters from a filename string"""
    valid_chars = "-_.,() %s%s" % (string.ascii_letters, string.digits)
    return "".join(c for c in filename if c in valid_chars)
