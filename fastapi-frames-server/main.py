from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
from pathlib import Path
import urllib.parse
import uvicorn
import logging
from bs4 import BeautifulSoup

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
logger.debug(f"BASE_DIR: {BASE_DIR}")

app = FastAPI()

# Mount the static directory to serve images
app.mount("/static", StaticFiles(directory=Path(BASE_DIR, 'static')), name="static")

# Set up Jinja2 templates with the correct path
templates = Jinja2Templates(directory=Path(BASE_DIR, 'templates'))
logger.debug(f"Templates directory: {Path(BASE_DIR, 'templates')}")

# Define the base URL for all buttons
BASE_URL = "https://6fb7-85-76-113-250.ngrok-free.app"

# Define the base URL for the Tumbller device
TUMBLLER_BASE_URL = "http://tumbller.local"

# Paycaster API base URL
PAYCASTER_API_URL = "https://app.paycaster.co/api/customs/"  # Ensure this is HTTPS

# Define your API key and default transaction values
API_KEY = "actual-key"  # Replace with your actual API key
TOKEN = "usdc"  # ERC20 token to be used
AMOUNT = 1  # Fixed amount of 1 USDC

# Keep track of whether the payment was successful
payment_successful = False

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """
    Displays the root frame. If payment was successful, it shows forward, back, stop buttons.
    Otherwise, it only shows the pay button.
    """
    global payment_successful

    if payment_successful:
        # Display the forward, back, and stop buttons after payment success
        return templates.TemplateResponse("control_buttons.html", {
            "request": request,
            "fc_frame_image": "https://i.imgur.com/WVi3q3d.jpeg",
            "page_title": "Control Tumbller",
            "base_url": BASE_URL
        })
    else:
        # Initially display only the Pay button
        return templates.TemplateResponse("pay_button.html", {
            "request": request,
            "fc_frame_image": "https://i.imgur.com/WVi3q3d.jpeg",
            "page_title": "Pay to Unlock Controls",
            "base_url": BASE_URL
        })

@app.post("/")
async def root_post(request: Request):
    """Handle POST requests to the root, which occur after payment redirection."""
    return RedirectResponse(url="/", status_code=303)  # Use 303 to change POST to GET

@app.post("/pay")
async def pay():
    """
    Endpoint to handle ERC20 token payments via Paycaster.
    The sender is 'anurajenp' and the receiver is 'infinity-rover'.
    :return: Farcaster frame HTML for payment initiation.
    """
    sender = "anurajenp"
    receiver = "infinity-rover"

    # Construct the query parameters for the Paycaster API
    query_params = {
        "key": API_KEY,
        "sender": sender,
        "amount": AMOUNT,
        "token": TOKEN,
        "receiver": receiver
    }

    # You can also add a callback if needed (currently optional)
    callback_url = f"{BASE_URL}/callback"
    encoded_callback = urllib.parse.quote(callback_url)
    query_params["callback"] = encoded_callback

    # Send the GET request to initiate the transaction
    async with httpx.AsyncClient(follow_redirects=True) as client:  # Enable following redirects
        try:
            response = await client.get(PAYCASTER_API_URL, params=query_params)
            response.raise_for_status()  # Raise exception for HTTP errors
            
            # Log the raw HTML response
            logger.info("Paycaster API Response (HTML):")
            logger.info(response.text)
            
            # Parse the HTML response
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract relevant metadata
            og_title = soup.find('meta', property='og:title')['content'] if soup.find('meta', property='og:title') else None
            fc_frame_image = soup.find('meta', attrs={'name': 'fc:frame:image'})['content'] if soup.find('meta', attrs={'name': 'fc:frame:image'}) else None
            fc_frame_button = soup.find('meta', attrs={'name': 'fc:frame:button:1'})['content'] if soup.find('meta', attrs={'name': 'fc:frame:button:1'}) else None
            fc_frame_button_action = soup.find('meta', attrs={'name': 'fc:frame:button:1:action'})['content'] if soup.find('meta', attrs={'name': 'fc:frame:button:1:action'}) else None
            fc_frame_button_target = soup.find('meta', attrs={'name': 'fc:frame:button:1:target'})['content'] if soup.find('meta', attrs={'name': 'fc:frame:button:1:target'}) else None
            
            # Properly handle the post_url
            fc_frame_post_url = soup.find('meta', attrs={'name': 'fc:frame:post_url'})['content'] if soup.find('meta', attrs={'name': 'fc:frame:post_url'}) else None
            if fc_frame_post_url:
                # First, decode the URL completely
                decoded_url = urllib.parse.unquote(fc_frame_post_url)
                # Then, encode it properly for use in HTML
                fc_frame_post_url = urllib.parse.quote(decoded_url, safe=':/')
            
            logger.info(f"Extracted metadata: Title: {og_title}, Image: {fc_frame_image}, Button: {fc_frame_button}, Action: {fc_frame_button_action}, Target: {fc_frame_button_target}, Post URL: {fc_frame_post_url}")
            
            # Log headers
            logger.info("Response Headers:")
            for name, value in response.headers.items():
                logger.info(f"{name}: {value}")
            
            # Log status code
            logger.info(f"Status Code: {response.status_code}")
            
            # Construct the modified HTML response
            modified_html = f"""
            <!DOCTYPE html>
            <html>
              <head>
                <title>{og_title}</title>
                <meta property="og:title" content="{og_title}" />
                <meta property="og:image" content="{fc_frame_image}" />
                <meta name="fc:frame" content="vNext" />
                <meta name="fc:frame:post_url" content="{fc_frame_post_url}" />
                <meta name="fc:frame:image" content="{fc_frame_image}" />
                <meta name="fc:frame:image:aspect_ratio" content="1.91:1" />
                <meta name="fc:frame:button:1" content="{fc_frame_button}" />
                <meta name="fc:frame:button:1:action" content="{fc_frame_button_action}" />
                <meta name="fc:frame:button:1:target" content="{fc_frame_button_target}" />
              </head>
              <body/>
            </html>
            """
            
            # Return the modified Farcaster frame HTML
            return HTMLResponse(content=modified_html, status_code=200)
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e}")
            raise HTTPException(status_code=e.response.status_code, detail="Transaction failed")


