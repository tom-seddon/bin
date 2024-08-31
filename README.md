# command line tools

Various un(der)documented command line tools from my `bin` folder.
Most should work on Mac OS X and Windows, and probably Linux too.

Most respond to `-h`.

Licence is GPL unless otherwise specified.

# C/C++ Stuff

## bin2cstr *(Python 2)*

Convert a binary file into a list of C-style strings. You can paste
the result into a Python or C program, copy it to a file and #include
it into a C program, and so on.

Specify -, to have a comma after each line of input, giving you an
array of strings, one per line; specify -n - probably most useful in
conjunction with -, - to leave the newlines out of the strings.

List files to process on the command line, or specify no files to have
it read stdin.

## bin2hex

Convert a binary file into comma-separated hex values. You can paste
the result into a Python or C program, copy it to a file and #include
it into a C program, and so on.

## mkhc

Makes a pair of files, .h and .cpp/.c/.m/.mm, with some skeleton C++
code in. Automatically generates sensible header guard defines and,
when generating C++ .h files, some markup so emacs knows they're not
C.

There are various options, that you can supply on the command line.

To keep files consistent, mkhc will look in the current folder, and
any parents, for a file, `.mkhc`. If it finds it, it will read
additional command line options from it, one per line. The long form
of each option should be specified, without the leading `--`. For
example:

    header-folder=h/shared
    src-folder=c
    c
    extern-c

This is equivalent to running mkhc as follows:

    mkhc --header-folder=h/shared --src-folder=c --c --extern-c

Lines beginning with `#` are comments.

By default, `mkhc` stops searching at the first `.mkhc` file it finds,
but you can add the special magic comment `#..` (just like that, on
its own line, with no spaces) to have mkhc keep searching parent
folders for more `.mkhc` files.

When specifying paths in a `.mkhc`, specify them relative to the
folder the `.mkhc` is in.

(Run `mkhc -v`, possibly with additional options, to show the options
that will be used, taking into account any `.mkhc` files read.)

# Shell Stuff

## branchtool

Look after sets of branches named `CATEGORY/NAME`. List branches and
categories. Find branches merged into another branch - candidates for
deletion. Find branches not merged into another branch - candidates
for force deletion, or possible recategorization.

## change_ext /(Python 2)/

Batch change of file extensions.

## commas

Prints input received on stdin, with thousands separators added to any
numbers printed.

    > p4 sync -N ...
    Server network estimates: files added/updated/deleted=3913/1635/0, bytes added/updated=1593990200/1166508036
    > p4 sync -N ... | commas
    Server network estimates: files added/updated/deleted=3,913/1,635/0, bytes added/updated=1,593,990,200/1,166,508,036

## count /(Python 2)/

Counts occurrences of contents of lines on stdin, and prints the
tallies.

## dateize /(Python 2)/

Move files into folders according to their creation date.

## diff2

Does a folder diff without printing out too much verbiage.

Can optionally invoke `diff` on edited files, to get the verbiage
back.

## dump

A version of the handy `#DUMP` command from the BBC Micro.

## find_dup

Find duplicate files.

## foreach

Reads a list of files on stdin, one per line, and executes a command
for each file.

(This works like `xargs`, but it makes lighter work of files that have
spaces in their names, and can work with the output from a wider range
of tools, particularly on Windows.)

## mkpasswd

Makes up a random password that can be copied from iTerm2 with one
double-click.

## modify /(Python 2)/

