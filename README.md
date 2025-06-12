# FastAPI farcaster frames server for tumbller rover


## Setup

* To run the robots first thing to do is the wifi setup. This computer running this server and both the ESP32s need to be on the same network or VPN. The following instructions will set it up for the devices on the same network. 
* Clone the follwoing three repos in a folder
  * https://github.com/YakRoboticsGarage/tumbller-fc-frames-fastapi
  * https://github.com/YakRoboticsGarage/tumbller-esp32s3
  * https://github.com/YakRoboticsGarage/tumbller-esp-cam
  
* Both tumbller-esp32s3 and tumbller-esp-cam have WIFI_SSID and WIFI_PASSWORD hardcoded. Find them and replace with your own wifi credentials
* Now we need to know the IPs of each of the ESPs and the computer this server will run on.
* The ESP-CAM will spit out the IP on the serial port when connected to a serial terminal. You should see something like this on the serial terminal when you press the __RESET__ button (the right button when the camera is facing you). The ESP-CAM will fast blink in red color when it is trying to connect to WiFi and will blink in White when connected. 
  * Note down the ESP-CAM-IP

```

WiFi connected
Camera Ready! Use 'http://ESP-CAM-IP/stream' to connect
HTTP server started
Camera sensor verified and ready
Signal strength (RSSI): -45 dBm
TX Power: 78 dBm

```

* For tumbller-esp32s3 we will need to enable the serial output in the code to find the IP
  * Open the tumbller-esp32s3 in a VSCode window with PlatformIO extension installed
  * On line 10 in the main.cpp file there is a macro called `// #define USE_SERIAL`. Comment/Uncomment to enable/disable serial output. For now enable it. Flash the ESP32-S3 with this firmware. 
  * On the serial terminal note down the IP of ESP32-S3
  * Now disable the serial output by commenting the macro `// #define USE_SERIAL` and flash the firmware again so that serial output is disabled
* Now create a file called .env in the `farcaster-frames-server` folder and paste this template content in that file

```
API_KEY=PAYBOT-KEY
DEBUG=False
ENVIRONMENT=development
CAMERA_URL_A=http://ESP32-S3-IP/getImage
CAMERA_URL_B=http://ESP32-S3-IP/getImage
BASE_URL=https://ngrok-ip.ngrok-free.app
TUMBLLER_URL_A=http://ESP-CAM-IP
TUMBLLER_URL_B=http://ESP-CAM-IP
MNEMONIC_ENV_VAR=FARCASTER-KEY
```
## Running the frame server 

* Replace each of the variable with the correct value from `.env.template` and put them into a `.env` file.
* Get the association file from the Manifest tool: https://farcaster.xyz/~/developers/mini-apps/manifest
* ngrok  url is got after starting ngrok with 
  * `ngrok http --url=<domain name> 8080`
* Now setup the fastapi python virtual env with this command
  * `python -m venv venv`
  * `pip install -r requirements.txt`
  * `source venv/bin/activate`
* Now you should see a (venv) prefix in your command prompt
* If you have no Tumbller around, you can use the fake rover
  * From the root of this repository (in a different shell): `PYTHONPATH=. python dev/fake_rover.py`
  * The fake rover by default listens on localhost at 5001
* Start the MiniApp server by going into farcaster-frames-server folder
  * `cd farcaster-frames-server`
* Start the frames server with command
  * `uvicorn main:app --host 0.0.0.0 --port 8080 --reload`
* Open a browser logged in with farcaster and then go to this url to test the frame
  * `https://farcaster.xyz/~/developers/mini-apps/embed` (you can also use the Manifest Tool; you can also try directly in a browser, but there will be no Farcaster integration there (e.g. payment will not work)).
  * Paste the ngrok url into it and play with the robot
