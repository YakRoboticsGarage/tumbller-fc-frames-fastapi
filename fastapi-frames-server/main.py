from fastapi import FastAPI, Request, HTTPException, Depends, BackgroundTasks
from fastapi.responses import RedirectResponse, HTMLResponse, FileResponse
from contextlib import asynccontextmanager
from datetime import datetime  
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
import asyncio
from pathlib import Path
import urllib.parse
import uvicorn
import logging
from logging.handlers import RotatingFileHandler
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
import time
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import uuid
import glob
from PIL import Image, ImageDraw, ImageFont
import io

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Base directory and configuration
BASE_DIR = Path(__file__).resolve().parent
logger.debug(f"BASE_DIR: {BASE_DIR}")


from pathlib import Path

env_path = BASE_DIR / '.env'
load_dotenv(dotenv_path=env_path)

# Configuration
TUMBLLER_CAMERA_URLS = {
    "A": "http://roverA-cam.local/getImage",  # Update with actual camera URLs
    "B": "http://roverB-cam.local/getImage"   # Update with actual camera URLs
}

# Configuration
BASE_URL = "https://ngrok-ip.ngrok-free.app"
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

# Create logs directory if it doesn't exist
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# Set up logging configuration
def setup_logging(debug_mode: bool = False):
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Set up the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)

    # Clear any existing handlers
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    logger.addHandler(console_handler)

    # File handler for debug logs
    if debug_mode:
        debug_file_handler = RotatingFileHandler(
            LOGS_DIR / 'debug.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        debug_file_handler.setFormatter(formatter)
        debug_file_handler.setLevel(logging.DEBUG)
        logger.addHandler(debug_file_handler)

    # File handler for errors (always active)
    error_file_handler = RotatingFileHandler(
        LOGS_DIR / 'error.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_file_handler.setFormatter(formatter)
    error_file_handler.setLevel(logging.ERROR)
    logger.addHandler(error_file_handler)

    return logger

# Initialize logging with debug flag
DEBUG_MODE = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')
logger = setup_logging(debug_mode=DEBUG_MODE)

logger.debug(f"BASE_DIR: {BASE_DIR}")
logger.debug(f"Debug mode: {DEBUG_MODE}")

# Add function to get latest image for a rover
def get_latest_rover_image(rover_id: str) -> str:
    """Get the most recent image file for given rover ID"""
    pattern = str(Path(BASE_DIR, "static", f"image{rover_id}-*.jpg"))
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getctime)


def clean_old_images(rover_id: str, keep_latest: int = 5):
    """Clean old images, keeping only the specified number of most recent ones"""
    pattern = str(Path(BASE_DIR, "static", f"image{rover_id}-*.jpg"))
    files = glob.glob(pattern)
    if len(files) > keep_latest:
        # Sort files by creation time, oldest first
        sorted_files = sorted(files, key=os.path.getctime)
        # Remove all but the latest n files
        for file in sorted_files[:-keep_latest]:
            try:
                os.remove(file)
                logger.info(f"Cleaned up old image: {file}")
            except Exception as e:
                logger.error(f"Error cleaning up file {file}: {e}")


async def take_picture(rover_id: str) -> bool:
    """Take a picture from the specified rover's camera and add time left text"""
    try:
        camera_url = TUMBLLER_CAMERA_URLS[rover_id]
        async with httpx.AsyncClient() as client:
            response = await client.get(camera_url)
            response.raise_for_status()
            
            # Convert response content to image
            image_bytes = io.BytesIO(response.content)
            img = Image.open(image_bytes)
            
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
                
            # Create drawing object
            draw = ImageDraw.Draw(img)
            
            # Get time left and log it
            time_left = rover_controls[rover_id].get_time_left()
            text = f"Time left: {time_left}"
            logger.info(f"Adding text to image: {text}")
            
            # Try common Linux font paths
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"
            ]
            
            font = None
            for font_path in font_paths:
                try:
                    font = ImageFont.truetype(font_path, size=60)
                    logger.info(f"Successfully loaded font from: {font_path}")
                    break
                except IOError as e:
                    logger.warning(f"Could not load font from {font_path}: {e}")
                    continue
            
            if font is None:
                logger.warning("No TrueType font found, using default")
                font = ImageFont.load_default()
            
            # Get text size
            text_box = draw.textbbox((0, 0), text, font=font)
            text_width = text_box[2] - text_box[0]
            text_height = text_box[3] - text_box[1]
            
            # Position text in top right with larger padding
            padding = 20
            x = img.width - text_width - padding
            y = padding
            
            logger.info(f"Text dimensions: {text_width}x{text_height}")
            logger.info(f"Text position: ({x}, {y})")
            
            # Draw black background rectangle for better visibility
            background_padding = 10
            draw.rectangle([
                (x - background_padding, y - background_padding),
                (x + text_width + background_padding, y + text_height + background_padding)
            ], fill='black')
            
            # Draw text multiple times for thicker appearance
            for offset in [(2,2), (-2,-2), (2,-2), (-2,2)]:
                draw.text((x + offset[0], y + offset[1]), text, font=font, fill='black')
            
            # Draw main text
            draw.text((x, y), text, font=font, fill='yellow')
            
            # Generate new UUID for the image
            image_uuid = str(uuid.uuid4())
            image_path = Path(BASE_DIR, "static", f"image{rover_id}-{image_uuid}.jpg")
            image_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save as JPEG with high quality
            img.save(image_path, 'JPEG', quality=95)
            logger.info(f"Saved image with text at: {image_path}")
            
            # Clean up old images
            clean_old_images(rover_id)
            
            logger.info(f"Took picture for Rover {rover_id} at {datetime.now()} with UUID {image_uuid}")
            return True
            
    except Exception as e:
        logger.error(f"Error taking picture for Rover {rover_id}: {e}")
        logger.exception("Full exception details:")
        return False


