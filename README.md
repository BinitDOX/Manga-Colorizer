# Manga-Colorizer
Introducing Manga-Colorizer, a tool that brings your mangas to life!


## Demo Video - PC:
[![DEMO VIDEO](https://github.com/user-attachments/assets/6737808a-8ad1-4dd3-b642-34c8020ebd98)](https://youtu.be/aD0jUb-vPOo)


## Demo Video - Android:
[DEMO VIDEO](https://drive.google.com/file/d/15Rw4aykO_7Gedj6sR50gAiIiaTjHLr6o/view?usp=sharing)

## New Features:
- [x] Now works seamlessly on any website.
- [x] Blazingly fast image colorization on the fly.
- [x] Intelligent and dynamic colorization.
- [x] Super-resolution upscaling for enhanced image quality.
- [x] Additional settings for more customization options.
- [x] Organized caching into a dedicated folder for reuse.
- [x] Options to display original, colorized version, or both.
- [x] Force colorization. 

## Notes:
- Old legacy project can be found <a href="https://github.com/BinitDOX/Manga-Colorizer/tree/main">here</a>.
- Follow any one of the server and one of client usage instructions.



## Server Usage Instructions | Local Hosting: 
0. Local hosting is recommended if you have access to a cuda GPU.
1. Clone or download this repository as .zip and extract. 
2. Download the <a href="https://drive.google.com/file/d/1qmxUEKADkEM4iYLp1fpPLLKnfZ6tcF-t/view?usp=sharing" rel="nofollow">Generator</a> weights and move it to <code>Backend/networks</code> folder.
3. Install <a href="https://www.python.org/downloads/">python</a> and setup <a href="https://pytorch.org/get-started/locally/">pytorch</a> if not already done.
4. In the Backend folder, open a command prompt, and run:
   - For installing necessary modules: <code>pip install -r requirements.txt</code>
   - For starting the server: <code>python app-stream.py</code>
   - Backend should be running on localhost (https://127.0.0.1:5000) and Private IP (https://x.x.x.x:5000)
5. Next, follow any of the 'Client Usage Instructions'.


## Server Usage Instructions | Online Hosting: 
0. Online hosting is recommended if you don't have access to a cuda GPU or you do not want to keep your system/server on, while reading on a mobile.
1. Make a <a href="https://www.kaggle.com/">kaggle</a> account and verify using phone to get ~30hrs of weekly GPU.
2. Make an <a href="https://ngrok.com/">ngrok</a> account and get your auth token from <a href="https://dashboard.ngrok.com/get-started/your-authtoken">here</a>
3. Go to <a href="https://www.kaggle.com/code/yeeandres/manga-colorizer-server-stream">this</a> notebook and click 'Copy & Edit'
4. Set the accelerator as GPU P100 under notebook options if not already selected.
5. Replace the your_ngrok_auth_token in '!ngrok config add-authtoken your_ngrok_auth_token' in the code with the auth-token in Step 3.
6. Next choose 'Run All' from the menu to run the notebook.
7. In a few minutes you should see some output from the last running line (!ngrok http 5000) with some urls.
8. Click on the one which looks something like https://314-1342-142-43.ngrok-free.app.
9. Alternatively, visit <a href="https://dashboard.ngrok.com/tunnels/agents">here</a> to get the running sessions.
10. On the tab that opens, click visit site.
11. You should see 'Manga Colorizer is Up and Running!'
12. Now you can follow any of the 'Client Usage Instructions' below, including step 0, but with this API URL
13. You may also now click 'Save Version' on the notebook, then 'Save and Run All (Compile)' to keep the notebook running (it will re-run) even after you turn off your system.
14. After a few minutes, visit <a href="https://dashboard.ngrok.com/tunnels/agents">here</a> to get the running sessions and get the new API URL and use that for the client.


## Client Usage Instructions | PC | Firefox: 
0. Open the server URL:
   - Use localhost (local-hosting) (https://127.0.0.1:5000) or,
   - Private IP (local-hosting) (Ex. https://x.x.x.x:5000) or,
   - The ngrokURL (online-hosting) (Ex. https://314-1342-142-43.ngrok-free.app).
      - It will show some certificate warning, as it is self-signed.
      - Click 'Advanced' and click 'Accept the risk and continue'.
      - You should now see 'Manga Colorizer is Up and Running!'
1. Open the firefox <a href="about:debugging#/runtime/this-firefox">debugging</a> page and click 'Load Temporary Add-on'.
2. Navigate to the Frontend-Firefox directory and choose manifest.json.
3. If the extension loads correctly, you will see it's settings page.
4. Paste the server URL, in the extension's 'API URL' field and press 'Test'.
5. If you see 'Manga Colorizer is Up and Running!', then its working!
6. Close all these necessary tabs now and open a black-and-white manga.
7. Open the Extensions menu (looks like a puzzle piece).
8. Then right-click 'Manga Colorizer' and select 'Always allow on ...' also 'Pin to Toolbar'
9. Click on the 'Manga Colorizer' extension to open its settings as a popup.
10. Click the 'Colorize' button, that should appear next to 'Next chapter'.
11. Press the 'Add ...' button to add the site to the list of Manga Sites, so it automatically colors images from now on.
12. Press 'Colorize!' and enjoy!.
13. These steps have to be repeated everytime firefox is started.


## Client Usage Instructions | PC | Chrome/Brave/Any-Chromium: 
0. Open the server URL:
   - Use localhost (local-hosting) (https://127.0.0.1:5000) or,
   - Private IP (local-hosting) (Ex. https://x.x.x.x:5000) or,
   - The ngrokURL (online-hosting) (Ex. https://314-1342-142-43.ngrok-free.app).
     - It will show some certificate warning, as it is self-signed.
     - Click 'Advanced' and click 'Proceed to x.x.x.x (unsafe)'.
     - You should now see 'Manga Colorizer is Up and Running!'
1. Goto <code>chrome://extensions/</code> webpage, turn on developer mode, and click 'Load Unpacked'.
2. Navigate to and select Frontend-Chrome folder. Manga Colorizer settings should open in a new tab.
3. Paste the server URL, in the extension's 'API URL' field and press 'Test'.
4. If you see 'Manga Colorizer is Up and Running!', then its working!
5. Close all these necessary tabs now and open a black-and-white manga.
6. Open the Extensions menu (looks like a puzzle piece) and click the pin next to 'Manga Colorizer'.
7. Click on the 'Manga Colorizer' extension to open its settings as a popup.
8. Press the 'Add ...' button to add the site to the list of Manga Sites, so it automatically colors images from now on.
9. Press 'Colorize!' and enjoy!.


## Client Usage Instructions | Android | Firefox Nightly:
1. First, goto 'Frontend-Firefox' folder and zip all the files.
2. Select all the files, then right-click, Send to, Compressed (zip) folder.
3. Rename this zip file to 'Frontend-Firefox.zip' and move it to your android device.
4. Install Firefox Nightly browser on android from google playstore.
5. Open settings, scroll down and select 'About Firefox Nightly'.
6. Keep Tapping on Firefox logo, until the Debug menu is enabled.
7. Go back and select Secret settings, and choose to install Add-on from file.
8. Browse for the 'Frontend-Firefox.zip' file that you uploaded to you device.
9. Follow Step-0 of 'Client Usage Instructions | PC | Firefox' **but use either Private IP or ngrokURL**.
10. Open any black-and-white mange page.
11. Tap settings menu (3 dots), select Add-ons, select the colorizer extension.
12. Input the server URL in the 'API URL' field.
13. Add the manga website in the list.
14. Press 'Colorize!' and enjoy!.
15. Unfortunately, only Step-8 has to be repeated at every chapter because of permission issues, so Kiwi Browser is recommended.


## Client Usage Instructions | Android | Kiwi/Any-Chromium (\w extension):
1. First on PC Chrome, go to <a href="chrome://extensions/">extension</a> settings and click 'Pack extension' on top-left.
2. Click browse, then navigate and choose the Frontend-Chrome folder and click 'Pack extension'.
3. This will create a 'Frontend-Chrome.crx' file. Move this file to your android device.
4. Install [Kiwi browser](https://drive.google.com/file/d/1Zsvfy2zchtqXx4lEgX544JKWfX2kD_wp/view?usp=sharing) on android from google playstore.
5. Open browser settings menu (3 dots), select 'Extensions', then select '+(from .zip / crx)' and browse for the 'Frontend-Chrome.crx' file.
6. Toggle on the extension and accept the permissions.
7. Follow Step-0 of 'Client Usage Instructions - PC - Chrome' **but use either Private IP or ngrokURL**.
8. Open any black-and-white mange page.
9. Tap settings menu (3 dots), scroll down, select the 'Manga-Colorizer' extension.
10. Input the server URL in the 'API Base-URL'.
11. Add the manga website in the list.
12. Press 'Colorize!' and enjoy!.


## Credits:
- https://github.com/qweasdd/manga-colorization-v2 by <a href="https://github.com/qweasdd">qweasdd</a> for AI Model and Weights.
- https://github.com/xiaogdgenuine/Manga-Colorization-FJ by <a href="https://github.com/xiaogdgenuine">xiaogdgenuine</a> for Upscaler integration.
- https://github.com/xinntao/Real-ESRGAN by <a href="https://github.com/xinntao">xinntao</a> for the Upscaler (ESR-GAN).
- https://github.com/vatavian/Manga-Colorizer fork by <a href="https://github.com/vatavian">vatavian</a> for any-site, on-the-fly, intelligent colorization, and multiple other direct contributions.
- And, <a href="https://github.com/iG8R">iG8R</a> for testing and opening great issues that lead to this updated version.
