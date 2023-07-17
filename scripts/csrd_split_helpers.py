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