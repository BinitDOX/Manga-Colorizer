# To use this extension in Chrome (or any Chromium browser like Brave) from a folder:
0. Make sure your Backend API is running (app-stream.py instead of app.py) and you have its URL.
1. In the browser visit <code>chrome://extensions/</code>
1. Turn on developer mode.
1. Click 'Load Unpacked'.
1. Navigate into the Frontend-Chrome-AnySite folder and click 'Select Folder'. Manga Colorizer settings  should open in a new tab.
1. Type or paste your API URL (it should look kind of like https://?.?.?.?:5000/) in the first blank.
1. Press 'Test' button to see if it works. Expect a security warning because your API is not running with a real security certificate.
1. Click 'Advanced' and click the link 'Proceed to ...'
1. If you see 'Manga Colorizer is Up and Running!' it is working!
1. Close the tab with the message and the tab with Manga Colorizer settings.
1. Open a page that has some black-and-white manga.
1. Optional: Open the Extensions menu (looks like a puzzle piece) and click the pin next to 'Any Manga Colorizer' to add its icon to your toolbar.
1. Click 'Any Manga Colorizer' in the Extensions menu or its icon on the toolbar to open its settings as a popup.
1. Optional: Press the 'Add ...' button to add this site to the list of Manga Sites so it will automatically color images on this site without having to open the settings.
1. Press 'Colorize!'

Hopefully it runs and the uncolored images you see automatically turn into colored images. It can take a minute and you may want to open the developer console to see messages about progress or problems. (Ctrl + Shift + I or F12 on Windows and Linux, or Cmd + Opt + I on macOS, then find the Console tab at the top of the tools that just opened.)

Test your API URL again whenever it stops working. The browser eventually forgets that you said this URL is safe and sometimes your URL may change.