@app.post("/callback")
async def transaction_callback(request: Request):
    """
    Callback endpoint to handle transaction success.
    """
    global payment_successful
    
    # Parse the request payload
    payload = await request.json()
    logger.info(f"Received callback payload: {payload}")

    # Check if the payment was successful
    # You'll need to determine the exact structure of the payload
    if payload.get('status') == 'success':  # Adjust this condition based on the actual payload
        payment_successful = True
        logger.info("Payment confirmed as successful")
    else:
        logger.warning("Payment not confirmed as successful")

    # Return a new Farcaster frame indicating the result
    if payment_successful:
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
          <head>
            <title>Payment Successful</title>
            <meta property="og:title" content="Payment Successful" />
            <meta property="og:image" content="https://i.imgur.com/WVi3q3d.jpeg" />
            <meta name="fc:frame" content="vNext" />
            <meta name="fc:frame:image" content="https://i.imgur.com/WVi3q3d.jpeg" />
            <meta name="fc:frame:button:1" content="Control Tumbller" />
            <meta name="fc:frame:button:1:action" content="post" />
            <meta name="fc:frame:button:1:target" content="{BASE_URL}/" />
          </head>
          <body/>
        </html>
        """)
    else:
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
          <head>
            <title>Payment Failed</title>
            <meta property="og:title" content="Payment Failed" />
            <meta property="og:image" content="https://i.imgur.com/WVi3q3d.jpeg" />
            <meta name="fc:frame" content="vNext" />
            <meta name="fc:frame:image" content="https://i.imgur.com/WVi3q3d.jpeg" />
            <meta name="fc:frame:button:1" content="Try Again" />
            <meta name="fc:frame:button:1:action" content="post" />
            <meta name="fc:frame:button:1:target" content="{BASE_URL}/pay" />
          </head>
          <body/>
        </html>
        """)

@app.post("/forward")
async def forward1(request: Request):
    url = f"{TUMBLLER_BASE_URL}/motor/forward"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    return templates.TemplateResponse("control_buttons.html", {
        "request": request,
        "fc_frame_image": "https://i.imgur.com/LH739Tc.png",
        "page_title": "Forward Command Sent to Tumbller",
        "base_url": BASE_URL
    })

@app.post("/back")
async def back1(request: Request):
    url = f"{TUMBLLER_BASE_URL}/motor/back"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    return templates.TemplateResponse("control_buttons.html", {
        "request": request,
        "fc_frame_image": "https://i.imgur.com/xjRvaTK.png",
        "page_title": "Back Command Sent to Tumbller",
        "base_url": BASE_URL
    })

@app.post("/stop")
async def stop1(request: Request):
    url = f"{TUMBLLER_BASE_URL}/motor/stop"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    return templates.TemplateResponse("control_buttons.html", {
        "request": request,
        "fc_frame_image": "https://i.imgur.com/WVi3q3d.jpeg",
        "page_title": "Stop Command Sent to Tumbller",
        "base_url": BASE_URL
    })

if __name__ == "__main__":
    logger.debug(f"SSL key file: {Path(BASE_DIR, 'key.pem')}")
    logger.debug(f"SSL cert file: {Path(BASE_DIR, 'cert.pem')}")
    uvicorn.run(app, host="0.0.0.0", port=8000, ssl_keyfile=Path(BASE_DIR, "key.pem"), ssl_certfile=Path(BASE_DIR, "cert.pem"))