#!/usr/bin/env python3
"""Basic script to interact with cse servers."""

import argparse
import datetime
import json
import os
import subprocess
import sys

from helper import DATEFRMT, color_print, header_print, prog_print

try:
    from dotenv import dotenv_values
except ImportError:
    sys.exit("%s: python-dotenv is required." %
             (os.path.basename(sys.argv[0])))


def parse_args() -> None:
    """Command line argument parser."""
    parser = argparse.ArgumentParser(
        allow_abbrev=False,
        exit_on_error=True,
        description='Utility to interact with cse servers')

    parent_flags = argparse.ArgumentParser(add_help=False)
    parent_flags.add_argument('-c',
                              '--copy',
                              action='store_true',
                              help='copy output to a "cse.out" file')
    parent_flags.add_argument('-d',
                              '--debug',
                              action='store_true',
                              help=argparse.SUPPRESS)

    run_parse = argparse.ArgumentParser(add_help=False)
    group_run = run_parse.add_mutually_exclusive_group()
    group_run.add_argument('-a',
                           nargs=2,
                           metavar=(
                               '<class_name>',
                               '<test>',
                           ),
                           help='run autotest')

    group_run.add_argument(
        '-s',
        action='store_true',
        help='request student record',
    )
    run_parse.add_argument('positional_args', nargs='*')

    sync_parse = argparse.ArgumentParser(add_help=False)
    group_sync = sync_parse.add_mutually_exclusive_group()
    group_sync.add_argument('-f',
                            action='store_true',
                            help='force update to cse folder')
    group_sync.add_argument('-u',
                            action='store_true',
                            help='sync cse folder with local')

    subp = parser.add_subparsers(dest='subcommand', help=False)
    run = subp.add_parser('run',
                          parents=[parent_flags, run_parse],
                          help='run a cse command')
    run.set_defaults(func=cse_run)
    sync_parse.add_argument('positional_args', nargs='*')
    sync = subp.add_parser('sync',
                           parents=[parent_flags, sync_parse],
                           help='sync a folder with cse')
    sync.set_defaults(func=cse_sync)

    return parser.parse_args()


def display_output(lines: str) -> None:
    """Display received response from cse servers."""
    for _ in lines.split('\n'):
        print(' ', _)


def output_file(*args: tuple) -> None:
    """Create cse.out file."""
    time = datetime.datetime.now().strftime(DATEFRMT)
    with open(f'{os.getcwd()}/cse.out', 'w') as f:
        print(time, file=f)
        for _ in args:
            print(_, file=f)
    print('output saved to \'cse.out\'')


def cse_execute(line: str) -> str:
    """Execute cse server commands."""
    if IN_CSE_FOLDER and FOLDER:
        line = ['ssh', 'cse', f'COMP; cd {FOLDER}; ' + line]
    else:
        line = ['ssh', 'cse', f'COMP; {line}']
    try:
        response = subprocess.run(line,
                                  capture_output=True,
                                  encoding='utf-8',
                                  timeout=TIMEOUT)
        message = response.stdout
        if not message:
            message = response.stderr
    except subprocess.TimeoutExpired:
        message = "timed out"
    return message


def cse_run(*args) -> None:
    flagc, flaga, flags, pos_args = args
    if not pos_args and not flaga and not flags:
        prog_print('no arguments provided')
        return
    if flaga:
        prompt = f'{flaga[0]} autotest {flaga[1]}'
        output = cse_execute(f'COMP; cd {FOLDER}; ' + prompt)
        if flagc:
            output_file(prompt, output)
            return
        header_print(prompt)
        display_output(output)
        print("  use 'cse sync' to ensure the latest file(s) " +
              "are uploaded to the cse servers.")
    elif flags:
        if not pos_args:
            prog_print('expected arguments [ list ... <class>]')
            return
        output = ''
        for c in pos_args:
            response = cse_execute(f'{c} classrun -sturec')
            if flagc:
                output = output + '\n' + response
                continue
            header_print(f'{c} classrun -sturec')
            display_output(response)
        if flagc:
            output_file()
            with open('cse.out', 'a') as f:
                print(output, f)
    else:
        header_print(' '.join(pos_args))
        output = cse_execute(' '.join(pos_args))
        display_output(output)
        if flagc:
            output_file(output)


def cse_sync(*args) -> None:
    flagc, flagf, flagu, pos_args = args
    if flagu:  # syncs cse ==> local
        for course in pos_args:
            local_path = f"{configuration.get('LOCAL_PATH')}/"
            if os.path.exists(local_path):
                response = subprocess.run([
                    "rsync",
                    "-ai",
                    f"{configuration.get('CSE_LOCAL_PATH')}/{course}",
                    local_path,
                ],
                                          capture_output=True,
                                          encoding="utf-8")
                print(response.stdout)
            else:
                prog_print(f"'{course}' does not exist on local")
        return
    for f in pos_args:  # syncs local ==> cse
        if not os.path.exists(os.getcwd() + r'/' + f):
            prog_print(f"'{f}' not found in current directory.")
            continue

        cwd = os.getcwd().replace(os.path.expanduser('~') + '/unsw/cse', '')
        cse_path = CSE + cwd
        if os.path.isfile(f):
            cse_path = cse_path + f'/{f}'
        response = subprocess.run(['rsync', '-acin', f, cse_path],
                                  capture_output=True,
                                  encoding='utf-8').stdout
        if response:
            color_print(f'==> uploading \'{f}\'')
            display_output(response)
            response = ''
            process = False
            if not flagf and input('==> process? ') in ('yes', 'y', 'Yes'):
                process = True
                response = subprocess.run(['rsync', '-aciv', f, cse_path],
                                          capture_output=True,
                                          encoding='utf-8').stdout
            if flagf:
                process = True
                response = subprocess.run(['rsync', '-aciv', f, cse_path],
                                          capture_output=True,
                                          encoding='utf-8').stdout
            if process and response:
                color_print(f'==> uploading \'{f}\'')
                display_output(response)
                if process and not response:
                    color_print(f'==> {f} is up to date')

        else:
            print(f'no changes to \'{f}\'')


configuration = dotenv_values(os.path.expandvars("$HOME") + '/.config/.env')
if configuration:
    FOLDER = os.getcwd().replace(
        configuration.get('CSE_LOCAL_PATH'),
        '') if configuration.get('CSE_LOCAL_PATH') else None
    CSE = configuration.get('CSE_PATH') if configuration.get(
        'CSE_PATH') else None
    IN_CSE_FOLDER: bool = os.getcwd() != FOLDER
    if not (FOLDER):
        sys.exit("%s: CSE_LOCAL_PATH missing from .env" %
                 (os.path.basename(sys.argv[0])))
    if not (CSE):
        sys.exit("%s: CSE_PATH missing from .env" %
                 (os.path.basename(sys.argv[0])))
else:
    sys.exit("%s: .env configuration file is required." %
             (os.path.basename(sys.argv[0])))

TIMEOUT: int = 5


def main() -> None:
    try:
        args = parse_args()
        _ = vars(args)
        flags = (_[k] for k in filter(
            lambda a: a not in ('func', 'debug', 'subcommand'), _.keys()))
        if args.subcommand == 'sync' or args.subcommand == 'run':
            if args.debug:
                color_print("  ==> Debugging information: ")
                for k, it in vars(args).items():
                    print(f'  {k}:', it)
            args.func(*flags)
        else:
            subprocess.run(['cse', '-h'])
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
