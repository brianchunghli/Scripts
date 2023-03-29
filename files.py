#!/usr/bin/env python3
"""Basic file factory.

file factory for c/c++, python, shell, make and cmake files.
"""

import argparse
import json
import os
import subprocess
import sys
from typing import Tuple

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
    print(f'{os.path.basename(sys.argv[0])}: {msg}', **kwargs)


def parse_arguments() -> dict:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        allow_abbrev=False,
        exit_on_error=True,
        description="Basic file factory.",
    )
    subp = parser.add_subparsers(dest='filetype',
                                 title='subcommands',
                                 required=True)

    main_flags = argparse.ArgumentParser(add_help=False)
    main_flags.add_argument('file_name',
                            nargs='+',
                            help='<program file>, list <dependencies...>')
    main_flags.add_argument('-d',
                            '--debug',
                            action='store_true',
                            help='print debugging related information')
    main_flags.add_argument('-p',
                            '--path',
                            nargs=1,
                            help='provide a path to the configuration file')
    # python files
    subp.add_parser('py',
                    parents=[main_flags],
                    help='file generator for py files')
    # make/cmake files
    make_flags = argparse.ArgumentParser(add_help=False)
    make_flags.add_argument('-std',
                            '--standard',
                            nargs=1,
                            type=str,
                            metavar='<std>',
                            help='set standard for compilation')
    make_flags.add_argument('-f',
                            '--flags',
                            nargs=1,
                            type=str,
                            help='replaces compiler flags')
    subp.add_parser('make',
                    parents=[main_flags, make_flags],
                    help='file generator for cmake files')
    cmake = subp.add_parser('cmake',
                            parents=[main_flags, make_flags],
                            help='file generator for make files')
    cmake.add_argument('-t',
                       '--tests',
                       action='store_true',
                       help='allow for testing')
    # c/cpp files
    c_flags = argparse.ArgumentParser(add_help=False)
    c_flags.add_argument('-m',
                         '--main',
                         action='store_true',
                         help='include argc and argv in main')
    subp.add_parser('c',
                    parents=[main_flags, c_flags],
                    help='file generator for c files')
    cpp = subp.add_parser('cpp',
                          parents=[
                              main_flags,
                              c_flags,
                          ],
                          help='file generator for cpp files')
    cpp.add_argument('-cp',
                     '--competitive',
                     action='store_true',
                     help='competitive programming template')
    # zsh/shell files
    subp.add_parser('sh',
                    parents=[main_flags],
                    help='file generator for sh files')
    subp.add_parser('zsh',
                    parents=[main_flags],
                    help='file generator for zsh files')

    return vars(parser.parse_args())
# re-factor into:
#   ** basic check
#   ** cmake / make file check
#   ** c++ file check
def check_args(args: dict) -> Tuple[bool, str]:
    """Check validity of arguments."""
    success = True
    err_message = ''
    filetype, filename = args['filetype'], args['file_name'][0]
    has_suffix = filename.split('.')
    try:
        if len(has_suffix) == 2 and filetype not in ('cmake', 'make'):
            err_message = f'extraneous suffix \'{has_suffix[1]}\''
            success = False
        elif not CONFIG[filetype]:
            err_message = f'no configuration found for \'{filetype}\''
            success = False
        elif filetype == 'cmake' or filetype == 'make':
            suffix = filename.split('.')
            if len(suffix) != 2:
                success = False
                err_message = f'invalid file \'{filename}\''
                return success, err_message
            if suffix[1] != 'cpp' and suffix[1] != 'c' and success:
                success = False
                err_message = f'invalid file \'{filename}\''
            if not os.path.exists(os.getcwd() + f'/{filename}') and success:
                success = False
                err_message = f'\'{filename}\' cannot be found in current directory'
            if suffix[1] == 'c' and args['tests'] and success:
                success = False
                err_message = 'catch2 cannot be run with c files'
            if args['standard']:
                subtype = filename.split('.')[1]
                if subtype == 'cpp':
                    if args['standard'][0] not in ('11', '17', '20'):
                        success = False
                        err_message =\
                            f'\'{args["standard"][0]}\'' +\
                        f' is not a valid standard for {subtype}.'
                elif args['standard'][0] not in ('99'):
                    success = False
                    err_message =\
                        f'\'{args["standard"][0]}\' is not a valid standard for c.'
    except KeyError:
        success = False
        err_message = f'no configuration found for \'{filetype}\''
    return success, err_message


def cmake_factory(args: dict, file_content: dict) -> str:
    """Generate a cmake file."""
    filename, suffix = args['file_name'][0].split('.')
    contents = ''.join(file_content['cmake']['p1'])
    if args['tests']:
        contents = contents.replace('add_executable(main $FILENAME.$SUFFIX)',
                                    ''.join(file_content['cmake']['tests']))
    contents = contents.replace('$FILENAME',
                                filename).replace('$SUFFIX', suffix)
    if args['standard']:
        contents = contents.replace('c++20', 'c++' + args['standard'])
    if suffix == 'c':
        contents = contents.replace('set(CMAKE_CXX_STANDARD 20)',
                                    'set(CMAKE_CXX_STANDARD 99)')
        if args['standard']:
            contents = contents.replace('c99', 'c' + args['standard'])
    return contents


