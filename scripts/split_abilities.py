# split_abilities : functionality for splitting the abilities
#                    part of the CSRD markdown into separate files
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
from csrd_split_helpers import *
import os
import re

def toStripped(x : str) -> str:
    return x.strip()

def isNonSpace(s : str) -> bool:
    return not isSpaceOrEmpty(s)

def toTierGroupLowerText(x : str) -> str:
    return x[5:].lower()

def toTierAbilityList(lst : list[str]) -> list[str]:
    '''
    compact the list to ability names for the tier only

    Args:
        lst: the list of lines that are part of the abilities for the tier
    '''
    # just filter out any lines that contain space only
    return [x for x in lst if not isSpaceOrEmpty(x)]

def toGroupFileName(groupTitle : str) -> str:
    '''
    Determine file name given the title of an ability group
    '''
    return groupTitle.replace(' ', '_') + '.md'

class AbilityGroup:
    '''
    A type for storing the information about a single ability group
    '''
    lowTier = []
    midTier = []
    highTier = []
    description = ''

    def __init__(self, title):
        self.title = title

class Ability:
    '''
    The information about the a single ability
    '''
    title = ''
    description = []

    def __init__(self, title, description):
        self.title = title
        if (len(description) == 0):
            self.description = []
        else:
            # remove any space chars at the end of the description
            endIndex = len(description) - 1
            while (endIndex > 0) and isSpaceOrEmpty(description[endIndex]):
                endIndex = endIndex - 1
            self.description = description[0 : endIndex + 1]

################################################################################
# start of actual program logic ################################################
################################################################################
parser = argparse.ArgumentParser(description='Split the abilities file into separate abilities')
parser.add_argument('--output-dir', '-o', dest='outputDir', help='a file containing the heading info')
parser.add_argument('--input-file', '-i', dest='inputFile', help='the input markdown file containing the abilities')
args = parser.parse_args()

# the directory to store the output in is the directory specified via command line parameter
# or the current working directory, if not specified
if args.outputDir == None:
    outDir = os.getcwd()
else:
    outDir = args.outputDir

with openMarkdownFile(args.inputFile, 'r') as file:
    inputLines = file.read().splitlines()

def findTierGroup(i : int):
    while i < len(inputLines):
        if inputLines[i].strip().startswith('#### '):
            return i
        i = i + 1

def findNextStartElement(i : int) -> int:
    global inputLines
    while i != len(inputLines):
        strippedLine = inputLines[i].strip()
        if strippedLine.startswith('### ') or strippedLine.lower().startswith('## abilities—a'):
            return i
        i = i + 1
    return len(inputLines)

abilityStartRegex = re.compile('(([^(:]+\\S)(\\s*\\([^)]+\\)\\s*)?):(.*)')
abilityPrefixHeadingRegex = re.compile('\\s*## abilities—[a-z]\\s*', re.IGNORECASE)
specialCharReplacementRegex = re.compile('[ ?./\\!&%]+')

def abilityTitleToFileName(s : str) -> str:
    m = abilityStartRegex.match(s + ':')
    if not m:
        printErrorAndExit(f'ability title does not match the expected pattern {s}')
    else:
        return re.sub(specialCharReplacementRegex, '_', m.group(2)) + '.md'

abilitiesDir = os.path.join(outDir, 'abilities')
groupsDir = os.path.join(outDir, 'ability_groups')

os.makedirs(abilitiesDir, exist_ok=True)
os.makedirs(groupsDir, exist_ok=True)

i = findNextStartElement(0)

# write everything write everything up until the first ability group
with openMarkdownFile(os.path.join(outDir, 'abilities.md'), 'w') as outFile:
    outFile.writelines(inputLines[0:i]) 

# the line starting the first 
abilitiesStartLine = -1
abilityGroups = []
currentlyParsedAbilityGroup = None

