import argparse
import re
import sys

from html.parser import HTMLParser

def toTableHeaderLine(x):
    return ' --- '

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
                print(f'expected <table> element, but found <{tag}>', file=sys.stderr)
                sys.exit(1)
        elif not self.inTableChild and not self.inColumnGroup:
            if tag == 'thead' or tag == 'tbody':
                self.inTableChild = True
            elif tag == 'colgroup':
                self.inColumnGroup = True
                self.columnCount = 0
            else:
                print(f'expected <thead> or <tbody> element, but found <{tag}>', file=sys.stderr)
                sys.exit(1)
        elif self.inColumnGroup:
            if tag == 'col':
                self.columnCount = self.columnCount + 1
            else:
                print(f'expected <col> element, but found <{tag}>', file=sys.stderr)
                sys.exit(1)
        elif not self.inRow:
            if tag == 'thead' or tag == 'tr':
                self.inRow = True
                self.currentRow = []
            else:
                print(f'expected <thead> or <tr> element, but found <{tag}>', file=sys.stderr)
                sys.exit(1)
        elif not self.inCell:
            if tag == 'th' or tag == 'td':
                self.inCell = True
                self.currentCellContent = []
            else:
                print(f'expected <th> or <td> element, but found <{tag}>', file=sys.stderr)
                sys.exit(1)
        elif tag != 'br' and tag != 'strong':
            print(f'unexpected inline found: <{tag}>', file=sys.stderr)
            sys.exit(1)


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
            print(f'unexpected data outside of <th> or <td> elements: {data}', file=sys.stderr)
            sys.exit(1)

def toMatchHeading(x):
    return x

def matchHeadings(matchHeading, x):
    return matchHeading == x

def matchNone(m, x):
    return False

def matchHeading(m, x):
    if matchHeadings(m.matchHeading, x):
        if m.hasOpenFile:
            m.file.write(('#' * m.headingLevel) + ' ' + m.replacementHeading + '\n')
        return True
    else:
        return False

def matchNewFileHeading(m, x):
    if matchHeadings(m.matchHeading, x):
        if m.hasOpenFile:
            m.file.close()
        m.file = open(m.matchFile, 'w', encoding='utf-8')
        m.hasOpenFile = True
        m.file.write('# ' + m.replacementHeading + '\n')
        return True
    else:
        return False

class FileMatcher:
    def __init__(self, hls):
        self.matcher = matchNone
        self.headingIndex = -1
        self.headingsLines = hls
        self.headerFilePattern = re.compile('([^;]+);(heading|file):([^;]*)(;(.*))?')
        self.matchHeading=''
        self.hasOpenFile = False
        self.activateNextHeadingIndex()

    def activateNextHeadingIndex(self):
        self.headingIndex = self.headingIndex + 1
        if self.headingIndex >= len(self.headingsLines):
            self.matcher = matchNone
        else:
            heading = self.headingsLines[self.headingIndex]
            m = self.headerFilePattern.match(heading)
            if m:
                type = m.group(2)
                if type == 'file':
                    self.matchHeading = m.group(1)
                    self.matchFile = m.group(3)
                    self.matcher = matchNewFileHeading
                    self.replacementHeading = m.group(5)
                    if self.replacementHeading is None:
                        self.replacementHeading = fixHeaderCase(self.matchHeading)
                    self.matchHeading = toMatchHeading(self.matchHeading)
                elif type == 'heading':
                    self.matchHeading = m.group(1)
                    self.replacementHeading = m.group(5)
                    self.headingLevel = int(m.group(3))
                    self.matcher = matchHeading
                    if self.replacementHeading is None:
                        self.replacementHeading = fixHeaderCase(self.matchHeading)
                    self.matchHeading = toMatchHeading(self.matchHeading)
                else:
                    print(f'unexpected entry type: "{type}"', file=sys.stderr)
                    sys.exit(1)
            else:
                print(f'error in headings file line {self.headingIndex} ("{heading}")', file=sys.stderr)
                sys.exit(1)

    def writeContent(self, content):
        if self.hasOpenFile:
            self.file.write(content + '\n')

    def writePossibleHeader(self, headerContent):
        if self.matcher(self, headerContent):
            self.activateNextHeadingIndex()
        else:
            print(f'WARNING: possible heading not listed in heading file: "{headerContent}"', file=sys.stderr)
            self.writeContent(headerContent)

    def writeTable(self, rows, columnCount):
        if len(rows) != 0:
            self.writeContent(' | '.join(rows[0]))
            self.writeContent(' | '.join(map(toTableHeaderLine, range(0, columnCount))))
        for row in rows[1:]:
            self.writeContent(' | '.join(row))
        self.writeContent('')

    def finish(self):
        for i in range(self.headingIndex, len(self.headingsLines)):
            print(f'WARNING: Heading missing from input: "{self.headingsLines[i]}"', file=sys.stderr)

        if self.hasOpenFile:
            self.file.close()


parser = argparse.ArgumentParser(description='Split into files')
parser.add_argument('--headings-file', '-s', dest='headingsFile', help='a file containing the heading info')
parser.add_argument('--input-file', '-i', dest='inputFile', help='the input markdown file')
args = parser.parse_args()
with open(args.headingsFile, 'r', encoding='utf-8') as hf:
    headingLines = hf.read().splitlines()
    
if len(headingLines) == 0:
    print(f'the headings file "{args.headingsFile}" is empty', file=sys.stderr)
    sys.exit(1)

with open(args.inputFile, 'r', encoding='utf-8') as inFile:
    inputLines = inFile.read().splitlines()
    
matcher = FileMatcher(headingLines)

previousLineWasSpace = True

def isSpaceOrEmpty(s):
    return len(s) == 0 or s.isspace()

def isListEntry(s):
    return s.startswith('\u2022 ')

def toMarkdownListItem(s):
    return '*' + s[1:]

def isTableStart(s):
    stripped = s.strip()
    return stripped.startswith('<table') and stripped.find('>') == (len(stripped) - 1) 

def isTableEnd(s):
    return s.strip() == '</table>'
 
def couldBeHeading(s):
    return not isSpaceOrEmpty(s) and not s.startswith('- ') and not s.endswith('.')

parsingTable = False

def parseSingleLine(i, assumeNextLineEmpty=False):
    global parsingTable
    global previousLineWasSpace
    global tableContent

    current = inputLines[i]
    if parsingTable:
        previousLineWasSpace = False
        tableContent = tableContent + current + '\n'
        if isTableEnd(current):
            fragmentParser = TableFragmentParser()
            fragmentParser.feed(tableContent)
            matcher.writeTable(fragmentParser.rows, fragmentParser.columnCount)
            parsingTable = False
    elif isListEntry(current):
        previousLineWasSpace = False
        matcher.writeContent(toMarkdownListItem(current))
    elif isTableStart(current):
        previousLineWasSpace = False
        parsingTable = True
        tableContent = current + '\n'
    elif previousLineWasSpace and (assumeNextLineEmpty or isSpaceOrEmpty(inputLines[i + 1])) and couldBeHeading(current):
        previousLineWasSpace = False
        matcher.writePossibleHeader(current)
    else:
        matcher.writeContent(current)
        previousLineWasSpace = isSpaceOrEmpty(current)

for i in range(0, len(inputLines) - 1):
    parseSingleLine(i)

if len(inputLines) != 0:
    parseSingleLine(len(inputLines) - 1, True)

if parsingTable:
    print(f'ERROR: end of file reached while parsing a table, current table content: {tableContent}', file=sys.stderr)
    sys.exit(1)

matcher.finish()
