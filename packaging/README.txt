WinKit — how to use
===================

This folder has three programs:
  winkit-studio\winkit-studio.exe   the app (window). Start here.
  winkit\winkit.exe                 the same on the command line (run as administrator)
  winkit-agent\                     the Agent; Studio copies this folder to the USB drive by itself

With Studio (recommended):
  1. Connect the USB drive with Ventoy and open winkit-studio.exe (it asks for administrator).
  2. Follow the sidebar from top to bottom. The Preferences button changes language and theme.
  3. In "Review and build", click "Build USB drive".

Then boot from Ventoy, choose the Windows ISO and the "winkit-..." template.
The ISO is never modified. Everything WinKit uses lives in the WinKit\ folder of the USB drive.

Command line: winkit\winkit.exe --idioma en-US --help

WARNING: pre-alpha version of a personal project, made for the author's own use as an
experiment, not a released product; whoever uses it is, in practice, a tester. 100%
"vibe-coded" app (written by AI, not fully reviewed by a human and not yet validated on a
real install). It may have bugs and security flaws. Use it at your own risk: all
responsibility lies with the user. Test it in a virtual machine first and back up
beforehand. Details in the LICENSE (Apache 2.0) and NOTICE files.
