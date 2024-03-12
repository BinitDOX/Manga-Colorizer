# Manga-Colorizer
Introducing Manga-Colorizer, a tool that brings your mangas to life!


## Demo Video - PC:
https://user-images.githubusercontent.com/93908298/227715568-52e4c510-aff5-40f7-aa5d-4954c3416253.mp4

## Demo Video - Android:
https://user-images.githubusercontent.com/93908298/227804094-d7552b52-71cf-4d08-b030-ae081c57cc88.mp4


## Limitations:
- Works with https://ww5.manganelo.tv and https://chapmanganelo.com/.
- Compatible with <b>Firefox, Chrome, Firefox Nightly Android and Kiwi</b> (Basically Android Chrome with extension) browser.
- <s>Backend server is not hosted, so self local hosting is required. (Python required) (Only works in LAN)</s>


## Server Usage Instructions (KAGGLE HOSTING, NEW)(21/11/23): 
1. Make a <a href="https://www.kaggle.com/">kaggle</a> account and verify using phone to get ~30hrs of weekly GPU.
2. Make an <a href="https://ngrok.com/">ngrok</a> account and get your auth token from <a href="https://dashboard.ngrok.com/get-started/your-authtoken">here</a>
3. Go to <a href="https://www.kaggle.com/code/yeeandres/manga-colorizer-server">this</a> notebook and click 'Copy & Edit'
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
    

## Server Usage Instructions (SELF HOSTING, OLD): 
0. If you are following this method, please refer <a href="https://ngrok.com/](https://github.com/BinitDOX/Manga-Colorizer/issues/6">here</a> for known issues.
1. Clone or download the repository as .zip and extract. 
2. Download the <a href="https://drive.google.com/file/d/1qmxUEKADkEM4iYLp1fpPLLKnfZ6tcF-t/view?usp=sharing" rel="nofollow">Generator</a> weights and move it to <code>Backend/networks</code> folder.
3. If you do not have a GPU, edit app.py and set <code>self.gpu = False</code> (~Line 75)
4. In the Backend folder, open a command prompt, and run:
   - <code>pip install -r requirements.txt</code> For installing necessary modules.
   - <code>python app.py</code> For running the Flask server.
   - Enter PEM Pass Phrase: <code>Ireckon</code>
   - Backend should be running on localhost (https://127.0.0.1:5000) and Private IP (https://x.x.x.x:5000)
  
  
## Client Usage Instructions - PC - Firefox: 
0. Open the server URL (Ex. https://x.x.x.x:5000)
   - It will show some certificate warning, as it is self-signed.
   - Click 'Advanced' and click 'Accept the risk and continue'. ('Proceed, unsafe' for Chrome)
   - You should now see 'Manga Colorizer is Up and Running!'
1. Install https://addons.mozilla.org/en-US/firefox/addon/manga-colorizer/ extension on firefox.
2. Open any manga on https://ww5.manganelo.tv/ or https://chapmanganelo.com/
3. Right click the extension and select 'Always allow on...' (No need for Chrome)
4. Click the extension and turn on cached panels, also input the server URL in the 'API Base-URL'.
5. Click the 'Colorize' button, that should appear next to 'Next chapter'.
6. Wait (~20sec-1min, depends on Network and GPU) and Enjoy.


## Client Usage Instructions - PC - Chrome: 
0. Open the server URL (Ex. https://x.x.x.x:5000)
   - It will show some certificate warning, as it is self-signed.
   - Click 'Advanced' and click 'Proceed to x.x.x.x (unsafe)'.
   - You should now see 'Manga Colorizer is Up and Running!'
1. Goto <code>chrome://extensions/</code> webpage, turn on developer mode, and click 'Load Unpacked'.
2. Navigate to and select Frontend-Chrome folder.
3. Open any manga on https://ww5.manganelo.tv/ or https://chapmanganelo.com/
4. Click the extension and turn on cached panels, also input the server URL in the 'API Base-URL'.
5. Click the 'Colorize' button, that should appear next to 'Next chapter'.
6. Wait (~20sec-1min, depends on Network and GPU) and Enjoy.


## Client Usage Instructions - Android - Firefox Nightly:
1. Install Firefox Nightly browser on android from google playstore.
2. Open settings, scroll down and select 'About Firefox Nightly'.
3. Keep Tapping on Firefox logo, until the Debug menu is enabled.
4. Go back and select Custom Add-on collection
5. Input <code>17834213</code> in User-ID and <code>XODalG-MC</code> in Collection name.
6. Follow Step-0 of 'Client Usage Instructions - PC - Firefox'
7. Open any manga on https://ww5.manganelo.tv/ or https://chapmanganelo.com/
8. Tap settings menu (3 dots), select Add-ons, select the colorizer extension.
9. Then turn on cached panels, also input the server URL in the 'API Base-URL', and go back.
10. Click the 'Colorize' button, that should appear next to 'Next chapter'.
11. Wait (~20sec-1min, depends on Network and GPU) and Enjoy.
12. Unfortunately, only Step-8 has to be repeated at every chapter because of permission issues, so Kiwi Browser is recommended.


## Client Usage Instructions - Android - Kiwi (Chrome \w extension):
1. Move the 'Frontend-Chrome.crx' file in the Frontend-Chrome folder to your Android device.
2. Install Kiwi browser on android from google playstore.
3. Open browser settings menu (3 dots), select 'Extensions', then select '+(from .zip / crx)' and browse for the 'Frontend-Chrome.crx' file.
4. Toggle on the extension and accept the permissions.
5. Follow Step-0 of 'Client Usage Instructions - PC - Chrome'
6. Open any manga on https://ww5.manganelo.tv/ or https://chapmanganelo.com/
7. Tap settings menu, scroll down, select the colorizer extension.
8. Then turn on cached panels, also input the server URL in the 'API Base-URL', and go back.
9. Click the 'Colorize' button, that should appear next to 'Next chapter'.
10. Wait (~20sec-1min, depends on Network and GPU) and Enjoy.


## Pro Tips:
- Install the uBlock Origin extension.
- Before reading a chapter, navigate to the next chapter and initiate the colorization. Then, navigate back to the current chapter immediately. The next time you visit and colorize the next chapter, it will take only 1 to 5 seconds, given that the panel caching is turned on. This means you can merge the colorization time into your reading time.


## Troubleshoot:
- If there is an error, make sure you can always access the server URL from Client device. (Refer Step-0)
- If there is an error, make sure you entered correct server URL with port number, in 'API Base-URL' of extension settings.
- If the 'Colorize' button does not appear, click the extension once.


## Credits:
- https://github.com/qweasdd/manga-colorization-v2 for AI Model and Weights.
