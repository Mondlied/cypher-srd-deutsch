# sync_translation_location :   update the English original to refer
#                               to the file containing the comment
#
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

import argparse
from csrd_split_helpers import openMarkdownFile
import glob
import re
import os
import sys

sourceExtractionRegex = re.compile('\s*<!--\\s*Quelle:\\s*(\\S.*\\S)\\s*-->\\s*', re.IGNORECASE)

def getSourceFile(fileName : str) -> str:
    with openMarkdownFile(fileName, 'r') as inputFile:
        for line in inputFile.read().splitlines():
            m = sourceExtractionRegex.match(line)
            if m:
                return m.group(1)
    return None

translationLocationRegex = re.compile('\s*<!--\\s*(Quelle|Übersetzung):.*-->\\s*', re.IGNORECASE)

def isTranslationLocationLine(line : str) -> bool:
    return bool(translationLocationRegex.match(line))

parser = argparse.ArgumentParser(description='Split the abilities file into separate abilities')
parser.add_argument('--source-dir', '-s', dest='sourceDir', help='the directory used to resolve relative paths of translation source paths')
parser.add_argument('--translations-dir', '-t', dest='translationsDir', help='location to use for determining the relative paths to list in the modified files')
parser.add_argument('patterns', nargs='+', help='the globbing patterns maching the input files')
args = parser.parse_args()

sourceDir = args.sourceDir if args.sourceDir != None else os.getcwd()
translationsDir = args.translationsDir if args.translationsDir != None else os.getcwd()

# list the input files
files = set()

for pattern in args.patterns:
    files.update(glob.glob(pattern, recursive=True))

for inputFile in files:
    source = getSourceFile(inputFile)
    if source == None:
        print(f'input file "{source}" does not contain a listed source', file=sys.stderr)
    else:
        resolvedSource = os.path.join(sourceDir, source)
        output = []
        fileNeedsModification = False
        translationLocation = os.path.relpath(inputFile, translationsDir).replace('\\', '/')
        with openMarkdownFile(resolvedSource, 'r') as input:
            for line in input.read().splitlines():
                if isTranslationLocationLine(line):
                    modifiedLine = f'<!-- Übersetzung: {translationLocation} -->'
                    output.append(modifiedLine)

                    # remember that we've actually changed something and need to
                    # overwrite the file contents
                    if modifiedLine != line:
                        fileNeedsModification = True
                else:
                    output.append(line)

        # only overwrite, if necessary
        if fileNeedsModification:
            with openMarkdownFile(resolvedSource, 'w') as outputFile:
                outputFile.writelines(map(lambda x: x + '\n', output))
