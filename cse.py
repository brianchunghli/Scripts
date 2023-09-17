#!/usr/bin/env python3
"""Basic script to interact with cse servers."""

import argparse
import datetime
import json
import os
import subprocess
import sys
import regex as re
import time

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
    parent_flags.add_argument('--debug',
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
    group_sync.add_argument(
        '-f',
        action='store_true',
        help='force from local environment to cse environment')
    group_sync.add_argument('-d',
                            action='store_true',
                            help='sync from cse to local environment')

    subp = parser.add_subparsers(dest='subcommand', help=False)
    run = subp.add_parser('run',
                          parents=[parent_flags, run_parse],
                          help='run a cse command')
    run.set_defaults(func=cse_run)
    sync_parse.add_argument('positional_args', nargs='*')
    sync = subp.add_parser(
        'sync',
        parents=[parent_flags, sync_parse],
        help='sync files or directories between local and cse environment')
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
    print('  output saved to \'cse.out\'')


def execute_and_stream(command: list) -> str:
    response = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding='utf-8',
    )
    start_time = time.time()
    output = ""
    while response.stdout.readable():
        if time.time() - start_time >= TIMEOUT:
            output = "request timed out"
            response.kill()
            break
        line = response.stdout.readline()
        output += line
        if not line:
            break
        print(' ', line.strip())
    print()
    return output, response.returncode == 0


def cse_execute(line: str):
    """Execute cse server commands."""
    header_print(line)
    if IN_CSE_FOLDER and FOLDER:
        line = ['ssh', 'cse', f'COMP; cd {FOLDER.lstrip("/")}; ' + line]
    else:
        line = ['ssh', 'cse', f'COMP; {line}']
    output, success = execute_and_stream(line)
    return output, success


def cse_run(args) -> None:
    flagc, flaga, flags, pos_args = args
    if not pos_args and not flaga and not flags:
        prog_print('no arguments provided')
        return
    if flaga:
        prompt = f'{flaga[0]} autotest {flaga[1]}'
        output, success = cse_execute(prompt)
        if flagc:
            output_file(prompt, output)
            return
        print("  use 'cse sync' to ensure the latest file(s) " +
              "are uploaded to the cse servers.")
    elif flags:
        if not pos_args:
            prog_print('expected arguments [ list ... <class> ]')
            return
        output = ''
        for c in pos_args:
            response, success = cse_execute(f'{c} classrun -sturec')
            if flagc:
                output = output + '\n' + response
                continue
        if flagc:
            output_file()
            with open('cse.out', 'a') as f:
                print(output, f)
    else:
        output, success = cse_execute(' '.join(pos_args))
        if flagc:
            output_file(output)


def is_directory(files, filename):
    """Filters the the output of ls -al from subprocess to check for 
       whether the specified file is a directory"""
    is_directory = False
    for f in files:
        line = f.split()
        if line[0][0] == 'd' and line[-1] == filename:
            is_directory = True
    return is_directory


def exists(files, filename):
    """Checks the output of ls -al from subprocess to see if a file matching
       the filename is found"""
    exists = False
    for f in files:
        if f.split()[-1] == filename:
            exists = True
    return exists


def cse_sync(args) -> None:
    flagc, flagf, flagd, pos_args = args

    if flagd:  # syncs a cse file or directory ==> local
        cwd = os.getcwd().replace(
            os.path.expandvars('$HOME') + '/unsw/cse', '')
        for item in pos_args:
            base_path = configuration.get('CSE_LOCAL_PATH')
            course_path = f"{base_path}{cwd}/{item}"
            cse_course_path = f"{configuration.get('CSE_PATH')}{cwd}/{item}"

            # check if directory
            dir_files = list(
                filter(lambda x: x != '',
                       cse_execute('ls -al')[0].split('\n')))

            # rsync will otherwise sync the directory as a sub directory
            if is_directory(dir_files, item):
                cse_course_path += "/"
                course_path += "/"

            command = [
                "rsync",
                "-ani",
                cse_course_path,
                course_path,
            ]
            response = subprocess.run(command,
                                      capture_output=True,
                                      encoding='utf-8').stdout
            if response:
                color_print(
                    f'==> downloading \'{item}\' from cse to local computer:')
                display_output(response)
                if not flagf and input('==> process? ') in ('yes', 'y', 'Yes'):
                    command = [
                        "rsync",
                        "-avi",
                        cse_course_path,
                        course_path,
                    ]
                    response, success = execute_and_stream(command)
            else:
                prog_print(f'no changes to \'{item}\'.' if exists(
                    dir_files, item) else f'\'{item}\' does not exist.')
        return

    for f in pos_args:  # syncs a local file or directory ==> cse
        if not os.path.exists(os.getcwd() + r'/' + f):
            prog_print(f"'{f}' not found in current directory.")
            continue

        cwd = os.getcwd().replace(os.path.expanduser('~') + '/unsw/cse', '')
        cse_path = CSE + cwd
        if os.path.isfile(f):
            cse_path = cse_path + f'/{f}'

        command = ['rsync', '-acin', f, cse_path]
        response = subprocess.run(command,
                                  capture_output=True,
                                  encoding='utf-8').stdout
        if response:
            color_print(f'==> uploading \'{f}\' from local computer to cse:')
            display_output(response)
            response = ''
            success = 1
            process = False
            if not flagf and input('==> process? ') in ('yes', 'y', 'Yes'):
                process = True
                color_print(f'==> uploading \'{f}\'')
                response, success = execute_and_stream(
                    ['rsync', '-aciv', f, cse_path])
            if flagf:
                process = True
                color_print(f'==> uploading \'{f}\'')
                response, success = execute_and_stream(
                    ['rsync', '-aciv', "--exclude 'target'", f, cse_path])

            if success != 0 and process:
                color_print(f'==> {f} is up to date')

        else:
            print(f'no changes to \'{f}\'')


configuration = dotenv_values(os.path.expandvars("$HOME") + '/.config/.env')
if configuration:

    if not (configuration.get('CSE_LOCAL_PATH')):
        sys.exit("%s: CSE_LOCAL_PATH missing from .env" %
                 (os.path.basename(sys.argv[0])))
    FOLDER = os.getcwd().replace(
        configuration.get('CSE_LOCAL_PATH'),
        '') if configuration.get('CSE_LOCAL_PATH') else None
    CSE = configuration.get('CSE_PATH') if configuration.get(
        'CSE_PATH') else None
    IN_CSE_FOLDER: bool = os.getcwd() != FOLDER
    if not (CSE):
        sys.exit("%s: CSE_PATH missing from .env" %
                 (os.path.basename(sys.argv[0])))
else:
    sys.exit("%s: .env configuration file is required." %
             (os.path.basename(sys.argv[0])))

TIMEOUT: int = 60


def main() -> None:
    try:
        args = parse_args()
        _ = vars(args)
        flags = (_[k] for k in filter(
            lambda a: a not in ('func', 'debug', 'subcommand'), _.keys()))
        if args.debug:
            color_print("  ==> Debugging information: ")
            for k, it in vars(args).items():
                print(f'  {k}:', it)
        args.func(flags)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
