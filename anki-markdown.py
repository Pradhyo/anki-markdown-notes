from aqt import mw
from aqt.utils import showInfo
from aqt.qt import *

import datetime
from glob import glob
import logging
from logging.handlers import RotatingFileHandler
import os
import re

BASIC_MODEL = "Basic"
REVERSE_MODEL = "Basic (and reversed card)"

directory = os.path.dirname(os.path.realpath(__file__))
logger = logging.getLogger("Anki Markdown Notes Log")
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('{}/anki-markdown.log'.format(directory),
                              maxBytes=10**6, backupCount=5)
logger.addHandler(handler)


def processAllNotes(NotesPath):
    """
    Read all markdown notes in `NotesPath` and load into Anki collection.
    Notes in root folder go to the default deck.
    Notes in subfolders go to a deck named after the corresponding subfolder.
    Any folders in the subfolder are ignored.
    """

    showInfo("Logs are located here - " + directory)

    deckCounter = {}
    existingNoteIDs = set()
    for markdownFile in glob(os.path.join(NotesPath, "*.md")):
        existingNotesInFile = processFile(markdownFile, "Default")
        deckCounter["Default"] = (deckCounter.get("Default", 0) +
                                  len(existingNotesInFile))
        existingNoteIDs.update(existingNotesInFile)
    for markdownFile in glob(os.path.join(NotesPath, "*", "*.md")):
        folderName = (os.path.basename(os.path.dirname(markdownFile)))
        existingNotesInFile = processFile(markdownFile, folderName)
        deckCounter[folderName] = (deckCounter.get(folderName, 0) +
                                   len(existingNotesInFile))
        existingNoteIDs.update(existingNotesInFile)

    deckCounter["DELETED"] = deleteNotes(existingNoteIDs)

    return deckCounter


def addNote(front, back, tag, model, deck, id=None):
    """
    Add note with `front` and `back` to `deck` using `model`.
    If `deck` doesn't exist, it is created.
    If `model` doesn't exist, nothing is done.
    If `id` is passed, it is used as the id
    """
    model = mw.col.models.byName(model)
    if model:
        mw.col.decks.current()['mid'] = model['id']
    else:
        return None

    # Creates or reuses deck with name passed using `deck`
    did = mw.col.decks.id(deck)
    deck = mw.col.decks.get(did)

    note = mw.col.newNote()
    note.model()['did'] = did

    note.fields[0] = front
    note.fields[1] = back

    if id:
        note.id = id
    note.addTag(tag)
    mw.col.addNote(note)
    mw.col.save()
    return note.id


def modifyNote(note, front, back, tag):
    """
    Modifies given note with given `front`, `back` and `tag`.
    If note with id is not found, do nothing.
    """
    note.fields[0] = front
    note.fields[1] = back
    note.addTag(tag)
    note.flush()
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
    front = []  # list of lines that make up the front of the card
    back = []  # list of lines that make up the back of the card
    model = None
    deck = deck
    currentID = ""
    toWrite = []  # buffer to store lines while processing a Note
    tag = os.path.basename(file).split('.')[0]  # get filename and ignores extension
    existingNotesInFile = set()  # notes in Anki not in this will be deleted at the end

    def handleNote():
        """
        Determines if current note is new or existing and acts appropriately.
        """
        if not (front and back):
            return

        frontText, backText = "<br>".join(front), "<br>".join(back)
        logger.debug('Importing front text: \n{}'.format(frontText))
        logger.debug('Importing back text: \n{}'.format(backText))

        # handle special ascii characters
        frontText = frontText.decode('utf-8')
        backText = backText.decode('utf-8')

        if currentID:
            newID = None
            try:
                note = mw.col.getNote(currentID)
                newID = modifyNote(note, frontText, backText, tag)
            except:
                newID = addNote(frontText, backText, tag, model, deck, currentID)

            if newID:
                # Overwrite in case format was off
                toWrite[-2] = ("<!-- {} -->\n".format(currentID))

        else:
            newID = addNote(frontText, backText, tag, model, deck)
            if newID:
                toWrite.insert(len(toWrite) - 1, "<!-- {} -->\n".format(newID))

        tempFile.writelines(toWrite)

        if newID:
            existingNotesInFile.add(newID)
            return True  # successfully handled Note

    tempFilePath = file + ".temp"
    with open(file, "r") as originalFile:
        with open(tempFilePath, "w") as tempFile:
            for line in originalFile:

                if not (line.startswith("Q:") or line.startswith("QA:") or toWrite):
                    tempFile.write(line)
                    continue

                # line is a part of a Note that has to be added to Anki

                toWrite.append(line)
                if not line.strip():
                    handleNote()
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
            handleNote()
    os.remove(file)
    os.rename(tempFilePath, file)
    return existingNotesInFile


def deleteNotes(existingNoteIDs):
    """
    Deletes notes in Anki that aren't in the passed list of `existingNoteIDs`
    """
    notesToDelete = set()
    numDeleted = 0
    allDecks = mw.col.decks.allNames()
    for deck in allDecks:
        for cid in mw.col.findNotes("deck:" + deck):
            # cid is of type long but existingNoteIDs are string
            if str(cid) not in existingNoteIDs:
                notesToDelete.add(cid)
                numDeleted += 1

    mw.col.remNotes(notesToDelete)
    return numDeleted


def writeNote(note, deckFile):
    """
    Write lines to the markdown file from the note object.
    '<br>' in the front/back are converted to '\n'
    """
    if note.model()["name"] == BASIC_MODEL:
        qPrefix = "Q:"
    elif note.model()["name"] == REVERSE_MODEL:
        qPrefix = "QA:"
    else:
        return  # Unsupported model

    note_front = note.fields[0].replace("<br>", "\n").encode('utf-8')
    logger.debug('Writing front of note:\n{}\n'.format(note_front))
    deckFile.write("{} {}\n".format(qPrefix, note_front))

    note_back = note.fields[1].replace("<br>", "\n").encode('utf-8')
    logger.debug('Writing back of note:\n{}\n'.format(note_back))
    deckFile.write("A: {}\n".format(note_back))

    # note_back = "A: {}\n".format(note.fields[1].replace("<br>", "\n"))
    # deckFile.write(note_back.encode('utf-8'))
    deckFile.write("<!-- {} -->\n\n".format(note.id))


def exportAllNotes(NotesPath):
    """
    Exports all notes to markdown files in a Notes folder in 'NotesPath'.
    Aborts if 'Notes' folder already exists.
    For deck 'DeckName', a folder 'DeckName' is created and all the notes
    in that deck are stored in 'DeckName.md' in that folder.
    """
    showInfo("Logs are located here - " + directory)
    NotesPath = os.path.join(NotesPath, "Notes")
    if os.path.exists(NotesPath):
        showInfo("Aborting - 'Notes' folder already exists")
        return

    os.makedirs(NotesPath)
    allDecks = mw.col.decks.allNames()
    for deck in allDecks:
        deckFolder = os.path.join(NotesPath, deck)
        os.makedirs(deckFolder)
        with open(os.path.join(deckFolder, deck + ".md"), "w") as deckFile:
            deckFile.write("# {} \n\n".format(deck))
            for cid in mw.col.findNotes("deck:" + deck):
                note = mw.col.getNote(cid)
                writeNote(note, deckFile)

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
