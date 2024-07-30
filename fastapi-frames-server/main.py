from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import httpx
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI()

# Mount the static directory to serve images
app.mount("/static",
          StaticFiles(directory=Path(BASE_DIR, 'static')),
          name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Simple OG Tags Example</title>
        <!-- Open Graph meta tags -->
        <meta property="og:title" content="Simple OG Tags Example">
        <meta property="og:image" content="https://i.imgur.com/WVi3q3d.jpeg" >

        <!-- Farcaster frame meta tags -->
        <meta property="fc:frame" content="vNext" />
        <meta property="fc:frame:image" content="https://i.imgur.com/WVi3q3d.jpeg" >
        
        <meta property="fc:frame:button:1" content="Forward">
        <meta property="fc:frame:button:1:action" content="post">
        <meta property="fc:frame:button:1:target" content=" http://353a-85-76-103-9.ngrok-free.app/forward">
        
        <meta property="fc:frame:button:2" content="Back">
        <meta property="fc:frame:button:2:action" content="post">
        <meta property="fc:frame:button:2:target" content=" http://353a-85-76-103-9.ngrok-free.app/back">

        <meta property="fc:frame:button:3" content="Stop">
        <meta property="fc:frame:button:3:action" content="post">
        <meta property="fc:frame:button:3:target" content=" http://353a-85-76-103-9.ngrok-free.app/stop">

    </head>
    <body>
        <h1>Tumbller Farcaster Frame Server</h1>
        <p>This will run commands on Tumbller</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


# endpoint /motor/forward to send GET request to ip address of ESP32
@app.post("/forward")
async def forward1():
    url = "http://tumbller/motor/forward"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Simple OG Tags Example</title>
        <!-- Open Graph meta tags -->
        <meta property="og:title" content="Simple OG Tags Example">
        <!-- meta property="og:image" content="https://i.imgur.com/LH739Tc.png" -->

        <!-- Farcaster frame meta tags -->
        <meta property="fc:frame" content="vNext" />
        <meta property="fc:frame:image" content="https://i.imgur.com/LH739Tc.png">

        <meta property="fc:frame:button:1" content="Forward">
        <meta property="fc:frame:button:1:action" content="post">
        <meta property="fc:frame:button:1:target" content=" http://353a-85-76-103-9.ngrok-free.app/forward">
        
        <meta property="fc:frame:button:2" content="Back">
        <meta property="fc:frame:button:2:action" content="post">
        <meta property="fc:frame:button:2:target" content=" http://353a-85-76-103-9.ngrok-free.app/back">

        <meta property="fc:frame:button:3" content="Stop">
        <meta property="fc:frame:button:3:action" content="post">
        <meta property="fc:frame:button:3:target" content=" http://353a-85-76-103-9.ngrok-free.app/stop">

    </head>
    <body>
        <h1>Tumbller Farcaster Frame Server</h1>
        <p>This will run commands on Tumbller</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# endpoint /motor/back to send GET request to ip address of ESP32
@app.post("/back")
async def back1():
    url = "http://tumbller/motor/back"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Simple OG Tags Example</title>
        <!-- Open Graph meta tags -->
        <meta property="og:title" content="Simple OG Tags Example">
        <!-- meta property="og:image" content="https://i.imgur.com/xjRvaTK.png" -->

        <!-- Farcaster frame meta tags -->
        <meta property="fc:frame" content="vNext" />
        <meta property="fc:frame:image" content="https://i.imgur.com/xjRvaTK.png">

        <meta property="fc:frame:button:1" content="Forward">
        <meta property="fc:frame:button:1:action" content="post">
        <meta property="fc:frame:button:1:target" content=" http://353a-85-76-103-9.ngrok-free.app/forward">
        
        <meta property="fc:frame:button:2" content="Back">
        <meta property="fc:frame:button:2:action" content="post">
        <meta property="fc:frame:button:2:target" content=" http://353a-85-76-103-9.ngrok-free.app /back">

        <meta property="fc:frame:button:3" content="Stop">
        <meta property="fc:frame:button:3:action" content="post">
        <meta property="fc:frame:button:3:target" content=" http://353a-85-76-103-9.ngrok-free.app/stop">

    </head>
    <body>
        <h1>Tumbller Farcaster Frame Server</h1>
        <p>This will run commands on Tumbller</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# endpoint /motor/stop to send GET request to ip address of ESP32
@app.post("/stop")
async def stop1():
    url = "http://tumbller/motor/stop"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Simple OG Tags Example</title>
        <!-- Open Graph meta tags -->
        <meta property="og:title" content="Simple OG Tags Example">
        <!-- meta property="og:image" content="https://i.imgur.com/WVi3q3d.jpeg" -->

        <!-- Farcaster frame meta tags -->
        <meta property="fc:frame" content="vNext" />
        <meta property="fc:frame:image" content="https://i.imgur.com/WVi3q3d.jpeg">
        
        <meta property="fc:frame:button:1" content="Forward">
        <meta property="fc:frame:button:1:action" content="post">
        <meta property="fc:frame:button:1:target" content=" http://353a-85-76-103-9.ngrok-free.app/forward">
        
        <meta property="fc:frame:button:2" content="Back">
        <meta property="fc:frame:button:2:action" content="post">
        <meta property="fc:frame:button:2:target" content=" http://353a-85-76-103-9.ngrok-free.app/back">

        <meta property="fc:frame:button:3" content="Stop">
        <meta property="fc:frame:button:3:action" content="post">
        <meta property="fc:frame:button:3:target" content=" http://353a-85-76-103-9.ngrok-free.app/stop">

    </head>
    <body>
        <h1>Tumbller Farcaster Frame Server</h1>
        <p>This will run commands on Tumbller</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# endpoint /sensor/ht to send GET request to ip address of ESP32
@app.post("/sensor/ht")
async def sensor_ht():
    url = "http://tumbller/sensor/ht"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    return HTMLResponse(content=response.text)