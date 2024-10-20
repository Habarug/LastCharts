import string

"""Various utility functions"""


def valid_filename(filename: str) -> str:
    """Removes illegal characters from a filename string"""
    valid_chars = "-_.,() %s%s" % (string.ascii_letters, string.digits)
    return "".join(c for c in filename if c in valid_chars)


def check_username(username: str) -> bool:
    """Checks if provided username is valid"""
    valid_chars = "-_ %s%s" % (string.ascii_letters, string.digits)
    if not isinstance(username, str):
        return False
    if (len(username) > 15) or (len(username) < 2):
        return False
    elif any(c not in valid_chars for c in username):
        return False
    else:
        return True


def check_API_key(API_key: str) -> bool:
    valid_chars = "%s%s" % (string.ascii_letters, string.digits)
    if not isinstance(API_key, str):
        return False
    elif any(c not in valid_chars for c in API_key):
        return False
    else:
        return True


def shorten_strings(strings, max_length=25):
    """ "Shortens string or strings to a given max length"""
    if isinstance(strings, str):
        return _shorten_string(strings, max_length)

    strings_new = []
    for string in strings:
        strings_new.append(_shorten_string(string, max_length))

    return strings_new


def _shorten_string(string, max_length):
    """Shorten single string"""
    if len(string) > max_length:
        string = string[0 : max_length - 3] + "..."
    return string
