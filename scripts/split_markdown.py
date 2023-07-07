import argparse
import re
import sys

from html.parser import HTMLParser

def printErrorAndExit(message):
    '''
    print a message to stderr and exit the program with error code 1
    '''
    print(message, file=sys.stderr)
    sys.exit(1)

def toTableHeaderLine(x):
    return ' --- '

# words that remain lower case, assuming they're not in the first word
unmodifiedHeaderWords = {
    'of',
    'the',
    'and',
    'as',
    'a',
    'an'
}

def capitalizeFirstLetter(s):
    if len(s) == 0:
        return ''
    else:
        return s[0].upper() + s[1:].lower()

def fixHeaderCase(s):
    '''
    Returns the input with all words capitalized except for those in unmodifiedHeaderWords 
    '''
    res = ''
    firstWord = True
    for p in re.split('\\b', s):
        if firstWord:
            if p.isspace():
                res = res + p
            else:
                res = res + capitalizeFirstLetter(p)
                firstWord = False
        elif p.lower() in unmodifiedHeaderWords:
            res = res + p
        else:
            res = res + capitalizeFirstLetter(p)
    return res


class TableFragmentParser(HTMLParser):
    '''
    A helper class for parsing table html fragemnts
    '''
    inTable = False
    inTableChild = False
    inRow = False
    inColumnGroup = False
    inCell = False
    columnCount = 0
    rows = []
    currentRow = []
    currentCellContent = []

    def handle_starttag(self, tag, attrs):
        if not self.inTable:
            if tag == 'table':
                self.inTable = True
            else:
                printErrorAndExit(f'expected <table> element, but found <{tag}>')
        elif not self.inTableChild and not self.inColumnGroup:
            if tag == 'thead' or tag == 'tbody':
                self.inTableChild = True
            elif tag == 'colgroup':
                self.inColumnGroup = True
                self.columnCount = 0
            else:
                printErrorAndExit(f'expected <thead> or <tbody> element, but found <{tag}>')
        elif self.inColumnGroup:
            if tag == 'col':
                self.columnCount = self.columnCount + 1
            else:
                printErrorAndExit(f'expected <col> element, but found <{tag}>')
        elif not self.inRow:
            if tag == 'thead' or tag == 'tr':
                self.inRow = True
                self.currentRow = []
            else:
                printErrorAndExit(f'expected <thead> or <tr> element, but found <{tag}>')
        elif not self.inCell:
            if tag == 'th' or tag == 'td':
                self.inCell = True
                self.currentCellContent = []
            else:
                printErrorAndExit(f'expected <th> or <td> element, but found <{tag}>')
        elif tag != 'br' and tag != 'strong':
            printErrorAndExit(f'unexpected inline found: <{tag}>')


    def handle_endtag(self, tag):
        if self.inCell:
            if tag == 'td' or tag == 'th':
                self.inCell = False
                if self.inRow:
                    self.currentRow.append(' '.join(self.currentCellContent))
        elif self.inRow:
            self.inRow = False
            self.rows.append(self.currentRow)
        elif self.inColumnGroup:
            if tag == 'colgroup':
                self.inColumnGroup = False
        elif self.inTableChild:
            self.inTableChild = False
        elif self.inTable:
            self.inTable = False

    def handle_data(self, data):
        if self.inCell:
            self.currentCellContent.append(data.strip().replace('\n', ' '))
        elif not data.isspace():
            printErrorAndExit(f'unexpected data outside of <th> or <td> elements: {data}')

def toMatchHeading(x):
    return x

################################################################################
# heading matching functions
#
# the functions take the FileMatcher object as first parameter and the heading
# check as second parameter
#
# The matcher function is responsible for writing the heading, if it matches
#
# The function returns True on a match and False otherwise
################################################################################

def matchHeadings(matchHeading, x):
    '''
    helper function for checking the equality of headings 
    '''
    return matchHeading == x

def matchNone(m, x):
    '''
    Matcher function for treating everything as non-heading
    '''
    return False

