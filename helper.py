"Helper module"

import os
import sys

DATEFRMT = '%d %B %Y %H:%M:%S'

ENDC = '\033[0m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'


class Bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'


COLORS: dict = {
    'r': Bcolors.FAIL,
    'g': Bcolors.OKGREEN,
    'b': Bcolors.OKBLUE,
    'c': Bcolors.OKCYAN,
    'y': Bcolors.WARNING,
}


def color_print(msg: str, color: str = 'g', **kwargs) -> None:
    """Color print a message."""
    start = COLORS.get(color, Bcolors.WARNING)
    print(start + f'{msg}' + ENDC, **kwargs)


def prog_print(msg: str, **kwargs) -> None:
    """Program print a message."""
    print(f'{os.path.basename(sys.argv[0])}: {msg}', **kwargs)


def header_print(msg: str, color='y', **kwargs) -> None:
    """Print a header line."""
    start = COLORS.get(color, Bcolors.WARNING)
    print('\n' + f'  \033{start}{msg}\n  {"-" * len(msg)}' + ENDC + '\n',
          **kwargs)
