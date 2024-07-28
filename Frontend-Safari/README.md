To test in Safari on Mac or iOS, follow these instructions:
https://developer.apple.com/documentation/safariservices/safari_web_extensions/running_your_safari_web_extension

This is a much more involved process than adding an extension to other browsers. You need Xcode and have to use your Apple ID as your development team. You can get this extension working on your own computer or iPhone or iPad without paying to become an official Apple developer. You only need to do that if you want to submit it to the app store. You need to set up each device for software development, and each Safari for running unsigned extensions, which decreases your security somewhat.

After getting the extension installed, the steps to get it working are similar to other browsers:

0. Make sure your Backend API is running (use app-stream.py instead of app.py) and you have its URL.
1. When the extension first loads, you should see its settings in a new tab and you should see a prompt with all the permissions the extension wants. This may look like a long list of permissions if you have several tabs open because it wants to look through all your tabs to see if any are the manga sites it knows about. As the author of the extension I give it permission on all URLs, but you do not have to agree to all of that. You can visit each site you want to use it on and enable the extension for it.
2. Close settings tab. We will get back to it later.
3. Open a page that has some black-and-white manga.
4. Open Manga Streaming Colorizer in Extensions and tell it to always allow for this site.
5. The settings should show up again (in a popup on MacOS or a tab in iOS). Type or paste your API URL (it should look kind of like https://?.?.?.?:5000/) in the first blank.
6. Press 'Test' button to see if it works. Expect a security warning the first time because your API is not running with a real security certificate. Depending on your OS, the messages may differ, but keep clicking Advanced and Allow.
7. If you see 'Manga Colorizer is Up and Running!' it is working!
8. Close the tab with the 'Manga Colorizer is Up and Running!' message and return to the Manga Colorizer settings. If you don't see the settings, open it again by finding it in the Extensions. 
9. Optional: Press the 'Add ...' button to add this site to the list of Manga Sites so it will automatically color images on this site without having to open the settings.
10. Press 'Colorize!'

Hopefully it runs and the uncolored images you see automatically turn into colored images. It can take a minute and you may want to open the developer console to see messages about progress or problems.

This frontend was made following Apple's instructions for converting an extension for another browser into one for Safari:
https://developer.apple.com/documentation/safariservices/safari_web_extensions/converting_a_web_extension_for_safari

To create this extension the following command was run in the top repository folder (Note: you should not need to do this!):
xcrun safari-web-extension-converter --project-location Frontend-Safari --app-name MangaStreamingColorizer --bundle-identifier net.vatavia.mangaStreamingColorizer --swift --copy-resources Frontend-Chrome-AnySite
