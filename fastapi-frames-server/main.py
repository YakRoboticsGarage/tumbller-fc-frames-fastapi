from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI()

# Mount the static directory to serve images
app.mount("/static", StaticFiles(directory=Path(BASE_DIR, 'static')), name="static")

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Define the base URL for all buttons. Get this from what ngrok generates
BASE_URL = "http://b2d8-85-76-113-250.ngrok-free.app"

# Define the base URL for the Tumbller device. Check this from the serial monitor output of the Tumbller device
TUMBLLER_BASE_URL = "http://tumbbler"

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("fcframe.html", {
        "request": request,
        "fc_frame_image": "https://i.imgur.com/WVi3q3d.jpeg", # TODO: Take image from the static directory
        "page_title": "Tumbller Farcaster Frame Server",
        "base_url": BASE_URL
    })


@app.post("/forward")
async def forward1(request: Request):
    url = f"{TUMBLLER_BASE_URL}/motor/forward"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    return templates.TemplateResponse("fcframe.html", {
        "request": request,
        "fc_frame_image": "https://i.imgur.com/LH739Tc.png", # TODO: Take image from the static directory
        "page_title": "Forward Command Sent to Tumbller",
        "action": "forward",
        "base_url": BASE_URL
    })


@app.post("/back")
async def back1(request: Request):
    url = f"{TUMBLLER_BASE_URL}/motor/back"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    return templates.TemplateResponse("fcframe.html", {
        "request": request,
        "fc_frame_image": "https://i.imgur.com/xjRvaTK.png", # TODO: Take image from the static directory
        "page_title": "Back Command Sent to Tumbller",
        "action": "back",
        "base_url": BASE_URL
    })


@app.post("/stop")
async def stop1(request: Request):
    url = f"{TUMBLLER_BASE_URL}/motor/stop"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    return templates.TemplateResponse("fcframe.html", {
        "request": request,
        "fc_frame_image": "https://i.imgur.com/WVi3q3d.jpeg", # TODO: Take image from the static directory
        "page_title": "Stop Command Sent to Tumbller",
        "action": "stop",
        "base_url": BASE_URL
    })
