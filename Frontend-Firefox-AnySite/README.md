# To load this extension in Firefox from a folder:
0. Make sure your Backend API is running (use app-stream.py instead of app.py) and you have its URL.
1. Open `about:debugging#/runtime/this-firefox` in the Firefox address bar.
1. Click 'Load Temporary Add-on'
1. Open the extension's directory and double-click manifest.json.
If the extension loads correctly, you will see its settings page.
1. Type or paste your API URL (it should look kind of like https://?.?.?.?:5000/) in the first blank.
1. Press 'Test' button to see if it works. Expect a security warning because your API is not running with a real security certificate.
1. Click 'Advanced' and click 'Accept the risk and continue'.
1. If you see 'Manga Colorizer is Up and Running!' it is working!
1. Close the tab with the message and the tab with Manga Colorizer settings.
1. Open a page that has some black-and-white manga.
1. Open the Extensions menu (looks like a puzzle piece), right-click 'Any Manga Colorizer' and select 'Always allow on ...'
1. Optional: Open the Extensions menu and click the gear next to 'Any Manga Colorizer' and choose 'Pin to Toolbar'.
1. Click 'Any Manga Colorizer' in the Extensions menu or its icon on the toolbar to open its settings as a popup.
1. Optional: Press the 'Add ...' button to add this site to the list of Manga Sites so it will automatically color images on this site without having to open the settings.
1. Press 'Colorize!'

Hopefully it runs and the uncolored images you see automatically turn into colored images. It can take a minute and you may want to open the developer console to see messages about progress or problems. (From the menu select Tools > Web Developer > Web Developer Tools or use the keyboard shortcut Ctrl + Shift + I or F12 on Windows and Linux, or Cmd + Opt + I on macOS, then find the Console tab at the top of the tools that just opened.)

You will need to repeat most of these steps each time you restart Firefox. The process will be easier once a published version of this extension is available.

For details about testing in Firefox, see Firefox instructions:
https://extensionworkshop.com/documentation/develop/temporary-installation-in-firefox/
