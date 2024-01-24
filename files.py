#!/usr/bin/env python3
"""Basic file generator.

file factory for c/c++, python, shell, make and cmake files.
"""

import os
import sys

try:
    from dotenv import dotenv_values
except ImportError:
    sys.exit("%s: the dotenv package is required." % (os.path.basename(sys.argv[0])))

import argparse
import json
import subprocess

from helper import color_print, prog_print


def parse_arguments() -> dict:
    """Command line arguments parser"""
    parser = argparse.ArgumentParser(
        allow_abbrev=False,
        exit_on_error=True,
        description="Basic file factory for c/c++, python, shell, make and cmake files",
    )
    subp = parser.add_subparsers(dest="filetype", title="subcommands", required=True)

    main_flags = argparse.ArgumentParser(add_help=False)
    main_flags.add_argument(
        "file_name",
        nargs="+",
        help="<program file>, list <dependencies...>",
    )
    main_flags.add_argument(
        "-d", "--debug", action="store_true", help="print debugging related information"
    )
    main_flags.add_argument(
        "-p", "--path", nargs=1, help="provide a path to the configuration file"
    )
    # python files
    subp.add_parser("py", parents=[main_flags], help="file generator for py files")
    # make/cmake files
    make_flags = argparse.ArgumentParser(add_help=False)
    make_flags.add_argument(
        "-std",
        "--standard",
        nargs=1,
        type=str,
        metavar="<std>",
        help="set standard for compilation",
    )
    make_flags.add_argument(
        "-f", "--flags", nargs=1, type=str, help="replaces compiler flags"
    )
    subp.add_parser(
        "make", parents=[main_flags, make_flags], help="file generator for cmake files"
    )
    cmake = subp.add_parser(
        "cmake", parents=[main_flags, make_flags], help="file generator for make files"
    )
    cmake.add_argument(
        "-t",
        "--tests",
        action="store_true",
        help="add testing features for cmake project",
    )

    cmake.add_argument(
        "--clean",
        action="store_true",
        help="remove cmake files",
    )

    # c/cpp files
    c_flags = argparse.ArgumentParser(add_help=False)
    c_flags.add_argument(
        "-m", "--main", action="store_true", help="include argc and argv in main"
    )
    subp.add_parser(
        "c", parents=[main_flags, c_flags], help="file generator for c files"
    )
    cpp = subp.add_parser(
        "cpp",
        parents=[
            main_flags,
            c_flags,
        ],
        help="file generator for cpp files",
    )
    cpp.add_argument(
        "-cp",
        "--competitive",
        action="store_true",
        help="competitive programming template",
    )
    # zsh/shell files
    subp.add_parser("sh", parents=[main_flags], help="file generator for sh files")
    subp.add_parser("zsh", parents=[main_flags], help="file generator for zsh files")

    return vars(parser.parse_args())


def basic_check(args: dict):
    """Check validity of arguments."""
    success = True
    err_message = ""
    file_t, file_n = args["filetype"], args["file_name"][0]
    has_suffix = file_n.split(".")
    # disallow suffixes in file creation
    if len(has_suffix) == 2 and file_t not in ("cmake", "make"):
        err_message = f"extraneous suffix '{has_suffix[1]}'"
        success = False
    # configuration must exist
    try:
        CONFIG[file_t]
    except KeyError:
        success = False
        err_message = f"no configuration found for '{file_t}'"
    # file must exist for cmake / make
    if not os.path.exists(os.getcwd() + f"/{file_n}") and file_t in ("cmake", "make"):
        success = False
        err_message = f"'{file_n}' not found in current directory"
    return success, err_message


def remove_all_files(path):
    if os.path.exists(path):
        for file_name in os.listdir(path):
            # construct full file path
            file = path + "/" + file_name
            if os.path.isfile(file):
                print("Deleting file:", file)
                os.remove(file)
        os.rmdir(path)


def cmake_factory(args: dict, file_content: dict) -> str:
    """Generate a cmake file."""
    contents = ""
    file_n = args["file_name"][0]
    if len(file_n.split(".")) != 2:
        prog_print(f"invalid file '{file_n}'")
        return contents

    if args["clean"]:
        remove_all_files(os.getcwd() + "/src")
        remove_all_files(os.getcwd() + "/build")
        remove_all_files(os.getcwd() + "/include")

    if os.path.exists(os.getcwd() + "/src"):
        prog_print(
            "existing cmake project exists. Remove all files before continuing.",
        )
        return contents

    filename, suffix = args["file_name"][0].split(".")

    if suffix not in ("c", "cpp"):
        prog_print(f"invalid file '{file_n}'")
        return contents

    contents = "".join(file_content["cmake"]["p1"])

    if args["tests"]:
        contents = contents.replace(
            "add_executable(main ${SRC_FILES})", "".join(file_content["cmake"]["tests"])
        )
    contents = contents.replace("$FILENAME", f"src/{filename}").replace(
        "$SUFFIX", suffix
    )

    if suffix == "cpp" and args["standard"]:
        contents = contents.replace("c++20", f"c++{args['standard']}")

    if suffix == "c":
        contents = contents.replace(
            "set(CMAKE_CXX_STANDARD 20)", "set(CMAKE_CXX_STANDARD 99)"
        )
        if args["standard"]:
            contents = contents.replace("c99", "c" + args["standard"])
    return contents


