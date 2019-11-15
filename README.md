# Pyro

Pyro is a semi-automated incremental build system for _Skyrim Classic_ (TESV), _Skyrim Special Edition_ (SSE), and _Fallout 4_ (FO4) projects. Pyro makes quick work of the process for creating new builds of mods for those games.

Fundamentally, Pyro is a command-line interface (CLI) that parses customized Papyrus Project (PPJ) files into actionable data and passes that data to Bethesda Softworks' Papyrus Compiler and zilav's BSArch.

Pyro automates most build tasks and can play a key role in an automated build and release pipeline. Pyro can also be integrated as an external tool within virtually any IDE, allowing modders to build their projects with a single hotkey.

## Binaries

Latest build: [![](https://github.com/fireundubh/pyro/workflows/GitHub%20CI/badge.svg)](https://github.com/fireundubh/pyro/actions)

Or build Pyro from source. Refer to the [Compiling](#compiling) section for details.

## Table of Contents

- [Features](#features)
  - [Overview](#overview)
  - [Multiple Game Support](#multiple-game-support)
  - [Extended PPJ Format](#extended-ppj-format)
  - [Incremental Build with Parallelized Compilation](#incremental-build-with-parallelized-compilation)
  - [Automatic BSA/BA2 Packaging](#automatic-bsaba2-packaging)
  - [Script Anonymization](#script-anonymization)
- [Resources](#resources)
  - [Example PPJ Files](#example-ppj-files)
  - [IDE Integration](#ide-integration)
- [Contributing](#contributing)
  - [License](#license)
  - [Compiling](#compiling)


## Features

### Overview

**Current Features**

- Supports multiple games (TESV, SSE, FO4)
- Supports Extended Papyrus Project XML (PPJ) documents
- Incremental, parallelized PPJ builds
- Automatically packages scripts _and_ non-script assets with BSArch
- Anonymizes compiled scripts

**Future Features**

- Automatic generation of Extended PPJ files from folders and ZIP archives
- Automatic generation of ZIP archives for distribution
- Automatic parallelized generation of multiple BSA/BA2 archives
- Support automated test assets
- Support folder includes for automatically packaging non-script assets
- Support YAML project files


### Multiple Game Support

Pyro supports the TESV, SSE, and FO4 compilers.

When the game is switched, all paths are generated using the `Installed Path` key in the Windows Registry for the respective games.

You can also set a path explicitly with the `--game-path` argument if you are on a non-Windows platform.


### Extended PPJ Format

The PPJ format was introduced with the FO4 version of the Papyrus Compiler, which was not backported to TESV and SSE. Pyro can parse all standard PPJ elements and attributes, in addition to several of its own, for TESV, SSE, and FO4 projects.


#### Elements

Element | Support
:--- | :---
`<PapyrusProject>` | This element and its `Flags`, `Output`, `Optimize`, `Release` (FO4 only), and `Final` (FO4 only) attributes are supported. The new `Archive`, `CreateArchive`, and `Anonymize` attributes are also required.
`<Imports>` | This element and its children `<Import>` contain absolute paths to a game's base scripts, a mod's user scripts, and third-party SDK scripts.
`<Scripts>` | This element and its children `<Script>` contain absolute or relative paths to a mod's user scripts.
`<Folders>` | This element and its children `<Folder>` contain absolute or relative paths to folders containing a mod's user scripts. The parent element's `NoRecurse` attribute is also supported.
`<Includes>` | This new element and its children `<Include>` contain relative paths to arbitrary files to be packaged in the mod's BSA or BA2 archive. The parent element has a `Root` attribute that contains the absolute path to the root of the relative Include paths.


#### Attributes

Element | Attribute | Data Type | Value
:--- | :--- | :--- | :---
PapyrusProject | Flags | String | file name with extension
PapyrusProject | Game | String | game type: fo4, tesv, sse
PapyrusProject | Output | String | absolute path to folder
PapyrusProject | Optimize | Boolean | true or false
PapyrusProject | Release | Boolean | true or false
PapyrusProject | Final | Boolean | true or false
PapyrusProject | Archive | String | absolute path to file name with extension
PapyrusProject | CreateArchive | Boolean | true or false
PapyrusProject | Anonymize | Boolean | true or false
Folders | NoRecurse | Boolean | true or false
Includes | Root | String | absolute path to folder


### Incremental Build with Parallelized Compilation

Incremental build _vastly_ accelerates builds by compiling only scripts that need to be compiled.

The incremental build system determines which PSC files to compile by comparing the last modified timestamp on PSC files with the compilation timestamps encoded in PEX files by the Papyrus Compiler.

Pyro then builds commands to be passed to the Papyrus Compiler and spawn multiple instances of the Papyrus Compiler in parallel to further reduce build times.


#### Benchmarks

The native PPJ compiler for FO4 is on average 70 ms faster per script. Tested with i5-3570k @ 3.4 GHz and 6 scripts.

However, there is no native PPJ compiler for TESV and SSE. Pyro fills that role.


### Automatic BSA/BA2 Packaging

You can package scripts into BSA and BA2 archives with [BSArch](https://www.nexusmods.com/newvegas/mods/64745).

1. Copy `bsarch.exe` to the `pyro\tools` folder, if the file does not exist.
2. The path to `bsarch.exe` should be automatically detected. If not, use the `--bsarch-path` argument to set the path.
3. Add the `Archive` attribute to the `PapyrusProject` root element. Set the value to the absolute path to the destination BSA or BA2 archive.
4. Add the `CreateArchive` attribute to the `PapyrusProject` root element. Set the value to `True`.
5. Compile as normal and the compiled scripts will be automatically packaged.

To package arbitrary files, add the following block before the `</PapyrusProject>` end tag:

```xml
<Includes Root="{absolute path to project root}">
	<Include>{relative path to file in project root}</Include>
	<Include>{...}</Include>
</Includes>
```

Currently, folder includes are not supported.


#### Notes

* A temporary folder will be created and deleted at a default temporary path or path specified by `--temp-path`.
* The compiled scripts and any arbitrary includes to be packaged will be copied to the temporary folder.
* The temporary folder will be removed if the procedure is successful.


### Script Anonymization

When a script is compiled, your system username and computer name are embedded in the binary header. This information can be revealed with a hex editor or decompiler. If your username is your real name, or you are concerned about targeted attacks using your system login, leaving this information intact can present security and/or privacy risks.

Pyro replaces those strings in compiled scripts with random letters, effectively anonymizing compiled scripts.

Simply add the `Anonymize` attribute to the `PapyrusProject` root element. Set the value to `True`.


## Resources

### Example PPJ Files

* [Auto Loot.ppj](https://gist.github.com/fireundubh/7eecf97135b8da74e59133842f0b60f9)
* [Better Favor Jobs SSE.ppj](https://gist.github.com/fireundubh/398a28227d220f0b45cbdb5fa618b75c)
* [Master of Disguise SSE.ppj](https://gist.github.com/fireundubh/cb3094ed851f74326090a681a78d5c5e)


### IDE Integration

* [PyCharm](https://i.imgur.com/dxk5ZfL.jpg)
* [UltraEdit](https://gist.github.com/fireundubh/cca1f4132ca4b000f094294f3f036fa0)


## Contributing

### License

Pyro is open source and licensed under the MIT License.

BSArch is licensed under the MPL-2.0 license. The binary included in this repository and distributions of Pyro was compiled from the original unmodified source code available [here](https://github.com/ElminsterAU/xEdit/tree/master/Tools/BSArchive).

### Compiling

First, install `pipenv`.

Python | Command
:--- | :--
CPython | `pip install pipenv`
Anaconda | `conda install -c conda-forge pipenv`

Set up the pipenv environment:

1. Change the current working directory to the Pyro source folder.
2. Run: `pipenv install`

The build process uses [Nuitka](https://nuitka.net/) which will be installed in the project environment by pipenv. Nuitka will need **clang**, **mingw**, or **MSVC**. To use MSVC, you will need to use the Developer Command Prompt for a Nuitka-supported version of MSVC.

Using the Developer Command Prompt, or any shell with access to development tools, run:

`pipenv run python build.py`

Executing this command will create a `pyro.dist` directory that contains the executable and required libraries and modules. A ZIP archive will be created in the `bin` folder.

#### Build Script

The build script has three arguments.

Short Argument | Long Argument |  Help
:--- | :--- | :---
`-p` | `--package-name` | Specifies package/executable name. Default: `pyro`.
&mdash; | `--loose` | Skips ZIP generation. Useful for CI.
&mdash; | `--mingw64` | Forces Nuitka to use mingw64. Not tested.
