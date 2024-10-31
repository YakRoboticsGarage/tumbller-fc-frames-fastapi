from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
from pathlib import Path
import urllib.parse
import uvicorn
import logging
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
import time
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Base directory and configuration
BASE_DIR = Path(__file__).resolve().parent
logger.debug(f"BASE_DIR: {BASE_DIR}")


from pathlib import Path

env_path = BASE_DIR / '.env'
load_dotenv(dotenv_path=env_path)

app = FastAPI()

# Mount static files and templates
app.mount("/static", StaticFiles(directory=Path(BASE_DIR, 'static')), name="static")
templates = Jinja2Templates(directory=Path(BASE_DIR, 'templates'))
logger.debug(f"Templates directory: {Path(BASE_DIR, 'templates')}")

# Add datetime filter for templates
def datetime_filter(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

templates.env.filters["datetime"] = datetime_filter

# Configuration
BASE_URL = "https://01e7-85-76-119-212.ngrok-free.app"
TUMBLLER_BASE_URLS = {
    "A": "http://tumbller-a.local",
    "B": "http://tumbller-b.local"
}
PAYCASTER_API_URL = "https://app.paycaster.co/api/customs/"

# Load environment variables
load_dotenv()
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY not found in .env file")

TOKEN = "usdc"
AMOUNT = 1

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, index=True)
    user = Column(String)
    rover_id = Column(String)
    timestamp = Column(Float)

Base.metadata.create_all(bind=engine)

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class RoverControl:
    def __init__(self):
        self.transaction_id: Optional[str] = None
        self.start_time: float = 0
        self.user: Optional[str] = None
        self.session_duration: int = 300  # 5 minutes

    def is_available(self) -> bool:
        if not self.transaction_id:
            return True
        return time.time() - self.start_time > self.session_duration

    def start_session(self, transaction_id: str, user: str):
        self.transaction_id = transaction_id
        self.start_time = time.time()
        self.user = user

    def get_time_left(self) -> str:
        if not self.transaction_id:
            return "00:00"
        elapsed = time.time() - self.start_time
        remaining = self.session_duration - elapsed
        remaining = max(0, int(remaining))
        minutes = remaining // 60
        seconds = remaining % 60
        return f"{minutes:02d}:{seconds:02d}"

    def clear_session(self):
        self.transaction_id = None
        self.start_time = 0
        self.user = None

# Initialize rover controls
rover_controls: Dict[str, RoverControl] = {
    "A": RoverControl(),
    "B": RoverControl()
}

# Routes
@app.get("/")
async def root_get(request: Request):
    """Handle GET requests to root endpoint"""
    return await root_handler(request)

@app.post("/")
async def root_post(request: Request):
    """Handle POST requests to root endpoint"""
    return await root_handler(request)

async def root_handler(request: Request):
    """Common handler for both GET and POST requests"""
    return templates.TemplateResponse("rover_selection.html", {
        "request": request,
        "fc_frame_image": "https://i.imgur.com/WVi3q3d.jpeg",
        "base_url": BASE_URL,
        "rover_a_available": rover_controls["A"].is_available(),
        "rover_b_available": rover_controls["B"].is_available()
    })

@app.post("/select_rover/{rover_id}")
async def select_rover(rover_id: str, request: Request):
    """Handle rover selection"""
    if rover_id not in rover_controls:
        raise HTTPException(status_code=400, detail="Invalid rover selection")

    if rover_controls[rover_id].is_available():
        # Pass the request object to pay function
        return await pay(rover_id, request)
    else:
        time_left = rover_controls[rover_id].get_time_left()
        return templates.TemplateResponse("waiting.html", {
            "request": request,
            "fc_frame_image": "https://i.imgur.com/WVi3q3d.jpeg",
            "base_url": BASE_URL,
            "rover_id": rover_id,
            "time_left": time_left
        })