def matchHeading(m, x):
    '''
    Matcher for inserting the matching heading at a specific heading level
    '''
    if matchHeadings(m.matchHeading, x):
        if m.hasOpenFile:
            m.file.write(('#' * m.headingLevel) + ' ' + m.replacementHeading + '\n')
        return True
    else:
        return False

def matchNewFileHeading(m, x):
    '''
    Matcher for opening a new file, if a heading is matched.
    The matched heading is inserted as h1 heading
    '''
    if matchHeadings(m.matchHeading, x):
        # close any previously opened file
        if m.hasOpenFile:
            m.file.close()
        
        # open the next file (note:pandoc uses utf-8)
        m.file = open(m.matchFile, 'w', encoding='utf-8')
        m.hasOpenFile = True

        # insert the heading
        m.file.write('# ' + m.replacementHeading + '\n')
        return True
    else:
        return False

class FileMatcher:
    '''
    Helper class for headings line matching/file writing
    '''
    def __init__(self, hls):
        self.matcher = matchNone
        self.headingIndex = -1
        self.headingsLines = hls
        self.headerFilePattern = re.compile('([^;]+);(heading|file):([^;]*)(;(.*))?')
        self.matchHeading=''
        self.hasOpenFile = False

        # activate the first line
        self.activateNextHeadingIndex()

    def activateNextHeadingIndex(self):
        '''
        Activate the next line from the headings file as the matcher
        '''
        self.headingIndex = self.headingIndex + 1
        if self.headingIndex >= len(self.headingsLines):
            # end of lines from the headings file reached
            # -> treat everything as non-headings from now on
            self.matcher = matchNone
        else:
            heading = self.headingsLines[self.headingIndex]

            # parse & activate the next heading matcher
            m = self.headerFilePattern.match(heading)
            if m:
                type = m.group(2)
                if type == 'file':
                    # matcher also opening the next file on a match
                    self.matchHeading = m.group(1)
                    self.matchFile = m.group(3)
                    self.matcher = matchNewFileHeading
                    self.replacementHeading = m.group(5)
                    if self.replacementHeading is None:
                        # replace with fixed version of the matched string, if no replacement is specified
                        self.replacementHeading = fixHeaderCase(self.matchHeading)
                    self.matchHeading = toMatchHeading(self.matchHeading)
                elif type == 'heading':
                    # matcher specifying the heading level
                    self.matchHeading = m.group(1)
                    self.replacementHeading = m.group(5)
                    self.headingLevel = int(m.group(3))
                    self.matcher = matchHeading
                    if self.replacementHeading is None:
                        # replace with fixed version of the matched string, if no replacement is specified
                        self.replacementHeading = fixHeaderCase(self.matchHeading)
                    self.matchHeading = toMatchHeading(self.matchHeading)
                else:
                    printErrorAndExit(f'unexpected entry type: "{type}"')
            else:
                printErrorAndExit(f'error in headings file line {self.headingIndex} ("{heading}")')

    def writeContent(self, content):
        '''
        Write a line that isn't a candidate for a heading
        '''
        if self.hasOpenFile:
            self.file.write(content + '\n')

    def writePossibleHeader(self, headerContent):
        '''
        Write something that is a candidate for a heading
        '''
        if self.matcher(self, headerContent):
            # matcher has already written the content
            # -> just activate the next matcher
            self.activateNextHeadingIndex()
        else:
            # not a matched heading: write warning and deal with it as if it was normal content
            print(f'WARNING: possible heading not listed in heading file: "{headerContent}"', file=sys.stderr)
            self.writeContent(headerContent)

    def writeTable(self, rows, columnCount):
        '''
        Write a table to the file.

        Args:
            rows:   a list of lists containing the cell contents of a single row;
                    the first element contains the header contents
            columnCount: the number of columns in the table
        '''
        if len(rows) != 0:
            # write the header
            self.writeContent(' | '.join(rows[0]))
            self.writeContent(' | '.join(map(toTableHeaderLine, range(0, columnCount))))
        # write the table content
        for row in rows[1:]:
            self.writeContent(' | '.join(row))
        self.writeContent('')

    def finish(self):
        '''
        Function for ending the file writing. Warns about any headings not matched
        '''
        for i in range(self.headingIndex, len(self.headingsLines)):
            print(f'WARNING: Heading missing from input: "{self.headingsLines[i]}"', file=sys.stderr)

        if self.hasOpenFile:
            self.file.close()

