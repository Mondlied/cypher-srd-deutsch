# csrd_split_helpers : helper functionality for working with CSRD markdown
# Copyright (C) 2023  Fabian Klein
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import io
import sys
import typing

def printErrorAndExit(message : str) -> None:
    '''
    print a message to stderr and exit the program with error code 1
    '''
    print(message, file=sys.stderr)
    sys.exit(1)

def isSpaceOrEmpty(s : str) -> bool:
    return len(s) == 0 or s.isspace()

def openMarkdownFile(fileName, mode) -> typing.TextIO:
    '''
    Open a file with a given mode with a pandoc-compatible encoding (UTF-8)
    '''
    return open(fileName, mode, encoding='utf-8')

def sourceReference(fileName: str) -> str:
    '''
    Get the content to write to a file mentioning the original source
    '''
    # ensure slashes are used as path separators, even on windows
    source = fileName.replace('\\', '/')
    return f'<!-- Quelle: {source} -->\n'