@app.post("/pay/{rover_id}")
async def pay(rover_id: str, request: Request):
    """Payment initiation endpoint"""
    sender = "anurajenp"
    receiver = "infinity-rover"

    query_params = {
        "key": API_KEY,
        "sender": sender,
        "amount": AMOUNT,
        "token": TOKEN,
        "receiver": receiver
    }

    callback_url = f"{BASE_URL}/callback/{rover_id}"
    encoded_callback = urllib.parse.quote(callback_url)
    query_params["callback"] = encoded_callback

    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.get(PAYCASTER_API_URL, params=query_params)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            og_title = soup.find('meta', property='og:title')['content'] if soup.find('meta', property='og:title') else None
            fc_frame_image = soup.find('meta', attrs={'name': 'fc:frame:image'})['content'] if soup.find('meta', attrs={'name': 'fc:frame:image'}) else None
            fc_frame_button = soup.find('meta', attrs={'name': 'fc:frame:button:1'})['content'] if soup.find('meta', attrs={'name': 'fc:frame:button:1'}) else None
            fc_frame_button_action = soup.find('meta', attrs={'name': 'fc:frame:button:1:action'})['content'] if soup.find('meta', attrs={'name': 'fc:frame:button:1:action'}) else None
            fc_frame_button_target = soup.find('meta', attrs={'name': 'fc:frame:button:1:target'})['content'] if soup.find('meta', attrs={'name': 'fc:frame:button:1:target'}) else None
            
            fc_frame_post_url = soup.find('meta', attrs={'name': 'fc:frame:post_url'})['content'] if soup.find('meta', attrs={'name': 'fc:frame:post_url'}) else None
            if fc_frame_post_url:
                decoded_url = urllib.parse.unquote(fc_frame_post_url)
                fc_frame_post_url = urllib.parse.quote(decoded_url, safe=':/')
            
            return templates.TemplateResponse("payment_frame.html", {
                "request": request,
                "og_title": og_title,
                "fc_frame_image": fc_frame_image,
                "fc_frame_post_url": fc_frame_post_url,
                "fc_frame_button": fc_frame_button,
                "fc_frame_button_action": fc_frame_button_action,
                "fc_frame_button_target": fc_frame_button_target
            })
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e}")
            raise HTTPException(status_code=e.response.status_code, detail="Transaction failed")
        

@app.post("/callback/{rover_id}")
async def transaction_callback(rover_id: str, request: Request, db: Session = Depends(get_db)):
    """Payment callback handler"""
    try:
        # Log raw request data for debugging
        body = await request.body()
        logger.debug(f"Raw request body: {body}")
        # Get the raw JSON data from the request
        payload = await request.json()
        logger.info(f"Received callback payload: {payload}")

        # Extract data from the Farcaster Frame callback format
        frame_data = payload.get("untrustedData", {})
        transaction_id = frame_data.get("transactionId")
        user = frame_data.get("fid")  # Farcaster user ID

        if transaction_id and user:
            # Store transaction in database
            new_transaction = Transaction(
                transaction_id=transaction_id,
                user=str(user),  # Convert to string in case it's a number
                rover_id=rover_id,
                timestamp=time.time()
            )
            db.add(new_transaction)
            db.commit()

            if rover_controls[rover_id].is_available():
                rover_controls[rover_id].start_session(transaction_id, str(user))
                logger.info(f"Payment confirmed for Rover {rover_id}. Transaction ID: {transaction_id}, User: {user}")
                return templates.TemplateResponse("control_mode.html", {
                    "request": request,
                    "fc_frame_image": "https://i.imgur.com/WVi3q3d.jpeg",
                    "base_url": BASE_URL,
                    "rover_id": rover_id,
                    "time_left": rover_controls[rover_id].get_time_left()
                })
            else:
                logger.warning(f"Rover {rover_id} is not available. User: {user}")
                return templates.TemplateResponse("waiting.html", {
                    "request": request,
                    "fc_frame_image": "https://i.imgur.com/WVi3q3d.jpeg",
                    "base_url": BASE_URL,
                    "rover_id": rover_id,
                    "time_left": rover_controls[rover_id].get_time_left()
                })
        else:
            logger.warning("Payment not confirmed as successful. Missing transaction ID or user.")
            return templates.TemplateResponse("payment_failed.html", {
                "request": request,
                "fc_frame_image": "https://i.imgur.com/WVi3q3d.jpeg",
                "base_url": BASE_URL
            })
            
    except Exception as e:
        logger.error(f"Error processing callback: {str(e)}")
        return templates.TemplateResponse("payment_failed.html", {
            "request": request,
            "fc_frame_image": "https://i.imgur.com/WVi3q3d.jpeg",
            "base_url": BASE_URL
        })
    

@app.post("/{rover_id}/control")
async def control_rover(rover_id: str, request: Request):
    """Main control frame"""
    if not _validate_session(rover_id):
        return await root(request)
    
    return templates.TemplateResponse("control_mode.html", {
        "request": request,
        "fc_frame_image": "https://i.imgur.com/WVi3q3d.jpeg",
        "base_url": BASE_URL,
        "rover_id": rover_id,
        "time_left": rover_controls[rover_id].get_time_left()
    })


@app.post("/{rover_id}/control/{mode}")
async def control_mode(rover_id: str, mode: str, request: Request):
    """Handle specific control mode (fb or lr)"""
    if not _validate_session(rover_id):
        return await root(request)
    
    template_name = "fb_control.html" if mode == "fb" else "lr_control.html"
    return templates.TemplateResponse(template_name, {
        "request": request,
        "fc_frame_image": "https://i.imgur.com/WVi3q3d.jpeg",
        "base_url": BASE_URL,
        "rover_id": rover_id,
        "time_left": rover_controls[rover_id].get_time_left()
    })