################################################################################
# actual start of the program
################################################################################
parser = argparse.ArgumentParser(description='Split into files')
parser.add_argument('--headings-file', '-s', dest='headingsFile', help='a file containing the heading info')
parser.add_argument('--input-file', '-i', dest='inputFile', help='the input markdown file')
args = parser.parse_args()
with open(args.headingsFile, 'r', encoding='utf-8') as hf:
    headingLines = hf.read().splitlines()
    
if len(headingLines) == 0:
    printErrorAndExit(f'the headings file "{args.headingsFile}" is empty')

# note: pandoc uses utf-8
with open(args.inputFile, 'r', encoding='utf-8') as inFile:
    inputLines = inFile.read().splitlines()
    
matcher = FileMatcher(headingLines)

# treat the start of the file as empty line
previousLineWasSpace = True

def isSpaceOrEmpty(s):
    return len(s) == 0 or s.isspace()

def isListEntry(s):
    '''
    Returns, whether the line is an entry of a unordered list
    '''
    return s.startswith('\u2022 ')

def toMarkdownListItem(s):
    '''
    Convert a line containing a list item to a line containing a proper markdown element
    '''
    return '*' + s[1:]

def isTableStart(s):
    '''
    Check, if the parameter is the start tag of a table
    '''
    stripped = s.strip()
    # note: the element could contain attributes
    return stripped.startswith('<table') and stripped.find('>') == (len(stripped) - 1) 

def isTableEnd(s):
    '''
    Check, if the parameter is the end element of a table
    '''
    return s.strip() == '</table>'
 
def couldBeHeading(s):
    '''
    Check, if the line could be a heading.

    Headings are non-empty lines not starting with unorderered list markdown and not ending with a period char.
    '''
    return not isSpaceOrEmpty(s) and not s.startswith('- ') and not s.endswith('.')

# we don't start of parsing a table
parsingTable = False

def parseSingleLine(i, assumeNextLineEmpty=False):
    '''
    Helper function for parsing a single line

    Args:
        i:                      the index of the line
        assumeNextLineEmpty:    whether to consider the next line empty (default: no)
    '''
    global parsingTable
    global previousLineWasSpace
    global tableContent

    current = inputLines[i]
    if parsingTable:
        # no headings inside a table; just collect content until we find the end of the table
        previousLineWasSpace = False
        tableContent = tableContent + current + '\n'
        if isTableEnd(current):
            # actually parse the table content and write the results
            fragmentParser = TableFragmentParser()
            fragmentParser.feed(tableContent)
            matcher.writeTable(fragmentParser.rows, fragmentParser.columnCount)
            parsingTable = False
    elif isListEntry(current):
        # write fixed list item (not a heading)
        previousLineWasSpace = False
        matcher.writeContent(toMarkdownListItem(current))
    elif isTableStart(current):
        # begin of table (not considered a heading)
        previousLineWasSpace = False
        parsingTable = True
        tableContent = current + '\n'
    elif previousLineWasSpace and (assumeNextLineEmpty or isSpaceOrEmpty(inputLines[i + 1])) and couldBeHeading(current): # note: do not access a line past the last one
        # possible headings are lines preceeding by a line considered empty and followed by a line considered to be empty
        previousLineWasSpace = False
        matcher.writePossibleHeader(current)
    else:
        # anything not considered a heading or another special line is written out as is
        matcher.writeContent(current)
        previousLineWasSpace = isSpaceOrEmpty(current)

for i in range(0, len(inputLines) - 1):
    # parse all lines except for the last one
    parseSingleLine(i)

if len(inputLines) != 0:
    # the last line is considered to be followed by an empty line
    parseSingleLine(len(inputLines) - 1, True)

if parsingTable:
    printErrorAndExit(f'ERROR: end of file reached while parsing a table, current table content: {tableContent}')

# do post-processing
matcher.finish()
