# To load this extension in Firefox from a folder:
0. Make sure your Backend API is running and you have its URL.
1. Open `about:debugging#/runtime/this-firefox` in the Firefox address bar.
2. Click 'Load Temporary Add-on'
3. Open the extension's directory and double-click manifest.json.
If the extension loads correctly, you will see its settings page. Close it for now, we will get back to it later.
4. Open a page that has some black-and-white manga.
5. Open the Extensions menu (looks like a puzzle piece), right-click 'Any Manga Colorizer' and select 'Always allow on ...'
6. Open the Extensions menu again and left-click 'Any Manga Colorizer' to open its settings as a popup.
7. Type or paste your API URL (it should look kind of like https://?.?.?.?:5000/) in the first blank.
8. Press 'Test' button to see if it works. Expect a security warning because your API is not running with a real security certificate.
9. Click 'Advanced' and click 'Accept the risk and continue'.
10. If you see 'Manga Colorizer is Up and Running!' it is working!
11. Close the tab with the message and return to your manga page.
12. Left-click 'Any Manga Colorizer' in the Extensions menu again to open its settings.
13. Add the manga site you want to test to the list of Manga Sites. Just include the domain name.
14. Press 'Colorize!'

Hopefully it runs and the uncolored images you see automatically turn into colored images. It can take a minute and you may want to open the developer console to see messages about progress or problems. (From the menu select Tools > Web Developer > Web Developer Tools or use the keyboard shortcut Ctrl + Shift + I or F12 on Windows and Linux, or Cmd + Opt + I on macOS, then find the Console tab at the top of the tools that just opened.)

You will need to repeat most of these steps each time you restart Firefox.The process will be easier once a published version of this extension is available.

For details about testing in Firefox, see Firefox instructions:
https://extensionworkshop.com/documentation/develop/temporary-installation-in-firefox/
