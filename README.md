# Pyro

A Python CLI for the Papyrus Compiler with PPJ Support for TESV, SSE, and FO4


## Requirements

* Python 3.4+
* [lxml](http://lxml.de/) module (`python -m pip install lxml`)


## Usage

```
usage: pyro.py [-g {sse,fo4,tesv}] [-i INPUT] [-o OUTPUT] [-q] [-s] [-t]
               [--help] [--version]

required arguments:
  -g {sse,fo4,tesv}  set compiler version
  -i INPUT           absolute path to input file or folder

optional arguments:
  -p                 pack scripts into bsa/ba2 (requires bsarch)

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
* Relative paths are supported.
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
2. Use the `-p` argument for all projects.
3. Add an `Archive` attribute to the `PapyrusProject` root element.
4. Fill that attribute's value with the absolute path to the destination BSA or BA2 archive.
5. Compile as normal and the compiled scripts will be automatically packaged.


#### Notes

* A temporary folder will be created and deleted at the `TempPath` specified in `pyro.ini`.
* The compiled scripts to be packaged will be copied there.
* The folder will be removed if the procedure is successful.
 
 
### Supports Release/Final/Optimize

* The `Release` and `Final` attributes are supported by only the FO4 compiler.
* The `Optimize` attributed is supported for all games.
* The PPJ parser will ignore unsupported attributes.


### Performance 

The native PPJ compiler for FO4 is on average 70 milliseconds faster per script.

Tested with i5-3570k @ 3.4 GHz and six scripts.


## Examples


### Master of Disguise.ppj

```xml
<PapyrusProject xmlns="PapyrusProject.xsd" Flags="TESV_Papyrus_Flags.flg" Output="E:\projects\skyrim\Master of Disguise - Special Edition\scripts">
	<Imports>
		<Import>E:\SKSE SDK\Scripts\Source</Import>
		<Import>E:\SkyUI 5.1 SDK\Scripts\Source</Import>
		<Import>E:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition\Data\Scripts\Source\User</Import>
		<Import>E:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition\Data\Scripts\Source\Base</Import>
	</Imports>
	<Scripts>
		<Script>Master of Disguise\dubhDisguiseMCMHelper.psc</Script>
		<Script>Master of Disguise\dubhDisguiseMCMQuestScript.psc</Script>
		<Script>Master of Disguise\dubhDisguiseMCMStringUtil.psc</Script>
		<Script>Master of Disguise\dubhApplyingEffectScript.psc</Script>
		<Script>Master of Disguise\dubhDisguiseQuestScript.psc</Script>
		<Script>Master of Disguise\dubhFactionEnemyScript.psc</Script>
		<Script>Master of Disguise\dubhMonitorEffectScript.psc</Script>
		<Script>Master of Disguise\dubhPlayerScript.psc</Script>
	</Scripts>
</PapyrusProject>
```


## IDE Integration


### UltraEdit

Go to `Advanced > Tool` Configuration and click the Insert button.

1. `[Command Tab]` **Menu item name** = `Compile Papyrus (FO4)`
2. `[Command Tab]` **Command line** = `python pyro.py -g fo4 -i "%p%n%e"`
3. `[Options Tab]` **Program type: DOS program** = `True`
4. `[Options Tab]` **Save active file** = `True`
5. `[Output Tab]` **Command output: Output to list box** = `True`
6. `[Output Tab]` **Command output: Capture output** = `True`
7. `[Output Tab]` **Command output: Handle output as Unicode** = `True`
8. `[Output Tab]` **Replace selected text with: No replace** = `True`
9. Do not set a working directory. Click `OK`.

Open a script or project file, and press `Ctrl+Shift+#` to compile that script or project file. (Go to Advanced to see your custom menu items and their hotkeys.)

For the command line, you may need to use absolute paths to `python.exe` and `pyro.py` depending on your development environment.


## TODO

- Add support for using a third-party compiler (i.e., Caprica for FO4)
- Add support for reporting physical lines of code
- Add support for writing timestamped log files
- Add support for parsing INI and JSON files instead of, or in addition to, PPJ XML files