def get_image_url(base_url: str, rover_id: str) -> str:
    """Get URL for the latest image of the specified rover"""
    latest_image = get_latest_rover_image(rover_id)
    if latest_image:
        # Extract just the filename from the full path
        image_filename = os.path.basename(latest_image)
        return f"{base_url}/static/{image_filename}"
    else:
        # Fallback to default image
        return f"{base_url}/static/tumbllerImage.jpg"
    

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup: Take initial pictures
    logger.info("Starting up: Taking initial pictures")
    for rover_id in ["A", "B"]:
        success = await take_picture(rover_id)
        if not success:
            logger.error(f"Failed to take initial picture for Rover {rover_id}")
            # Copy default image if available
            default_image = Path(BASE_DIR, "static", "tumbllerImage.jpg")
            if default_image.exists():
                target_image = Path(BASE_DIR, "static", f"image{rover_id}.jpg")
                target_image.write_bytes(default_image.read_bytes())
    
    yield  # Runtime: FastAPI runs here
    
    # Shutdown: Nothing specific needed for cleanup
    logger.info("Shutting down")

# Initialize FastAPI with lifespan
app = FastAPI(lifespan=lifespan)

# app = FastAPI()

# Mount static files and templates
app.mount("/static", StaticFiles(directory=Path(BASE_DIR, 'static')), name="static")
templates = Jinja2Templates(directory=Path(BASE_DIR, 'templates'))
logger.debug(f"Templates directory: {Path(BASE_DIR, 'templates')}")

