# Pyro

A Python CLI for the Papyrus Compiler with PPJ Support for TESV, SSE, and FO4


## Requirements

* Python 3.4+ (Tested with Python 3.7.2)
* [lxml](http://lxml.de/) module (`python -m pip install lxml`)


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


### Supports multiple games

When the game is switched, all paths are generated using the `Installed Path` key in the Windows Registry for the respective games.

You can also set a path explicitly in `pyro.ini` if you are on a non-Windows platform.


### Supports Papyrus Project XML (PPJ) files

* Scripts are compiled individually in parallel.
* Imports are generated from the input path and each script.
* No changes to script names either in scripts or plugins are needed.
* Absolute and relative paths are supported.
* The `<Scripts>` tag and child elements are required.
* The `<Folders>` tag and `NoRecurse` attribute are supported.
* The `<Imports>` tag and child elements are required for third-party libraries.


### Supports incremental PPJ builds

* After the first run, Pyro builds an index for that project containing the file paths and CRC32 hashes of those files.
* When generating commands for the next run, the CRC32 hashes of those files are compared with the indexed file records.
* Commands are not generated for matching records, reducing the work passed on to the compiler.
* Records are updated for previously indexed scripts that have been modified and successfully compiled.
* New records are created for new scripts that have been successfully compiled.


### Supports automatic packaging with BSArch

You can package scripts into BSA and BA2 archives with [BSArch](https://www.nexusmods.com/newvegas/mods/64745).

1. Set the path to `bsarch.exe` in `pyro.ini`.
2. Add the `Archive` attribute to the `PapyrusProject` root element. Set the value to the absolute path to the destination BSA or BA2 archive.
3. Add the `CreateArchive` attribute to the `PapyrusProject` root element. Set the value to `True`.
4. Compile as normal and the compiled scripts will be automatically packaged.


#### Supports packaging arbitrary files

Add the following block before the `</PapyrusProject>` end tag:

```xml
<Includes Root="{absolute path to project root}">
	<Include>{relative path to file in project root}</Include>
	<Include>{...}</Include>
</Includes>
```

Currently, directory includes are not supported.


### Supports anonymizing compiled scripts

When a script is compiled, your system username and computer name are embedded in the binary header. This information can be revealed with a hex editor or decompiler. If your username is your real name, or you are concerned about targeted attacks using your system login, leaving this information intact can present security and/or privacy risks.

Pyro replaces those strings in compiled scripts with random letters, effectively anonymizing compiled scripts.

Simply add the `Anonymize` attribute to the `PapyrusProject` root element. Set the value to `True`.


#### Notes

* A temporary folder will be created and deleted at the `TempPath` specified in `pyro.ini`.
* The compiled scripts to be packaged will be copied there.
* The folder will be removed if the procedure is successful.
 
 
### Supports the Release/Final/Optimize attributes

* The `Release` and `Final` attributes are supported by only the FO4 compiler.
* The `Optimize` attribute is supported for all games.
* The PPJ parser will ignore unsupported attributes.


### Performance 

The native PPJ compiler for FO4 is on average 70 milliseconds faster per script.

Tested with i5-3570k @ 3.4 GHz and six scripts.


## Examples

* [Auto Loot.ppj](https://gist.github.com/fireundubh/7eecf97135b8da74e59133842f0b60f9)
* [Better Favor Jobs SSE.ppj](https://gist.github.com/fireundubh/398a28227d220f0b45cbdb5fa618b75c)
* [Master of Disguise SSE.ppj](https://gist.github.com/fireundubh/cb3094ed851f74326090a681a78d5c5e)


## IDE Integration

* [PyCharm](https://i.imgur.com/dxk5ZfL.jpg)
* [UltraEdit](https://gist.github.com/fireundubh/cca1f4132ca4b000f094294f3f036fa0)