Modifies a file by changing every byte. For binary files, each byte is
XORed with 255; for ASCII text files (use `-a`), it does a rot47 on
the 94 printable chars. (`-a` may not actually change anything, of
course, if the file isn't really ASCII.)

## picsplit /(Python 2)/

Splits an image into equally-sized tiles, possibly after removing
border regions based on alpha channel. The tiles can optionally be
generated overlapping, to avoid gaps due to transformation
inaccuracies.

Dependencies: PIL

## pmacs

Sends stdin to emacs via `emacsclient`, so you can use emacs as the
target of pipes.

If using recentf, add the following to your `.emacs`:

    (add-to-list 'recentf-exclude "pmacs\\.[0-9]+\\.dat$")

# WAV/MP3 Stuff

## compress_wavs /(Python 2)/

Batch convert WAVs and FLACs to MP3s. Useful for devices that have
limited storage, don't support FLAC, etc.

(lame is run with `--preset insane`, so 320Kbps output. This is
compatible with all the playback devices I use.)

Dependencies: lame, flac tools (if converting FLACs), GNU make

## find_mp3_residue /(Python 2)/

Find MP3 "residue" (a poor choice of terminology, sorry!) - the
difference between the signal in the original WAV and the signal in
the MP3.

Specify the name of a .wav file. It will compress it to MP3 using
various settings (both CBR and VBR), then for each set of settings it
will produce a WAV that's the difference between that MP3 and the
original WAV. The 128kbps one will probably be noisy; the 320kbps one
will probably be very quiet.

Inspired by: http://ryanmaguiremusic.com/theghostinthemp3.html

Dependencies: GNU make, mpg123, lame, rm, flac (only needed if you use
a flac file as input)

## make_looping_mp3 /(Python 2)/

Makes a seamlessly-looping MP3 from a WAV file. Requires LAME
(http://lame.sourceforge.net/).

For the principle, see http://www.compuphase.com/mp3/mp3loops.htm.

## wavdump /(Python 2)/

Lists WAV file chunks. Pretty-prints chunks it knows about.

# Ancient iOS/Xcode Stuff

I haven't done any iOS stuff for years. This stuff probably no longer
works.

## improve-xcode-asm-output /(Python 2)/

Takes asm output from Xcode on stdin, and prints it to stdout, only
with `.loc` directives replaced with the actual lines from the
original source code. This is what Visual C++ does, and it's very
handy...

(To get asm output from Xcode, click the button at the top left of the
text edit window - it looks like a little 4x2 grid, I've no idea what
it's supposed to be - and select `Assembly` from the menu.)

You can copy the result from Xcode and use `pbpaste` to pipe it
through `improve-xcode-asm-output`, e.g.:

    pbpaste | ./improve-xcode-asm-output.py

## iosids /(Python 2)/

Helper script for importing device IDs en masse into the developer
portal without endless "this devices already exists" errors.

How to use:

1. Ask Test Flight to export device IDs list for your team
   members. You'll get a file called something like
   `testflight_devices.txt` in your downloads folder.

2. Visit the iOS Provisioning Portal, Devices section. Use File>Save
   As to save the page in Page Source format (i.e., an HTML file).

3. Run this script, supplying name of HTML file and devices txt. The
   output is all device identifiers and device names that are
   mentioned in the Test Flight devices list, but not in the
   provisioning portal. Redirect the output to a .txt file, since
   you'll need it in the next step:

    ./iosids.py /tmp/Devices\ -\ iOS\ Provisioning\ Portal\ -\ Apple\ Developer.html ~/Downloads/testflight_devices.txt > /tmp/devices.txt

4. Use the Upload Devices button in the Provisioning Portal to bulk
   add the new devices. Point it at the text file created in step 3.

## symcrash /(Python 2)/

Symbolicates a crash log from the iPhone. Apple supply a perl script
to do this, but it relies on spotlight having indexed the dSYM folders
for the binaries. It never seems to do that on my system, so the
script always fails. I believe you can use Xcode to do it, too. But I
don't like perl, and I don't like Xcode.

`symcrash` uses spotlight to search for dSYM files by file name, which
appears to be perfectly reliable, then looks through all the dSYMs
found to find the one for the binary in question.

(`symcrash` does not support as many different kinds of crash log
types as Apple's perl script.)

# Atari ST Stuff

## relocate_prg

Converts an Atari ST GEMDOS format executable file (.PRG/.TOS/.TTP)
into a memory image suitable for use by a disassembler. It loads the
program in, relocates it, puts the zero-filled BSS in the right place,
then saves the result. Have your disassembler start from the first
byte (which is the usual `BRA *+$1E`).

## stdisk

Extract files from Atari ST trackwise floppy disk images.

(May also be suitable for DOS disks, which have a very similar format,
but that's untested.)

## strom

Split Atari ST ROM images into banks, for programming into multiple
PROMs. Also verify ROM checksums present in TOS 2.06+.

# Windows Stuff

## fix_vpn_route_table

Modify route tables when using VPN that takes over your PC's entire
network interface. Removes VPN routes for internet and LAN, and
(optionally) reinstates them for specified address ranges
corresponding to whichever VPN resources you need to use.

## vsoutput

Handle Visual Studio multithreaded build output.

## window_placement

Use `list` to list windows (optionally filtering by PID or window
title) and their base64-encoded placement data. 

Use `set` to set a single window's placement (filtering by PID or
title is required) using the data printed out by `list`. 

Intended workflow:

1. have batch file or whatever that runs a few programs that open
   windows in random places

2. run batch file and arrange windows in desired layout

3. use `window_placement list` interactively, to get the placement
   data for each window of interest

4. add `window_placement set` invocations to batch file (or wrapper
   of) so that the desired window layout is reproduced on each run

# macOS Stuff

## svnsync_remote /(Python 2)/

Does an `svnsync` from a remote repo.

## tma

Analyze Time Machine backups. There are various options, but just run
it like this, from your Time Machine backups folder:

    tma -wum

This tells you how the most recent backup differed from the
penultimate one. Handy if Time Machine backs up a ton of stuff, and
you're not sure why.

# TextScripts/

Various text-processing scripts for use with a text editor.

For emacs, use `M-x shell-command-on-region`.

For Visual Studio 2012 and later, use my VSScripts addin from
https://github.com/tom-seddon/VSScripts.

# Third Party Stuff

See each file for the licence.

## img_fingerprint, pdb_fingerprint_from_img

See https://github.com/chromium/chromium/tree/master/tools/symsrc

## pefile

https://github.com/erocarrera/pefile

# Half baked/WIP Stuff

Written with the intent of being useful, but, for now, at your own
risk...

## dmp_modules /(Windows only)/ /(Python 2)/

Invokes
[`cdb`](https://docs.microsoft.com/en-us/windows-hardware/drivers/debugger/debugger-download-tools)
to print a list of the modules in a Windows .dmp file.

## find_exe_or_pdb /(Python 2)/

Finds a Windows .exe or .pdb by embedded timestamp in a folder
structure. This is the info used to find the .pdb that matches a .exe;
when you have one of the pair, this might help you find the other.

For a bit more about this, see
http://www.debuginfo.com/articles/debuginfomatch.html

## pdb_info /(Python 2)/

Print some info about a .pdb file.

For an overview of the pdb format, see
https://llvm.org/docs/PDB/MsfFile.html

## pe_header /(Python 2)/

Print some stuff - though not much, at least yet - from an EXE header.

This is a tiny little bit like `dumpbin /headers EXE` in a Visual
Studio command prompt, but the output is a compact, one-line format,
for easier interop with `grep` or `findstr`.

For an overview of the PE format, see
https://en.wikipedia.org/wiki/Portable_Executable
