# Org-Roam to Obsidian Converter

## Overview

`org-roam-to-obsidian` is a command-line tool that converts your org-roam personal wiki into an Obsidian vault, preserving your notes, links, and metadata while transforming them into Obsidian's Markdown format.

## Features

- Converts Org-roam `.org` files to Obsidian-compatible Markdown
- Preserves internal links and transforms them to Obsidian's `[[]]` format
- Migrates tags and properties to YAML frontmatter
- Handles attachments and embedded images
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
--source, -s         Path to your org-roam database file
--destination, -d    Path for the new Obsidian vault
--config, -c         Path to a config file (optional)
--dry-run            Test the conversion without writing files
--verbose, -v        Show detailed conversion information
--help, -h           Display this help message
```

## Configuration

Create a `config.yml` file to customize conversion behavior:

```yaml
# Default configuration
conversion:
  preserve_creation_date: true
  frontmatter_format: yaml
  convert_tags: true
  link_format: "[[${filename}]]"

attachments:
  copy_attachments: true
  attachment_folder: "assets"

formatting:
  convert_tables: true
  convert_code_blocks: true
  convert_latex: true
```

## Examples

### Basic Conversion

```bash
# Convert your entire Org-roam wiki
org-roam-to-obsidian -s ~/org-roam.db -d ~/ObsidianVault
```

### Using a Config File

```bash
# Use custom configuration
org-roam-to-obsidian -s ~/org-roam.db -d ~/ObsidianVault -c my-config.yml
```

## Conversion Details

### Properties Handling

Org-roam properties are converted to YAML frontmatter in Obsidian:

**Org-roam:**
```org
:PROPERTIES:
:ID:       20210505T152634
:ROAM_REFS: https://example.com
:END:
```

**Obsidian:**
```markdown
---
id: 20210505T152634
aliases: []
tags: []
refs: https://example.com
---
```

### Link Conversion

Org-roam links are converted to Obsidian's wiki-link format:

**Org-roam:**
```org
[[file:20210505T152634-example.org][Example Note]]
```

**Obsidian:**
```markdown
[[Example Note]]
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- org-roam project for their excellent personal knowledge management system
- Obsidian for their powerful note-taking application