@app.post("/{rover_id}/move/{direction}")
async def move_rover(rover_id: str, direction: str, request: Request):
    """Handle movement commands"""
    logger.info(f"Received movement command: {direction} for rover {rover_id}")
    
    if not _validate_session(rover_id):
        logger.warning(f"Invalid session for rover {rover_id}")
        return await root(request)

    # Map directions to commands
    command_map = {
        "forward": "forward",
        "backward": "back",
        "left": "left",
        "right": "right",
        "stop": "stop"
    }

    command = command_map.get(direction)
    if not command:
        logger.error(f"Invalid direction received: {direction}")
        raise HTTPException(status_code=400, detail="Invalid direction")

    # Send command to the rover
    logger.info(f"Sending command {command} to rover {rover_id}")
    success, message = await send_tumbller_command(rover_id, command)
    logger.info(f"Command result: success={success}, message={message}")
    
    if direction == "stop":
        # Double-check that stop command was sent
        logger.info("Stop command requested, confirming stop was sent")
        return templates.TemplateResponse("control_mode.html", {
            "request": request,
            "fc_frame_image": "https://i.imgur.com/WVi3q3d.jpeg",
            "base_url": BASE_URL,
            "rover_id": rover_id,
            "time_left": rover_controls[rover_id].get_time_left(),
            "previous_command": "stop"
        })
    else:
        # For other commands, return to appropriate control mode
        mode = "fb" if direction in ["forward", "backward"] else "lr"
        return await control_mode(rover_id, mode, request)
    

async def send_tumbller_command(rover_id: str, command: str):
    """Send command to Tumbller device"""
    url = f"{TUMBLLER_BASE_URLS[rover_id]}/motor/{command}"
    logger.info(f"Attempting to send command to URL: {url}")
    
    try:
        async with httpx.AsyncClient() as client:
            logger.info(f"Sending {command} command to {url}")
            response = await client.get(url, timeout=10.0)
            logger.info(f"Sent {command} command to Rover {rover_id}. Response: {response.status_code}")
            logger.info(f"Response content: {response.text}")
        response.raise_for_status()
        return True, "Command sent successfully"
    except httpx.TimeoutException:
        logger.error(f"Timeout while sending {command} command to Tumbller {rover_id}")
        return False, f"Tumbller {rover_id} not responding"
    except httpx.HTTPStatusError as exc:
        logger.error(f"HTTP error {exc.response.status_code} while sending {command} command to Tumbller {rover_id}")
        return False, f"Tumbller {rover_id} returned error: {exc.response.status_code}"
    except httpx.RequestError as exc:
        logger.error(f"An error occurred while sending {command} command to Tumbller {rover_id}: {exc}")
        return False, f"Unable to communicate with Tumbller {rover_id}"
    

@app.get("/transactions", response_class=HTMLResponse)
async def get_transactions(request: Request, db: Session = Depends(get_db)):
    """View transaction history"""
    transactions = db.query(Transaction).all()
    return templates.TemplateResponse("transactions.html", {
        "request": request,
        "transactions": transactions
    })


@app.post("/{rover_id}/update_time/{mode}")
async def update_time(rover_id: str, mode: str, request: Request):
    """Handle time update requests and return to the same frame"""
    if not _validate_session(rover_id):
        return await root(request)
    
    if mode == "fb":
        return templates.TemplateResponse("fb_control.html", {
            "request": request,
            "fc_frame_image": "https://i.imgur.com/WVi3q3d.jpeg",
            "base_url": BASE_URL,
            "rover_id": rover_id,
            "time_left": rover_controls[rover_id].get_time_left()
        })
    elif mode == "lr":
        return templates.TemplateResponse("lr_control.html", {
            "request": request,
            "fc_frame_image": "https://i.imgur.com/WVi3q3d.jpeg",
            "base_url": BASE_URL,
            "rover_id": rover_id,
            "time_left": rover_controls[rover_id].get_time_left()
        })
    else:
        return templates.TemplateResponse("control_mode.html", {
            "request": request,
            "fc_frame_image": "https://i.imgur.com/WVi3q3d.jpeg",
            "base_url": BASE_URL,
            "rover_id": rover_id,
            "time_left": rover_controls[rover_id].get_time_left()
        })

def _validate_session(rover_id: str) -> bool:
    """Validate if the session is still active"""
    if rover_id not in rover_controls:
        return False
    
    rover = rover_controls[rover_id]
    if rover.is_available():
        rover.clear_session()
        return False
    
    return True

if __name__ == "__main__":
    logger.debug(f"SSL key file: {Path(BASE_DIR, 'key.pem')}")
    logger.debug(f"SSL cert file: {Path(BASE_DIR, 'cert.pem')}")
    uvicorn.run(app, host="0.0.0.0", port=8000, ssl_keyfile=Path(BASE_DIR, "key.pem"), ssl_certfile=Path(BASE_DIR, "cert.pem"))