#!/usr/bin/env python3
import argparse
import os
import subprocess
import textwrap
from typing import Tuple

from localutils.printing import prog_print

'''
Basic script used to create c/c++, python, shell, make and cmake files.
'''


ACCEPTED_FILES = ('c', 'cpp', 'py', 'sh', 'zsh', 'cmake', 'make')


def parseArguments() -> argparse.Namespace:
    '''
    Parses command line arguments
    '''
    global ACCEPTED_FILES

    parser = argparse.ArgumentParser(
        allow_abbrev=False,
        exit_on_error=True,
        description="Utility for file generation",
    )
    parser.add_argument('file_type', choices=ACCEPTED_FILES,
                        help='filetype to be generated')
    parser.add_argument('file_name', nargs='+',
                        help='new program file and related dependencies')
    parser.add_argument('-f', '--subtype', default='cpp', choices=('c', 'cpp'),
                        help=argparse.SUPPRESS)
    parser.add_argument('-d', '--debug', action='store_true',
                        help=argparse.SUPPRESS)
    return parser.parse_args()


def gen_makefile_and_cmakefile(args: dict) -> str:
    filename = args['file_name'][0]
    suffix = args['subtype']
    file_contents = ''
    standard = '20'
    dep_files = ''
    if suffix == 'c':
        standard = 'c99'
    if args['file_name'][1:]:
        dep_files = ' ' + ' '.join(
            (f'{f}.{suffix}' if len(f.split('.')) == 1
             else f for f in args['file_name'][1:]))
    if args['file_type'] == 'cmake':
        if not os.path.exists(os.getcwd() + 'r/build'):
            subprocess.run(['mkdir', 'build'], capture_output=True)
        # CMakeLists file details
        file_contents = textwrap.dedent(f"""\
        # options
        cmake_minimum_required(VERSION 3.18.4)
        project({filename})
        set(CMAKE_CXX_STANDARD {standard})
        set(CMAKE_EXPORT_COMPILE_COMMANDS ON)\n
        add_compile_options(-Wall -Werror -std={standard})
        add_executable({filename} {filename}.{suffix}{dep_files})
        """)
    else:
        # based on
        # https://stackoverflow.com/questions/1950926/create-directories-using-make-file
        compiler = 'g++'
        standard = 'c++' + standard
        if suffix == 'c':
            compiler = 'gcc'
            standard = 'c99'
        compile_command = r'${CC} ${CFLAGS}'
        file_contents = textwrap.dedent(f"""\
        CC = {compiler} 
        CFLAGS = -Wall -Werror -std={standard}
        MKDIR_P := mkdir -p
        OUT_DIR := build

        .PHONY: {filename} clean
        {filename}: $(OUT_DIR)/{filename}
        $(OUT_DIR):
        \t$(MKDIR_P) $(OUT_DIR)
        $(OUT_DIR)/{filename}: {filename}.{suffix}{dep_files} | $(OUT_DIR) 
        \t{compile_command} -o $(OUT_DIR)/{filename} {filename}.{suffix}{dep_files}
        clean:
        \trm -rf $(OUT_DIR)
        """)
    return file_contents


def generate_file(args: dict) -> str:
    """
    Generates the file contents for the
    file.
    """
    contents: str = ''
    filetype = args['file_type']
    if filetype in ["c", "cpp"]:
        header = '#include <stdio.h>\n#include <stdlib.h>\n\n'
        main = 'int main(int argc, char* argv[]) {\n\n  return 0;\n}'
        if filetype == 'cpp':
            header = '#include <iostream>\n\n'
            main = main.replace('int argc', 'const int argc')
            main = main.replace('char*', 'const char *const')
        contents = header + main
    elif filetype == "py":
        contents = textwrap.dedent("""\
        #!/usr/bin/env python3\n\n
        def main() -> None:
            pass\n\n
        if __name__ == '__main__':
            main()
        """)
    elif filetype in ["sh", "zsh"]:
        contents = f"#!/bin/{filetype}\n"
    elif filetype in ["cmake", "make"]:
        success, message = check_args(args)
        if not success:
            prog_print(message)
            return ''
        contents = gen_makefile_and_cmakefile(args)
    return contents


def check_args(args: dict) -> Tuple[bool, str]:
    '''
    Check validity of arguments
    '''
    success = True
    err_message = ''
    filetype, filename = args['file_type'], args['file_name'][0]
    if filetype == 'cmake' or filetype == 'make':
        suffix = args['subtype']
        if '.cpp' in filename or '.c' in filename:
            success = False
            err_message = f'Remove suffix from \'{filename}\''
        elif not os.path.exists(os.getcwd() + f'/{filename}.{suffix}'):
            success = False
            err_message = f'\'{filename}.{suffix}\' not found in current directory'
    return success, err_message


def main() -> None:
    opts = vars(parseArguments())
    if opts['debug']:
        print(opts)
    file_contents = generate_file(opts)
    new_file, suffix = opts['file_name'][0], opts['file_type']
    if not file_contents:
        prog_print('no file generated.. check program')
        return
    filename = f"{new_file}.{suffix}"
    if os.path.exists(os.path.abspath(filename)):
        message: str = f"File exists. Replace {os.path.basename(filename)}? "
        if input(message) not in ("yes", 'y'):
            print("file creation aborted")
            return
    if suffix == 'cmake':
        filename = 'CMakeLists.txt'
    if suffix == 'make':
        filename = 'Makefile'
    with open(filename, "w") as w:
        w.write(file_contents)
    if suffix in ["zsh", "sh", "py"]:
        subprocess.run(
            ["chmod", "+x", filename])
    if suffix == 'cmake':
        subprocess.run(['cmake', '-S', '.', '-B', 'build/'])
    print(f"{filename} created.")


if __name__ == "__main__":
    main()
