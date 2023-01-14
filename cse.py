#!/usr/bin/env python3
import argparse
import datetime
import os
import subprocess
from sys import argv

from localutils.credentials import cse_credentials
from localutils.printing import header_print, prog_print

'''
Basic script to interact with cse servers
'''

# define globals
CSE = cse_credentials()[0]
FOLDER = os.getcwd().replace(cse_credentials()[1], '')
IN_CSE_FOLDER: bool = os.getcwd() != FOLDER
DATEFRMT = '%d %B %Y %H:%M:%S'


def parse_args():
    '''
    Command line argument parser
    '''
    parser = argparse.ArgumentParser(
        allow_abbrev=False,
        exit_on_error=True,
        description='Utility to interact with cse servers')

    # exclude combined usage of different optional flags
    group = parser.add_mutually_exclusive_group()
    parser.add_argument(
        '-c',
        action='store_true',
        help='copy output to a "cse.out" file')

    parser.add_argument(
        '-d', '--debug',
        action='store_true',
        help=argparse.SUPPRESS)

    group.add_argument(
        '-f',
        action='store_true',
        help='upload files or directories to cse',)

    group.add_argument(
        '-a',
        action='store_true',
        help='run autotest')

    group.add_argument(
        '-s',
        action='store_true',
        help='request student record',)

    parser.add_argument('positional_args', nargs='*')
    return parser.parse_args()


def cse_run(line: str) -> str:
    '''
    Execute cse server commands
    '''
    global IN_CSE_FOLDER
    global FOLDER
    if IN_CSE_FOLDER:
        line = ['ssh', 'cse', f'COMP; cd {FOLDER}; ' + line]
    else:
        line = ['ssh', 'cse', line]
    return subprocess.run(line,
                          capture_output=True,
                          encoding='utf-8',
                          ).stdout


def display_output(lines: str) -> None:
    '''
    Display received response from cse servers
    '''
    for _ in lines.split('\n'):
        print('  ' + _)


def output_file(*args) -> None:
    '''
    Create cse.out file
    '''
    time = datetime.datetime.now().strftime(DATEFRMT)
    with open(f'{os.getcwd()}/cse.out', 'w') as f:
        print(time, file=f)
        for _ in args:
            print(_, file=f)
    print('output saved to \'cse.out\'')


def check_args(command: argparse.Namespace) -> (bool, bool):
    '''
    Basic checks for each flag
    '''

    global FOLDER
    global IN_CSE_FOLDER
    passed_check = True
    contains_flag = False
    pargs = command['positional_args']
    if command['f']:
        contains_flag = True
        if len(pargs) < 1:
            prog_print('missing file for -f command')
            passed_check = False
    elif command['a']:
        contains_flag = True
        if not IN_CSE_FOLDER:
            prog_print('autotest must be run in a unsw/cse folder')
            passed_check = False
        elif len(pargs) < 2:
            print('expected two arguments <class> <autotest>')
            passed_check = False
    elif command['s']:
        contains_flag = True
    else:
        if 'give' in pargs or 'autotest' in pargs and not IN_CSE_FOLDER:
            prog_print('give/autotest must be run in the unsw/cse folder')
            passed_check = False
    if command['c']:
        if command['f'] or command['s']:
            prog_print('Invalid flag used with -c')
            passed_check = False
    return passed_check, contains_flag


def process_flag(command: argparse.Namespace) -> None:
    '''
    Execute process for each flag
    '''
    global FOLDER
    global IN_CSE_FOLDER
    output = ''
    pargs = command['positional_args']
    if command['f']:
        for f in pargs:
            if not os.path.exists(os.getcwd() + r'/' + f):
                prog_print(f"'{f}' not found in current directory.")
                continue
            if os.path.isdir(os.getcwd() + r'/' + f) and f[-1] != '/':
                prog_print(f'{f}: directories require an additional \'/\'')
                continue
            response = subprocess.run(
                ['rsync', '-aciv', os.getcwd() + r'/' + f,
                    CSE + r'/' + FOLDER + r'/' + f],
                capture_output=True,
                encoding='utf-8').stdout
            if response:
                print('uploading', f'\'{f}\' to', f'\'{FOLDER}\'')
                display_output(response)
            else:
                print(f'no changes to \'{f}\'')
    elif command['a']:
        prompt = f'{pargs[0]} autotest {pargs[1]}'
        output = cse_run(f'COMP; cd {FOLDER}; ' + prompt)
        if command['c']:
            output_file(prompt, output)
            return
        header_print(prompt)
        display_output(output)
        print(
            "  use 'cse -f' to ensure the latest file(s) " +
            "are uploaded to the cse servers."
        )
    elif command['s']:
        for c in pargs:
            response = cse_run(f'{c} classrun -sturec')
            header_print(f'{c} classrun -sturec')
            display_output(response)


def main() -> None:
    try:
        args = vars(parse_args())
        if args['debug']:
            print(args)
        is_valid, contains_flag = check_args(args)
        pargs = args['positional_args']
        if is_valid and contains_flag:
            process_flag(args)
        elif is_valid and not contains_flag and pargs:
            output = cse_run(' '.join(pargs))
            if args['c']:
                output_file(' '.join(pargs), output)
                return
            header_print(' '.join(pargs))
            display_output(output)
        elif not is_valid:
            return
        else:
            subprocess.run([argv[0], '-h'])
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
