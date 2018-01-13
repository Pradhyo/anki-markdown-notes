from aqt import mw
from aqt.utils import showInfo
from aqt.qt import *

import re
from glob import glob
import os

BASIC_MODEL = "Basic"
REVERSE_MODEL = "Basic (and reversed card)"

def processAllNotes(NotesPath):
    """
    Read all markdown notes in `NotesPath` and load into Anki collection.
    Notes in root folder go to the default deck.
    Notes in subfolders go to a deck named after the corresponding subfolder.
    Any folders in the subfolder are ignored.
    """
    deckCounter = {}
    for markdownFile in glob(os.path.join(NotesPath, "*.md")):
        deckCounter["Default"] = (deckCounter.get("Default", 0)
                                  + processFile(markdownFile, "Default"))
    for markdownFile in glob(os.path.join(NotesPath, "*", "*.md")):
        folderName = (os.path.basename(os.path.dirname(markdownFile)))
        deckCounter[folderName] = (deckCounter.get(folderName, 0)
                                   + processFile(markdownFile, folderName))
    return deckCounter

def addNote(front, back, model, deck):
    """
    Add note with `front` and `back` to `deck` using `model`.
    If `deck` doesn't exist, it is created.
    If `model` doesn't exist, nothing is done.
    """
    model = mw.col.models.byName(model)
    if model:
        mw.col.decks.current()['mid'] = model['id']
    else:
        return None

    # Creates are reuses deck with name passed using `deck`
    did = mw.col.decks.id(deck)
    deck = mw.col.decks.get(did)

    note = mw.col.newNote()
    note.model()['did'] = did

    note.fields[0] = front
    note.fields[1] = back
    mw.col.addNote(note)
    mw.col.save()
    return note.id

def modifyNote(front, back, id):
    """
    Get note with id and update `front` and `back`.
    If note with id is not found, do nothing.
    """
    note = mw.col.getNote(id)
    if not note:
        return None
    note.fields[0] = front
    note.fields[1] = back
    mw.col.addNote(note)
    mw.col.save()
    return note.id

def isIDComment(line):
    """
    Check if line matches this format <!-- 1510862771508 -->
    """
    idCommentPattern = re.compile("<!-{2,} *\d{13,} *-{2,}>")
    return True if idCommentPattern.search(line) else False

def getIDfromComment(line):
    """
    Get id from comment
    Returns 1510862771508 from <!-- 1510862771508 -->
    """
    idPattern = re.compile("\d{13,}")
    return idPattern.findall(line)[0]

def processFile(file, deck="Default"):
    """
    Go through one markdown file, extract notes and load into Anki collection.
    Writes everything to a .temp file and adds ID comments as necessary.
    Once processing is done, the .temp file is moved to the original file.
    """
    front = [] # list of lines that make up the front of the card
    back = [] # list of lines that make up the back of the card
    model = None
    deck = deck
    currentID = ""
    toWrite = [] # buffer to store lines while processing a Note
    counter = 0

    def handleNote():
        """
        Determines if current note is new or existing and acts appropriately.
        """
        if not (front and back):
            return
        frontText, backText = "<br>".join(front), "<br>".join(back)
        if currentID:
            newID = modifyNote(frontText, backText, currentID)
            if newID:
                # Overwrite in case format was off
                toWrite[-2] = ("<!-- {} -->\n".format(currentID))
        else:
            newID = addNote(frontText, backText, model, deck)
            if newID:
                toWrite.insert(len(toWrite)-1, "<!-- {} -->\n".format(newID))
        tempFile.writelines(toWrite)
        if newID:
            return True # successfully handled Note

    tempFilePath = file + ".temp"
    with open(file, "r") as originalFile:
        with open(tempFilePath, "w") as tempFile:
            for line in originalFile:

                if not (line.startswith("Q:")
                        or line.startswith("QA:")
                        or toWrite):
                    tempFile.write(line)
                    continue

                # line is a part of a Note that has to be added to Anki

                toWrite.append(line)
                if not line.strip():
                    if handleNote():
                        counter += 1
                    toWrite = []
                    front = []
                    back = []
                    currentID = ""
                    model = None
                    continue

                if line.startswith("Q:"):
                    model = BASIC_MODEL
                    front.append(line[2:].strip())
                elif line.startswith("QA:"):
                    model = REVERSE_MODEL
                    front.append(line[3:].strip())
                elif isIDComment(line):
                    currentID = getIDfromComment(line)
                elif line.startswith("A:"):
                    back.append(line[2:].strip())
                elif not back:
                    front.append(line.strip())
                else:
                    back.append(line.strip())
            if toWrite:
                # Append new line so id comment is on the next line
                toWrite[-1] = toWrite[-1].strip() + "\n"
            toWrite.append("\n")
            if handleNote():
                counter += 1
    os.remove(file)
    os.rename(tempFilePath, file)
    return counter

def exportAllNotes(NotesPath):
    """
    Exports all notes to markdown files in a Notes folder in 'NotesPath'.
    Aborts if 'Notes' folder already exists.
    For deck 'DeckName', a folder 'DeckName' is created and all the notes
    in that deck are stored in 'DeckName.md' in that folder.
    """
    NotesPath = os.path.join(NotesPath, "Notes")
    if os.path.exists(NotesPath):
        showInfo("Aborting - 'Notes' folder already exists")
        return

    def writeNote(note):
        """
        Write lines to the markdown file from the note object.
        '<br>' in the front/back are converted to '\n'
        """
        if note.model()["name"] == BASIC_MODEL:
            qPrefix = "Q:"
        elif note.model()["name"] == REVERSE_MODEL:
            qPrefix = "QA:"
        else:
            return # Unsupported model
        deckFile.write("{} {}\n".format(qPrefix,
                                        note.fields[0].replace("<br>", "\n")))
        deckFile.write("A: {}\n".format(note.fields[1].replace("<br>", "\n")))
        deckFile.write("<!-- {} -->\n\n".format(note.id))

    os.makedirs(NotesPath)
    allDecks = mw.col.decks.allNames()
    for deck in allDecks:
        deckFolder = os.path.join(NotesPath, deck)
        os.makedirs(deckFolder)
        with open(os.path.join(deckFolder, deck + ".md"), "w") as deckFile:
            deckFile.write("# {} \n\n".format(deck))
            for cid in mw.col.findNotes("deck:" + deck):
                note = mw.col.getNote(cid)
                writeNote(note)

    return allDecks


# Import UI
######################################################################

def importNotesUI():
    """
    Lets user pick a directory and imports Notes from it.
    """
    w = QWidget()
    NotesPath = str(QFileDialog.getExistingDirectory(w, "Pick Notes Folder"))
    if NotesPath:
        deckCounter = processAllNotes(NotesPath)
        w.show()
        showInfo("Notes handled in each deck - " + str(deckCounter))

importAction = QAction("Import from Markdown Notes", mw)
importAction.triggered.connect(importNotesUI)
mw.form.menuTools.addAction(importAction)

# Export UI
######################################################################

def exportNotesUI():
    """
    Lets user pick a directory and exports Notes to it.
    """
    w = QWidget()
    NotesPath = str(QFileDialog.getExistingDirectory(w, "Pick Notes Folder"))
    if NotesPath:
        exportedDecks = exportAllNotes(NotesPath)
        if exportedDecks:
            w.show()
            showInfo("Exported these decks - " + ", ".join(exportedDecks))

exportAction = QAction("Export to Markdown Notes", mw)
exportAction.triggered.connect(exportNotesUI)
mw.form.menuTools.addAction(exportAction)