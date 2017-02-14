import re


class ConfigError(Exception):
    pass


def regex_compiles(regex):
    try:
        re.compile(regex)
    except re.error:
        return False

    return True
