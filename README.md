# Anki-Markdown-Notes

⚠️⚠️Please version control your markdown notes and backup your Anki notes before attempting to import notes from markdown files using this add-on. Since only two built-in models are supported, this add-on might cause unexpected behavior. This has worked out well for me since Jan 2018 because I was starting from scratch and I only use the two supported models. ⚠️⚠️ 

This is an [Anki](https://apps.ankiweb.net/) [add-on](https://ankiweb.net/shared/addons/) that extracts notes from markdown files and imports them to Anki. This add-on is meant to be used when maintaining all notes using Markdown files only - any edits made from Anki will be lost the next time this add-on is used. Major advantages of doing so:
- easily see all notes from each deck at the same place
- easy to add notes in bulk into Anki when covering a lot of new material
- maintain additional material that doesn't have to go into Anki along with Anki notes
- version control the notes since they are now markdown files

>Only these two built-in models are supported for now - `Basic` and `Basic (and reversed card)`
>Media (images/audio) is not supported.


## Installation

To download and install directly from [Ankiweb](https://ankiweb.net/shared/info/2141874715), please copy and paste the following code into the desktop program: 2141874715

Alternatively, open your add-ons folder by selecting "Tools -> Add-Ons -> Open Add-Ons Folder" and simply paste the [anki-markdown.py](https://github.com/Pradhyo/anki-markdown-notes/blob/master/anki-markdown.py) file into it.

## Usage

### Existing Notes
To start using this add-on, first extract all existing notes into markdown by selecting "Tools -> Export to Markdown Notes". You should see all the notes following the built in models in a "Notes" folder in the folder you chose. You can now follow the conventions below and choose to rearrange your notes along with their id comments.

### Starting from scratch
Create a Notes folder wherever you want the notes to be and follow the below conventions. Then select "Tools -> Import from Markdown Notes" in the Anki desktop app to import them into Anki.

## Conventions
The file structure of the Markdown files is shown below.
- All notes extracted from the root folder are added to the Default deck. In the below case, notes from random.md go to the Default deck.
- Everything in a sub-folder goes to a deck named after that subfolder - here notes from socket.md and files.md go into the python deck.
- The filename is set as a tag for each note in a file - here all notes from socket.md are assigned a tag 'socket'. The tag can be used used in the [card templates as shown here](https://apps.ankiweb.net/docs/manual.html#special-fields).

```
Notes
│   algorithms.md
│
└───python
│   │   socket.md
│   │   files.md
│
└───tools
    │   git.md
    │   tmux.md
```

**Currently there is support only for two types of notes - `Basic` and `Basic (and reversed card)`**. To create a basic card, enter the following anywhere in the Markdown file:

```
Q: Question
A: - Answer line 1
- Answer line 2
```

This creates a basic card with `Question` as the front of the card and
```
Answer line 1
Answer line 2
```
as the back.

Blank lines in the markdown file are considered the end of a Note.

To create a basic and reversed card, use QA instead of Q above like so:
```
QA: Question
A: - Answer line 1
- Answer line 2
```

Sample Notes are in the **[Notes](https://github.com/Pradhyo/anki-markdown-notes/tree/master/Notes)** folder.

## Development
All the code is in the single **[anki-markdown.py](https://github.com/Pradhyo/anki-markdown-notes/blob/master/anki-markdown.py)** file.
Going through the [docs](https://apps.ankiweb.net/docs/addons.html) first is highly recommended. In the markdown files, id comments are added as soon as a note is imported successfully into anki - this will ensure any changes to the note in the markdown file edits the same anki note.