# Add datetime filter for templates
def datetime_filter(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

templates.env.filters["datetime"] = datetime_filter


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
        "fc_frame_image": f"{BASE_URL}/static/tumbllerImage.jpg",  # Add slash after BASE_URL
        "base_url": f"{BASE_URL}/",  # Add slash after BASE_URL for button targets
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
            "fc_frame_image": f"/static/tumbllerImage.jpg",
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
    try:
        body = await request.body()
        logger.debug(f"Raw request body: {body}")
        payload = await request.json()
        logger.info(f"Received callback payload: {payload}")

        frame_data = payload.get("untrustedData", {})
        transaction_id = frame_data.get("transactionId")
        user = frame_data.get("fid")

        if transaction_id and user:
            new_transaction = Transaction(
                transaction_id=transaction_id,
                user=str(user),
                rover_id=rover_id,
                timestamp=time.time()
            )
            db.add(new_transaction)
            db.commit()

            if rover_controls[rover_id].is_available():
                rover_controls[rover_id].start_session(transaction_id, str(user))
                # Take initial picture when session starts
                await take_picture(rover_id)
                return templates.TemplateResponse("control_mode.html", {
                    "request": request,
                    "fc_frame_image": get_image_url(BASE_URL, rover_id),
                    "base_url": f"{BASE_URL}/",
                    "rover_id": rover_id,
                    "time_left": rover_controls[rover_id].get_time_left()
                })
            else:
                return templates.TemplateResponse("waiting.html", {
                    "request": request,
                    "fc_frame_image": get_image_url(BASE_URL, rover_id),
                    "base_url": f"{BASE_URL}/",
                    "rover_id": rover_id,
                    "time_left": rover_controls[rover_id].get_time_left()
                })
        else:
            return templates.TemplateResponse("payment_failed.html", {
                "request": request,
                "fc_frame_image": f"{BASE_URL}/static/tumbllerImage.jpg",
                "base_url": f"{BASE_URL}/"
            })
            
    except Exception as e:
        logger.error(f"Error processing callback: {str(e)}")
        return templates.TemplateResponse("payment_failed.html", {
            "request": request,
            "fc_frame_image": f"{BASE_URL}/static/tumbllerImage.jpg",
            "base_url": f"{BASE_URL}/"
        })


#control mode endpoints

@app.post("/{rover_id}/control/{mode}")
async def control_mode(rover_id: str, mode: str, request: Request):
    """Handle specific control mode (fb or lr)"""
    if not _validate_session(rover_id):
        return await root_handler(request)
    
    template_name = "fb_control.html" if mode == "fb" else "lr_control.html"
    return templates.TemplateResponse(template_name, {
        "request": request,
        "fc_frame_image": get_image_url(BASE_URL, rover_id),
        "base_url": f"{BASE_URL}/",
        "rover_id": rover_id,
        "time_left": rover_controls[rover_id].get_time_left()
    })



@app.post("/{rover_id}/pic")
async def take_rover_picture(rover_id: str, request: Request):
    """
    Take new picture from rover's camera
    Returns to the same frame user was on with new picture
    """
    if not _validate_session(rover_id):
        return await root_handler(request)
    
    success = await take_picture(rover_id)
    
    # Get the referer URL to determine which frame to return to
    referer = request.headers.get("referer", "")
    
    # Default to control_mode if can't determine frame
    template_name = "control_mode.html"
    
    # Determine which frame to return to based on the referer URL
    if "control/fb" in referer:
        template_name = "fb_control.html"
    elif "control/lr" in referer:
        template_name = "lr_control.html"
    
    # Get the URL for the newly taken picture
    image_url = get_image_url(BASE_URL, rover_id)
    
    return templates.TemplateResponse(template_name, {
        "request": request,
        "fc_frame_image": image_url,
        "base_url": f"{BASE_URL}/",  # Make sure there's a trailing slash
        "rover_id": rover_id,
        "time_left": rover_controls[rover_id].get_time_left()
    })



# Movement and Picture Commands
@app.post("/{rover_id}/move/{direction}")
async def move_rover(rover_id: str, direction: str, request: Request):
    if not _validate_session(rover_id):
        return await root_handler(request)

    command_map = {
        "forward": "forward",
        "backward": "back", 
        "left": "left",
        "right": "right",
        "stop": "stop"
    }
    
    command = command_map.get(direction)
    if not command:
        raise HTTPException(status_code=400, detail="Invalid direction")

    success, message = await send_tumbller_command(rover_id, command)
    
    if direction == "stop":
        return templates.TemplateResponse("control_mode.html", {
            "request": request,
            "fc_frame_image": get_image_url(BASE_URL, rover_id),
            "base_url": f"{BASE_URL}/",
            "rover_id": rover_id,
            "time_left": rover_controls[rover_id].get_time_left(),
            "previous_command": "stop"
        })
    else:
        mode = "fb" if direction in ["forward", "backward"] else "lr"
        return templates.TemplateResponse(f"{mode}_control.html", {
            "request": request,
            "fc_frame_image": get_image_url(BASE_URL, rover_id),
            "base_url": f"{BASE_URL}/",
            "rover_id": rover_id,
            "time_left": rover_controls[rover_id].get_time_left()
        })
    

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
    

# Utility Endpoints
@app.get("/transactions")
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
            "fc_frame_image": f"/static/tumbllerImage.jpg",
            "base_url": BASE_URL,
            "rover_id": rover_id,
            "time_left": rover_controls[rover_id].get_time_left()
        })
    elif mode == "lr":
        return templates.TemplateResponse("lr_control.html", {
            "request": request,
            "fc_frame_image": f"/static/tumbllerImage.jpg",
            "base_url": BASE_URL,
            "rover_id": rover_id,
            "time_left": rover_controls[rover_id].get_time_left()
        })
    else:
        return templates.TemplateResponse("control_mode.html", {
            "request": request,
            "fc_frame_image": f"/static/tumbllerImage.jpg",
            "base_url": BASE_URL,
            "rover_id": rover_id,
            "time_left": rover_controls[rover_id].get_time_left()
        })
    

@app.get("/static/image/{rover_id}")
async def get_image(rover_id: str, request: Request):
    """Serve image with UUID parameter to prevent caching"""
    image_path = Path(BASE_DIR, "static", f"image{rover_id}.jpg")
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(image_path)


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