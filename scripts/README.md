The python script in this directory allows for splitting the result of using pandoc on the CSRD document provided, splitting the result into files when headings are encountered. A file containing headings info must be provided.

### Usage

```bash
# convert docx using to md file using pandoc
pandoc -t markdown_strict '--extract-media=.attachments/myfilename' '.\Cypher-System-Reference-Document-2023-02-10.docx' -o csrd_2023_02_10.md

# use python script to split the file
# (redirect of stderr to a file recommended, since there are 5k+ lines of complaints)
python .\split_markdown.py -i 'csrd_2023_02_10.md' -s headings.txt 2>stderr.txt  
```

The resulting files are placed in the current working directory.

### Headings file structure

This is a UTF-8 formated text file. Each line lists either a rule for starting a new file, or a rule for placing a heading at a specific heading level. The content of the heading line is stated before the first semicolon.

```
How to Play the Cypher System;file:01_How_to_Play_the_Cypher_System.md
WHEN DO YOU ROLL?;heading:2
```
Capitalization is automatically applied to the heading. In this example the heading becomes `When Do You Roll?`. This content can be overwritten by placing a semicolon followed by the replacement content after the rule.

```
How to Play the Cypher System;file:01_How_to_Play_the_Cypher_System.md;hOW tO pLAY tHe cYpHeR sYsTEm!!!
WHEN DO YOU ROLL?;heading:2;I replaced this heading:)>
```