# Org-Roam to Obsidian Converter

## Overview

`org-roam-to-obsidian` is a command-line tool that converts your org-roam personal wiki into an Obsidian vault, preserving your notes, links, and metadata while transforming them into Obsidian's Markdown format.

## Requirements

- Python 3.11 or higher (required for standard library TOML support)
- [Pandoc](https://pandoc.org/) must be installed

## Features

- Converts Org-roam `.org` files to Obsidian-compatible Markdown
- Preserves internal links and transforms them to Obsidian's `[[]]` format
- Migrates tags and properties to YAML frontmatter
- Maintains your note hierarchy and organization
- Converts Org syntax (lists, tables, code blocks) to Markdown
- Preserves backlinks and references

## Usage

Basic usage:

```bash
org-roam-to-obsidian --source /path/to/org-roam.db --destination /path/to/obsidian-vault
```

Options:

```
--source, -s                Path to your org-roam database file
--destination, -d           Path for the new Obsidian vault
--source-base-path, -b      Base path of org-roam files for preserving directory structure (optional)
--dry-run                   Test the conversion without writing files
--verbose, -v               Show detailed conversion information
--help, -h                  Display this help message
```


## Examples

### Basic Conversion

```bash
# Convert your entire Org-roam wiki
org-roam-to-obsidian -s ~/org-roam.db -d ~/ObsidianVault
```


### Preserving Directory Structure

When your org-roam notes are organized in subdirectories, you can preserve this structure in Obsidian by specifying the base path of your org-roam files:

```bash
# Specify the base path to preserve directory structure
org-roam-to-obsidian -s ~/org-roam.db -d ~/ObsidianVault -b ~/org-roam/
```

For example, if you have a file at `~/org-roam/projects/work/notes.org`, it will be converted to `~/ObsidianVault/projects/work/notes.md` rather than flattening it to just `~/ObsidianVault/notes.md`.


## Conversion Details

### Properties and Refs Handling

Org-roam properties, tags, aliases, and references are converted to YAML frontmatter in Obsidian:

**Org-roam:**
```org
:PROPERTIES:
:ID:       20210505T152634
:ROAM_REFS: https://example.com
:END:
#+FILETAGS: :concept:reference:
#+ROAM_ALIAS: "Knowledge Management"
```

**Obsidian:**
```markdown
---
aliases:
  - Knowledge Management
tags:
  - concept
  - reference
links:
  - https:example.com
---
```

### Link Conversion

Org-roam links are converted to Obsidian's wiki-link format:

**Org-roam:**
```org
[[id:20210505T152634][Example Note]]
```

**Obsidian:**
```markdown
[[Example Note]]
```

## A note on the code

This was almost entirely written with Claude Code, using the 3.7 Sonnet model.
I've never written a code base with Claude Code before, so it was very much a learning experience.

If it were hand-crafted, it would be different. Terser perhaps, with more functions and fewer methods, more iterators and fewer lists. There are almost certainly methods in the database layer that are completely unnecessary.
I'm not going to do a thorough code review, because I want to move on.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request, although I might well be slow in reviewing it.
`CLAUDE.md` has guidelines on how to make changes.

You're welcome to file issues, but I'm unlikely to fix them without substantial compensation.

## Acknowledgments

- [org-roam](https://www.orgroam.com/) project for their excellent personal knowledge management system
- [Obsidian](https://obsidian.md/) for their lovely documentation
- Claude, which wrote most of the code
- [Pandoc](https://pandoc.org/), for being amazing