def generate_file(args: dict, file_content: dict) -> str:
    """Generate the file contents for the file."""
    contents: str = ''
    success, message = check_args(args)

    if not success:
        prog_print(message)
        return contents
    file_t = args['filetype']
    if file_t == 'py':
        contents = ''.join(file_content['py']['p1'])
    if file_t == 'c' or file_t == 'cpp':
        if file_t == 'c':
            c = file_content['c']
            contents = ''.join(c['p1'])
            if args['main']:
                contents = ''.join(c['p2'])
        else:
            cpp = file_content['cpp']
            contents = ''.join(cpp['p1'])
            if args['competitive']:
                contents = "".join(cpp["p2.m"]) if args["main"] else "".join(
                    cpp["p2"])
            elif args['main']:
                contents = ''.join(cpp['p1.m'])
    if file_t == 'sh' or file_t == 'zsh':
        contents = file_content[file_t]['p1']
    if file_t == 'make':
        # not yet implemented
        # flags
        filename, suffix = args['file_name'][0].split('.')
        contents = ''.join(file_content['make'][f'p1.{suffix}'])
        contents = contents.replace('$FILENAME',
                                    filename).replace('$SUFFIX', suffix)
        if args['standard']:
            contents = contents.replace('c++20', f'c++{args["standard"][0]}')

    if file_t == 'cmake':
        contents = cmake_factory(args, file_content)
    return contents


dir_path = os.getcwd().split('/')
path_length = len(dir_path)
configuration_found = False
while path_length > 1:
    curr_files = os.listdir('/'.join(dir_path))
    if 'src' in curr_files:
        config_local = '/'.join(dir_path) + '/src/.files'
        if os.path.exists(config_local):
            configuration_found = True
            with open(config_local) as f:
                CONFIG = json.load(f)
    elif '.config' in curr_files:
        config_global = '/'.join(dir_path) + '/.config/.files'
        if os.path.exists(config_global):
            configuration_found = True
            with open(config_global) as f:
                CONFIG = json.load(f)
    dir_path.pop(-1)
    path_length = len(dir_path)
if not configuration_found:
    prog_print("missing configuration file")
    sys.exit(0)


def main() -> None:
    opts = parse_arguments()
    if not configuration_found and not opts['path']:
        prog_print("missing configuration file")
        return
    if opts['path']:
        print()
    if opts['debug']:
        color_print('Provided arguments:')
        for arg in opts:
            print(f'{arg}:', opts[arg])
    file_contents = generate_file(opts, CONFIG)
    new_file, suffix = opts['file_name'][0], opts['filetype']
    if not file_contents:
        return
    filename = f"{new_file}.{suffix}"
    message = f'File exists. Replace {os.path.basename(filename)}? '
    if os.path.exists(
            os.path.abspath(filename)) and input(message) not in ('yes', 'y',
                                                                  'Yes'):
        print("file creation aborted")
        return
    name_conversion = {
        "cmake": "CMakeLists.txt",
        "make": "Makefile",
    }
    if suffix == 'cmake' or suffix == 'make':
        filename = name_conversion.get(suffix)
    with open(filename, "w") as w:
        w.write(file_contents)
    if suffix in ["zsh", "sh", "py"]:
        subprocess.run(["chmod", "+x", filename])
    if suffix == 'cmake':
        build_folder = False
        build_test = False
        if not os.path.exists(os.getcwd() + 'r/build'):
            subprocess.run(['mkdir', 'build'], capture_output=True)
            build_folder = True
        if opts['tests']:
            build_tests = True
            if not os.path.exists(os.getcwd() + '/lib'):
                subprocess.run(['cp', '-r', CONFIG['catch2'], '.'])
            if not os.path.exists(os.getcwd() + '/src'):
                subprocess.run(['mkdir', 'src'])
            os.rename(os.getcwd() + f'/{new_file}',
                      os.getcwd() + f'/src/{new_file}')
            fname, fsuffix = new_file.split('.')
            testfile = new_file.replace(fsuffix, f'test.{fsuffix}')
            with open(os.getcwd() + f'/src/{testfile}', 'a') as f:
                print(f'#include \"{fname}.{fsuffix.replace("c", "h")}\"',
                      file=f)
                print('#include "catch2/catch.hpp"', file=f)
                print(file=f)
            with open(
                    os.getcwd() + f'/src/{fname}.{fsuffix.replace("c", "h")}',
                    'w') as f:
                pass
        subprocess.run(['cmake', '-S', '.', '-B', 'build/'])
    print(f"{filename} created.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        prog_print('\nkeyboard interrupted.')
