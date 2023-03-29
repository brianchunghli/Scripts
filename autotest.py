#!/usr/bin/env python3
"""Autotest.

Autotester for python, rust and c/c++ scripts.

"""

import argparse
import datetime
import filecmp
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
from sys import argv

from localutils.printing import color_print, prog_print

# static global variables
CURRENT_FOLDER: str = os.getcwd()
TEST_FOLDER_EXISTS: bool = os.path.exists(CURRENT_FOLDER + r'/tests')
SOLUTIONS_FOLDER_EXISTS: bool = os.path.exists(CURRENT_FOLDER + r'/solutions')
DATEFRMT: str = '%d %B %Y %H:%M:%S'
TIMEOUT: int = 5
# global variable structures
NO_SOLUTIONS: list[str] = []


def parse_args() -> None:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        allow_abbrev=False,
        exit_on_error=True,
        description='Autotesting script for rust, python and c files.')

    filetypes = ('r', 'py', 'c')

    parser.add_argument('-f',
                        '--file',
                        choices=filetypes,
                        default=None,
                        help='set filetype for autotest')
    parser.add_argument('-i',
                        '--input',
                        action='store_true',
                        default=False,
                        help='set input stream for program')
    parser.add_argument('-o',
                        '--output',
                        action='store_true',
                        help='display output only')
    parser.add_argument('-v',
                        '--verbose',
                        action='store_true',
                        help='display all output')
    parser.add_argument('-c',
                        '--copy',
                        action='store_true',
                        help='copy output to p.out')
    parser.add_argument('-t',
                        '--testcases',
                        action='store_true',
                        default=False,
                        help='execute tests in test folder')
    parser.add_argument('-F',
                        '--filter',
                        metavar='<folder>',
                        nargs=1,
                        help='filter folder')
    parser.add_argument('-T',
                        '--timeout',
                        metavar='<integer>',
                        nargs=1,
                        help='set custom timeout')
    parser.add_argument('positional_args', nargs='*')
    return parser.parse_args()


def check(commands: dict) -> bool:
    """Conduct input check."""
    passed_check = True
    pargs = commands['positional_args']
    if commands['testcases'] and not TEST_FOLDER_EXISTS:
        prog_print('the -t flag requires a \'tests\' directory.')
        return False
    if not commands['testcases'] and not (commands['input']
                                          or commands['output']):
        prog_print(
            'running programs without input require the use of the -o flag.')
        return False
    if not pargs:
        subprocess.run([argv[0], '-h'])
        passed_check = False
    elif commands['file'] != 'r' and len(pargs) < 2:
        if not os.path.exists(pargs[0]):
            prog_print('missing program file')
            passed_check = False
        elif not commands['testcases'] and not commands['output']:
            prog_print('expected positional arguments: <program> <test_file>')
            passed_check = False
    if commands['file'] == 'r':
        if len(pargs) < 1 and not commands['testcases']:
            prog_print('expected positional arguments: <test_file>')
            passed_check = False
    elif commands['file'] and pargs[0].split('.')[1] != commands['file']:
        prog_print('Invalid program filetype provided')
        passed_check = False
    return passed_check


