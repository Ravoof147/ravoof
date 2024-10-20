from pathlib import Path
import config
from pyrogram.types import InputMediaDocument 
import pickle, os, random, string, asyncio
from utils.logger import Logger
from datetime import datetime, timezone
from utils.clients import get_client
from pyrogram import Client
from pyrogram.types import Message
from urllib.parse import unquote_plus

logger = Logger(__name__)

cache_dir = Path("./cache")
cache_dir.mkdir(parents=True, exist_ok=True)
drive_cache_path = cache_dir / "drive.data"

PROGRESS_CACHE = {}
STOP_TRANSMISSION = []

# Function to generate a random ID
def getRandomID():
    global DRIVE_DATA
    while True:
        id = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if id not in DRIVE_DATA.used_ids:
            DRIVE_DATA.used_ids.append(id)
            return id

async def progress_callback(current, total, id, client: Client, file_path):
    global PROGRESS_CACHE, STOP_TRANSMISSION

    PROGRESS_CACHE[id] = ("running", current, total)
    if id in STOP_TRANSMISSION:
        logger.info(f"Stopping transmission {id}")
        client.stop_transmission()
        try:
            os.remove(file_path)
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")

async def start_file_uploader(file_path, id, directory_path, filename, file_size):
    global PROGRESS_CACHE
    from utils.directoryHandler import DRIVE_DATA

    logger.info(f"Preparing to upload file: {file_path} | ID: {id}")

    if not Path(file_path).exists():
        logger.error(f"File does not exist: {file_path}")
        PROGRESS_CACHE[id] = ("failed", 0, 0)
        return

    if file_size > 1.5 * 1024 * 1024 * 1024:  # Set maximum file size to 1.5 GB
        client: Client = get_client(premium_required=True)
    else:
        client: Client = get_client()

    # Generate a random ID for the file description
    random_id = getRandomID()

    PROGRESS_CACHE[id] = ("running", 0, 0)

    try:
        # Attempt to upload the file
        logger.info(f"Uploading file {file_path} with ID {id}")
        message: Message = await client.send_document(
            config.STORAGE_CHANNEL,
            file_path,
            caption="Uploading...",  # Temporary caption
            progress=progress_callback,
            progress_args=(id, client, file_path),
            disable_notification=True,
        )

        # After successful upload, update the message caption with the random ID
        await client.edit_message_caption(
            chat_id=config.STORAGE_CHANNEL,
            message_id=message.id,
            caption=f"File ID: {random_id}",  # Update caption with the random ID
        )

        # Extract file size
        size = (
            message.photo
            or message.document
            or message.video
            or message.audio
            or message.sticker
        ).file_size

        filename = unquote_plus(filename)

        # Add the new file info to the drive data
        DRIVE_DATA.new_file(directory_path, filename, message.id, size)
        PROGRESS_CACHE[id] = ("completed", size, size)

        logger.info(f"Uploaded file {file_path} | ID: {random_id}")

    except Exception as e:
        logger.error(f"Failed to upload {file_path}: {e}")
        PROGRESS_CACHE[id] = ("failed", 0, 0)
        return

    finally:
        # Clean up the local file after upload
        if Path(file_path).exists():
            try:
                os.remove(file_path)
                logger.info(f"Deleted local file {file_path}")
            except Exception as e:
                logger.error(f"Error deleting file {file_path}: {e}")

# Make sure to include necessary imports and initialization for your bot and any other required components.
