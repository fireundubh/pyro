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
  -ns NAMESPACE      namespace for single script compilation
  -o OUTPUT          absolute path to output folder (default: ..)
  -q                 report only compiler failures
  -s                 skip output validation

program arguments:
  --help             show help and exit
  --version          show program's version number and exit
```

## Features

### Supports multiple games

When the game is switched, all paths are generated using the `Installed Path` key in the Windows Registry for the respective games.

You can also set a path explicitly in `pyro.ini` if you are on a non-Windows platform.
 

### Supports recursive compilation

The CLI can compile single `.psc` files and folders recursively.

Fallout 4 scripts are compiled with the `-release`, and `-final` arguments.
 

### Supports Papyrus Project XML (PPJ) files

* Compiles each script individually in parallel
* Generates imports from both the input path and `<Scripts>`
* No changes to script names in scripts or plugins are needed
* The `<Scripts>` tag is required.
* The `<Imports>` tag is required only for third-party libraries, like SKSE, etc.
* The `<Folders>` tag is not supported.

 
#### Notes: Release/Final/Optimize

The `Release` and `Final` attributes are supported by only the FO4 compiler.

The PPJ parser will ignore unsupported attributes.

`Optimize` is unsupported because the official recommendation is not use it.


#### Notes: Performance 

The native PPJ compiler for FO4 is around 4 seconds faster, but TESV and SSE do not have a PPJ compiler.


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
2. `[Command Tab]` **Command line** = `python pyro.py -g fo4 -i "%p%n%e" -p`
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
- Add support for custom imports in shell (PPJ already supports custom imports)
- Add support for importing DLC scripts explicitly
- Add support for importing SKSE and F4SE scripts explicitly
- Add support for third-party PEX decompilers
- Add support for packaging compiled and/or source scripts into BA2 archives (FO4 only)
- Add support for reporting physical lines of code
- Add support for writing timestamped log files
- Add support for parsing INI and JSON files instead of, or in addition to, PPJ XML files
- Add support for parsing custom XML tags in all PPJ files to tell Pyro how to BURN BABY BURN