def run_test(commands: dict, folder: str) -> bool:
    """Execute test run."""
    global NO_SOLUTIONS
    global TIMEOUT
    pargs = commands['positional_args']
    filetype = commands['file']
    # check filetype
    run_test = [f'./{pargs[0]}'] if '/' not in pargs[0] else [pargs[0]]
    if filetype == 'r':
        run_test = ['cargo', 'run']
    run_test.extend(pargs[1:])  # uses pargs as cli options
    try:
        if commands['input']:
            with open(folder, 'rb') as f:
                data = f.read()
            output = subprocess.run(run_test,
                                    capture_output=True,
                                    input=data,
                                    timeout=TIMEOUT)
        else:
            output = subprocess.run(run_test,
                                    capture_output=True,
                                    timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        print('timed out')
        return

    solution = ''
    testfile = '/'.join(folder.split('/')[-2:])
    solve = folder.replace('/tests', '/solutions')
    if os.path.exists(solve) and solve != folder:
        with open(solve, 'rb') as f:
            solution = f.read()
    if output.stdout and solution:
        with tempfile.NamedTemporaryFile() as program_output:
            program_output.write(output.stdout)
            with tempfile.NamedTemporaryFile() as expected_solution:
                expected_solution.write(solution)
                if filecmp.cmp(program_output.name, expected_solution.name):
                    color_print('Test passed!')
                else:
                    color_print('Test failed.', 'r')
    elif not output.stderr:
        NO_SOLUTIONS.append(testfile)
        print('..')
    output = output.stderr if output.stderr else output.stdout
    if commands['output'] or folder is None:
        if not testfile:
            testfile = f'./{pargs[0]}' if '/' not in pargs[0] else pargs[0]
        if solution:
            color_print(f'\nProgram output ({testfile}):', 'y')
            print('\n' + output.decode())
            color_print(f'Expected solution ({testfile}):', 'y')
            print('\n' + solution.decode())
        else:
            if commands['verbose'] or not commands['input']:
                color_print(f'\nProgram output ({testfile}):', 'y')
                print('\n' + output.decode())
    if commands['copy']:
        with open('p.out', 'a') as f:
            color_print(' '.join(run_test) + f' {testfile}', 'y', file=f)
            print(output.decode(), file=f)


def batch_test(commands: dict) -> None:
    """Execute a batch of tests in tests directory."""
    global NO_SOLUTIONS
    if commands['file'] == 'r':
        program = f'cargo run {os.path.basename(os.getcwd())}'
    else:
        program = f"{commands['positional_args'][0]}"
        if '/' not in commands['positional_args'][0]:
            program = f"./{commands['positional_args'][0]}"
    count = 1
    if commands['filter']:
        filter_folders = set(commands['filter'])
        print(filter_folders)
    for file in glob.glob(CURRENT_FOLDER + r'/tests/*'):
        if commands['filter'] and not filter_folders.intersection(
                file.split('/')[-2:]):
            continue
        if os.path.isdir(file):
            # realistically, I won't exceed three digits...
            for file2 in sorted(
                    glob.glob(file + r'/*'),
                    key=lambda x: int(re.sub(r'[a-zA-Z]*', '', x[-3:]))):
                print(
                    f'test {count}: ({program} <{"/".join(file2.split("/")[-2:])});',
                    end=' ')
                run_test(commands, file2)
                count += 1
        else:
            print(f'test {count}: ({program} <{os.path.basename(file)});',
                  end=' ')
            run_test(commands, file)
            count += 1
    if SOLUTIONS_FOLDER_EXISTS and NO_SOLUTIONS:
        color_print('\nNo solutions were found for:', 'r')
        for _ in NO_SOLUTIONS:
            color_print(f'  {_}', 'r')
        print()
        if not commands['output']:
            print('Done. Use the -o flag to see program output(s)')


def file_test(commands: dict) -> None:
    """Execute individual tests provided by the user."""
    pargs = commands['positional_args']
    if commands['file'] == 'r':
        # must supply at least one test file
        index_start = 0
        program = f'cargo run (../{os.path.basename(os.getcwd())})'
    else:
        # py, c files
        # must supply program and test file(s)
        index_start = 1
        program = f'./{pargs[0]}'
        if '/' in pargs[0]:
            program = pargs[0]
    if commands['input']:
        if not pargs[index_start:]:
            prog_print('expected inputs <list [ files... ]>')
            return
        for i, f in enumerate(pargs[index_start:], 1):
            file_exists = os.path.isfile(f)
            if file_exists:
                print(f'test {i}: ({program} <{f});', end=' ')
                run_test(commands, CURRENT_FOLDER + f'/{f}')
            else:
                print(
                    f'file \'{os.path.basename(f)}\' not found in current directory.',
                )
    elif commands['output']:
        print(f'{program};', end=' ')
        run_test(commands, '')


def main() -> None:
    global TIMEOUT
    try:
        args = vars(parse_args())
        # print(args)
        if not check(args):
            return
        # input and multiple files
        if args['timeout']:
            TIMEOUT = int(args['timeout'])
        if args['copy']:
            with open('p.out', 'w') as f:
                color_print('; '.join(
                    ('Autotest run',
                     datetime.datetime.now().strftime(DATEFRMT))),
                            'g',
                            file=f)
                print(file=f)
        if args['testcases']:
            # print('batch test')
            if not SOLUTIONS_FOLDER_EXISTS:
                print(
                    'Missing solutions folder. Running tests with outputs only...',
                )
            batch_test(args)
        # individual files
        else:
            # print('filetest')
            if args['output'] or args['input']:
                if args['output'] and not args['input']:
                    print(f'running \'{args["positional_args"][0]}\'' +
                          ' with commandline inputs: ',
                          end='')
                    color_print(f'{" ".join(args["positional_args"][1:])}')
                file_test(args)
        if args['copy']:
            print('\nprogram outputs written to \'p.out\'')
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('keyboard interrupted..')
        pass