def generate_file(args: dict, file_content: dict) -> str:
    """Generate the file contents to be written."""
    contents: str = ""
    success, message = basic_check(args)
    if not success:
        prog_print(message)
        return contents

    try:
        file_t = args["filetype"]

        if file_t == "py":
            contents = "".join(file_content["py"]["p1"])

        if file_t == "c" or file_t == "cpp":
            if file_t == "c":
                c = file_content["c"]
                contents = "".join(c["p1"])
                if args["main"]:
                    contents = "".join(c["p2"])
            else:
                cpp = file_content["cpp"]
                contents = "".join(cpp["p1"])
                if args["competitive"]:
                    contents = (
                        "".join(cpp["p2.m"]) if args["main"] else "".join(cpp["p2"])
                    )
                elif args["main"]:
                    contents = "".join(cpp["p1.m"])

        if file_t == "sh" or file_t == "zsh":
            contents = file_content[file_t]["p1"]

        if file_t == "make":
            filename, suffix = args["file_name"][0].split(".")
            contents = "".join(file_content["make"][f"p1.{suffix}"])
            contents = contents.replace("$FILENAME", filename).replace(
                "$SUFFIX", suffix
            )
            if args["standard"]:
                contents = contents.replace("c++20", f'c++{args["standard"][0]}')

        if file_t == "cmake":
            contents = cmake_factory(args, file_content)
    except KeyError:
        prog_print(f"missing template for {file_t}")
        contents = ""

    return contents


CONFIG = {}
dir_path = os.getcwd().split("/")
path_length = len(dir_path)
if os.path.exists(os.path.expandvars("$HOME") + "/.config/files/files.json"):
    configuration_found = True
    with open(os.path.expandvars("$HOME") + "/.config/files/files.json") as f:
        CONFIG = json.load(f)
while path_length > 2 and not CONFIG:
    curr_files = os.listdir("/".join(dir_path))
    if "src" in curr_files:
        config_local = "/".join(dir_path) + "/src/.files.json"
        if os.path.exists(config_local):
            configuration_found = True
            with open(config_local) as f:
                CONFIG = json.load(f)
    dir_path.pop(-1)
    path_length = len(dir_path)

load_env = dotenv_values(f'{os.path.expandvars("$HOME")}/.config/files/.files')
CATCH2_FOLDER = load_env["CATCH2_PATH"] if load_env else None
if not (CONFIG and CATCH2_FOLDER):
    sys.exit(
        "%s: missing configuration file parameters" % (os.path.basename(sys.argv[0]))
    )

NAME_CONVERSIONS = {
    "cmake": "CMakeLists.txt",
    "make": "Makefile",
}


def main() -> None:
    opts = parse_arguments()
    if opts["debug"]:
        color_print("Provided arguments:")
        for arg in opts:
            print(f"{arg}:", opts[arg])
    file_contents = generate_file(opts, CONFIG)

    if not file_contents:
        return

    new_file, suffix = opts["file_name"][0], opts["filetype"]
    file_n = f"{new_file}.{suffix}"
    if os.path.exists(os.path.abspath(file_n)) and input(
        f"File exists. Replace {os.path.basename(file_n)}? "
    ) not in ("yes", "y", "Yes"):
        print("file creation aborted")
        return
    filename = NAME_CONVERSIONS.get(suffix) if NAME_CONVERSIONS.get(suffix) else file_n

    with open(filename, "w") as w:
        w.write(file_contents)

    if suffix in ["zsh", "sh", "py"]:
        # allow the file to be executable
        subprocess.run(["chmod", "+x", filename])

    if suffix == "cmake":
        # create required folders
        subprocess.run(["mkdir", "build"])
        subprocess.run(["mkdir", "src"])
        subprocess.run(["mkdir", "include"])

        # move file to the src folder
        os.rename(os.getcwd() + f"/{new_file}", os.getcwd() + f"/src/{new_file}")

        # set up testing functionality
        if opts["tests"]:
            if not os.path.exists(os.getcwd() + "/lib"):
                # copy folder into cwd and filter out git related files
                subprocess.run(
                    ["rsync", "-rv", "-f- .git", "-f- README.md", CATCH2_FOLDER, "."]
                )
            fname, fsuffix = new_file.split(".")
            testfile = new_file.replace(fsuffix, f"test.{fsuffix}")
            with open(os.getcwd() + f"/src/{testfile}", "a") as f:
                print(f'#include "{fname}.{fsuffix.replace("c", "h")}"', file=f)
                print('#include "catch2/catch.hpp"', file=f)
                print(file=f)
            open(  # noqa: SIM115
                os.getcwd() + f'/include/{fname}.{fsuffix.replace("c", "h")}', "x"
            )
        subprocess.run(["cmake", "-S", ".", "-B", "build/"])

    print(f"{filename} created.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        prog_print("\nkeyboard interrupted.")