# parse all ability groups
while i != len(inputLines):
    strippedLine = inputLines[i].strip()
    if strippedLine.lower().startswith('## abilities—a'):
        abilitiesStartLine = i
        break
    else:
        currentlyParsedAbilityGroup = AttributeError(strippedLine[4:])
        lowTierStart = findTierGroup(i+1)
        if not toTierGroupLowerText(inputLines[lowTierStart]).startswith('low tier'):
            printErrorAndExit(f'expected low tier ability group section but found: {inputLines[lowTierStart]}')
        midTierStart = findTierGroup(lowTierStart + 1)
        if not toTierGroupLowerText(inputLines[midTierStart]).startswith('mid tier'):
            printErrorAndExit(f'expected mid tier ability group section but found: {inputLines[midTierStart]}')
        highTierStart = findTierGroup(midTierStart + 1)
        if not toTierGroupLowerText(inputLines[highTierStart]).startswith('high tier'):
            printErrorAndExit(f'expected high tier ability group section but found: {inputLines[highTierStart]}')
        nextStart = findNextStartElement(highTierStart + 1)
        currentlyParsedAbilityGroup = AbilityGroup(strippedLine[4:])
        currentlyParsedAbilityGroup.description = ' '.join(map(toStripped, filter(isNonSpace, inputLines[i+1 : lowTierStart])))
        currentlyParsedAbilityGroup.lowTier = toTierAbilityList(inputLines[lowTierStart + 1 : midTierStart])
        currentlyParsedAbilityGroup.midTier = toTierAbilityList(inputLines[midTierStart + 1 : highTierStart])
        currentlyParsedAbilityGroup.highTier = toTierAbilityList(inputLines[highTierStart + 1 : nextStart])
        abilityGroups.append(currentlyParsedAbilityGroup)
        i = nextStart

currentAbility = None
abilities = []
currentDescription = []
currentTitle = None

# treat the line prior to the start of the 
previousLineEmpty = True

for l in inputLines[abilitiesStartLine:]:
    if previousLineEmpty:
        m = abilityStartRegex.match(l.strip())
        if m:
            if currentTitle != None:
                abilities.append(Ability(currentTitle, currentDescription))
            currentTitle = m.group(1)
            desc = m.group(4)
            if desc == None:
                currentDescription = []
            else:
                currentDescription = [desc.strip()]
        elif currentTitle != None:
            matchAbilityPrefix = abilityPrefixHeadingRegex.match(l)
            if matchAbilityPrefix:
                abilities.append(Ability(currentTitle, currentDescription))
                currentTitle = None
            else:
                currentDescription.append(l.strip())
    elif currentTitle != None:
        currentDescription.append(l.strip())
    previousLineEmpty = isSpaceOrEmpty(l)

if currentTitle != None:
    abilities.append(Ability(currentTitle, currentDescription))

for ag in abilityGroups:
    fileName = os.path.join(groupsDir, toGroupFileName(ag.title))
    with openMarkdownFile(fileName, 'w') as outFile:
        outFile.write(sourceReference(os.path.relpath(fileName, outDir))+ '\n')
        outFile.write('### ' + ag.title + '\n\n')
        outFile.writelines(ag.description)
        outFile.write('\n#### Low Tier\n\n')
        outFile.writelines(map(lambda s : f' - {s}\n', ag.lowTier))
        outFile.write('\n#### Mid Tier\n\n')
        outFile.writelines(map(lambda s : f' - {s}\n', ag.midTier))
        outFile.write('\n#### High Tier\n\n')
        outFile.writelines(map(lambda s : f' - {s}\n', ag.highTier))

for a in abilities:
    fileName = os.path.join(abilitiesDir, abilityTitleToFileName(a.title))
    with openMarkdownFile(fileName, 'w') as outputFile:
        outputFile.write(sourceReference(os.path.relpath(fileName, outDir)) + '\n')
        outputFile.write(f'**{a.title}:** ')
        for l in a.description:
            outputFile.write(l + '\n')
