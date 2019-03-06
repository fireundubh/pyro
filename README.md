# Pyro

Pyro is a semi-automated incremental build system for _Skyrim Classic_ (TESV), _Skyrim Special Edition_ (SSE), and _Fallout 4_ (FO4) projects. Pyro makes quick work of the process for creating new builds of mods for those games.

Fundamentally, Pyro is a command-line interface (CLI) that parses customized Papyrus Project (PPJ) files into actionable data and passes that data to Bethesda Softworks' Papyrus Compiler and zilav's BSArch.

Pyro automates most build tasks and can play a key role in an automated build and release pipeline. Pyro can also be integrated as an external tool within virtually any IDE, allowing modders to build their projects with a single hotkey.


## Requirements

* Python 3.4+ (Tested with Python 3.7.2) - [Download (python.org)](https://www.python.org/downloads/)
* lxml module (`python3 -m pip install lxml`) - [Documentation (lxml.de)](http://lxml.de/)
* BSArch (only for automatic BSA/BA2 packaging) - [Download (nexusmods.com)](https://www.nexusmods.com/newvegas/mods/64745)
* an Extended PPJ XML document for your project - [Examples](https://github.com/fireundubh/pyro#examples)


## Usage

```
usage: pyro [-g {fo4,tesv,sse}] [-i INPUT] [--disable-anonymizer]
            [--disable-bsarch] [--disable-indexer] [--help] [--version]

required arguments:
  -g {sse,fo4,tesv}  set compiler version
  -i INPUT           absolute path to input file or folder

optional arguments:
  --disable-anonymizer  do not anonymize script metadata
  --disable-bsarch      do not pack scripts with BSArch
  --disable-indexer     do not index scripts

program arguments:
  --help             show help and exit
  --version          show program's version number and exit
```

## Features

### Overview

**Current Features**

- Supports multiple games (TESV, SSE, FO4)
- Supports Extended Papyrus Project XML (PPJ) documents
- Incremental, parallelized PPJ builds
- Automatically packages scripts and non-script assets with BSArch
- Anonymizes compiled scripts

**Future Features**

- Automatic generation of Extended PPJ files
- Automatic generation of ZIP archives for distribution
- Automatic, parallelized generation of multiple BSA/BA2 archives
- Support folder includes for automatically packaging non-script assets
- XML validation, or move to YAML (undecided)


### Feature Details

#### Multiple Game Support

Pyro supports the TESV, SSE, and FO4 compilers.

When the game is switched, all paths are generated using the `Installed Path` key in the Windows Registry for the respective games.

You can also set a path explicitly in `pyro.ini` if you are on a non-Windows platform.


#### Extended Papyrus Project XML (PPJ)

The PPJ format was introduced with the FO4 version of the Papyrus Compiler, which was not backported to TESV and SSE. Pyro can parse all standard PPJ elements and attributes, in addition to several of its own, for TESV, SSE, and FO4 projects.

Element | Support
:--- | :---
`<PapyrusProject>` | This element and its Flags, Output, Optimize, Release, and Final attributes are supported. Pyro also supports, if not requires, the new Archive, CreateArchive, and Anonymize attributes.
`<Imports>` | This element and its children `<Import>` contain absolute paths to a game's base scripts, a mod's user scripts, and third-party SDK scripts.
`<Scripts>` | This element and its children `<Script>` contain absolute or relative paths to a mod's user scripts.
`<Folders>` | This element and its children `<Folder>` contain absolute or relative paths to folders containing a mod's user scripts. The parent element's `NoRecurse` attribute is also supported.
`<Includes>` | This new element and its children `<Include>` contain absolute or relative paths to arbitrary files to be packaged in the mod's BSA or BA2 archive. The parent element has a `Root` attribute that contains the absolute path to the root of the relative Include paths, assuming relative paths are used.


#### Incremental Build with Parallelized Compilation

What is incremental build? Basically, incremental build means that only the files that need to be compiled will be compiled. Incremental build vastly accelerates the build process by eliminating redundant work.

Here's how the incremental build system works:

* After the first run, Pyro builds an index for that project containing the file paths and CRC32 hashes of those files.
* When generating commands for the next run, the CRC32 hashes of those files are compared with the indexed file records.
* Commands are not generated for matching records, reducing the work passed on to the compiler.
* Records are updated for previously indexed scripts that have been modified and successfully compiled.
* New records are created for new scripts that have been successfully compiled.

In addition, Pyro will spawn multiple instances of the Papyrus Compiler in parallel to further reduce build times.


#### Automatic BSA/BA2 Packaging 

You can package scripts into BSA and BA2 archives with [BSArch](https://www.nexusmods.com/newvegas/mods/64745).

1. Set the path to `bsarch.exe` in `pyro.ini`.
2. Add the `Archive` attribute to the `PapyrusProject` root element. Set the value to the absolute path to the destination BSA or BA2 archive.
3. Add the `CreateArchive` attribute to the `PapyrusProject` root element. Set the value to `True`.
4. Compile as normal and the compiled scripts will be automatically packaged.

To package arbitrary files, add the following block before the `</PapyrusProject>` end tag:

```xml
<Includes Root="{absolute path to project root}">
	<Include>{relative path to file in project root}</Include>
	<Include>{...}</Include>
</Includes>
```

Currently, folder includes are not supported.

##### Notes

* A temporary folder will be created and deleted at the `TempPath` specified in `pyro.ini`.
* The compiled scripts and any arbitrary includes to be packaged will be copied there.
* The folder will be removed if the procedure is successful.


### Script Anonymization

When a script is compiled, your system username and computer name are embedded in the binary header. This information can be revealed with a hex editor or decompiler. If your username is your real name, or you are concerned about targeted attacks using your system login, leaving this information intact can present security and/or privacy risks.

Pyro replaces those strings in compiled scripts with random letters, effectively anonymizing compiled scripts.

Simply add the `Anonymize` attribute to the `PapyrusProject` root element. Set the value to `True`.


### Benchmarks 

* The native PPJ compiler for FO4 is on average 70 milliseconds faster per script. Tested with i5-3570k @ 3.4 GHz and 6 scripts.


## Examples

* [Auto Loot.ppj](https://gist.github.com/fireundubh/7eecf97135b8da74e59133842f0b60f9)
* [Better Favor Jobs SSE.ppj](https://gist.github.com/fireundubh/398a28227d220f0b45cbdb5fa618b75c)
* [Master of Disguise SSE.ppj](https://gist.github.com/fireundubh/cb3094ed851f74326090a681a78d5c5e)


## IDE Integration

* [PyCharm](https://i.imgur.com/dxk5ZfL.jpg)
* [UltraEdit](https://gist.github.com/fireundubh/cca1f4132ca4b000f094294f3f036fa0)
