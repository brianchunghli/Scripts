"Helper module containing basic functions and variables"

import os

DATEFRMT = '%d %B %Y %H:%M:%S'
COLORS: dict = {
    'r': '[38;5;1m',
    'g': '[38;5;2m',
    'y': '[38;5;11m',
}


def color_print(msg: str, color='g', **kwargs) -> None:
    """Color print a message."""
    start = COLORS.get(color, '[0;0m')
    print(f'\033{start}{msg}\033[0;0m', **kwargs)


def prog_print(msg: str, **kwargs) -> None:
    """Program print a message."""
    print(f'{os.path.basename(__file__)}: {msg}', **kwargs)


def header_print(msg: str, color='y', **kwargs) -> None:
    """Print a header line."""
    print(f'\n  \033{COLORS.get(color)}{msg}\n  {"-" * len(msg)}\033[0;0m\n',
          **kwargs)
