import time
import requests
import os
import sys
import logging
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor

sys.path.append(os.getcwd())

# Import Service Logic
from app_ai.service.processing_service import process_image, ProcessingOptions

# --- Setup ---
logging.basicConfig(level="INFO", format="%(asctime)s | PULL-WORKER | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# --- Configuration ---
try:
    API_URL = os.environ["FLEET_MANAGER_URL"]
    SECRET = os.environ["REGISTRATION_SECRET"]
    WORKER_ID = int(os.environ["WORKER_ID"])
    MAX_THREADS = int(os.environ.get("MAX_THREADS", 3))
except KeyError as e:
    logger.critical(f"FATAL: Missing env var: {e}")
    sys.exit(1)

shutdown_event = threading.Event()


# --- Helper: Fleet Notification ---
def notify_fleet_manager(status: str, error: str = None):
    try:
        payload = {
            "worker_id": WORKER_ID,
            "status": status,
            "public_url": None,
            "error_message": error
        }
        headers = {
            "Authorization": f"Bearer {SECRET}",
            "User-Agent": f"Hydra-Pull-Worker/{WORKER_ID}"
        }

        register_url = API_URL

        response = requests.post(register_url, json=payload, headers=headers, timeout=15)

        if response.status_code not in [200, 202]:
            logger.error(f"Failed to notify fleet ({status}): {response.status_code} - {response.text}")
        else:
            logger.info(f"Reported status: {status}")

    except Exception as e:
        logger.error(f"Error notifying fleet: {e}")


# --- Job Processor ---
def process_single_job(job_data: dict):
    job_id = job_data["id"]
    headers = {"Authorization": f"Bearer {SECRET}"}
    rid = f"JOB-{job_id[:8]}"

    logger.info(f"Thread-{threading.get_ident()}: Starting job {job_id}")

    try:
        # 1. Download
        img_resp = requests.get(job_data["input_url"], timeout=45)
        img_resp.raise_for_status()

        # 2. Process
        result_bytes, width, height = asyncio.run(
            process_image(img_resp.content, ProcessingOptions(**job_data["options"]), rid)
        )

        # 3. Upload
        upload_resp = requests.put(
            job_data["upload_url"],
            data=result_bytes,
            headers={"Content-Type": "image/png"},
            timeout=90
        )
        upload_resp.raise_for_status()

        # 4. Complete
        requests.post(f"{API_URL}/complete", json={
            "job_id": job_id, "worker_id": WORKER_ID, "status": "success",
            "meta": {"width": width, "height": height,
                     "upscale_applied": job_data["options"].get("apply_upscale", False)}
        }, headers=headers, timeout=15)

        logger.info(f"Job {job_id} DONE.")

    except Exception as e:
        logger.error(f"Job {job_id} FAILED: {e}")
        requests.post(f"{API_URL}/complete", json={
            "job_id": job_id, "worker_id": WORKER_ID, "status": "failed", "error": str(e)
        }, headers=headers, timeout=15)


def main():
    headers = {"Authorization": f"Bearer {SECRET}"}
    error_message = None

    # 1. Report BOOTING
    notify_fleet_manager("booting")

    # 2. Load Models
    logger.info("Warming up AI models...")
    try:
        from app_ai.service.processing_service import ai_models
        _ = ai_models
    except Exception as e:
        logger.error(f"Model load failed: {e}")
        notify_fleet_manager("failed", error=f"Model Init Error: {e}")
        return

    time.sleep(1)

    # 3. Report ACTIVE
    notify_fleet_manager("active")
    logger.info(f"Pull Worker {WORKER_ID} ACTIVE with {MAX_THREADS} threads. Polling...")

    consecutive_errors = 0
    MAX_RETRIES = 5

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        while not shutdown_event.is_set():
            try:
                resp = requests.post(
                    f"{API_URL}/poll",
                    json={"worker_id": WORKER_ID},
                    headers=headers,
                    timeout=30
                )

                # Reset error counter on success
                consecutive_errors = 0

                if resp.status_code != 200:
                    logger.warning(f"Poll non-200: {resp.status_code}")
                    time.sleep(5)
                    continue

                data = resp.json()
                command = data.get("command")

                if command == "shutdown":
                    logger.warning("Shutdown command received.")
                    clean_exit = True
                    shutdown_event.set()
                    break

                if command == "process" and data.get("job"):
                    executor.submit(process_single_job, data["job"])

                # Small breathe
                time.sleep(3)

            except requests.exceptions.RequestException as e:
                consecutive_errors += 1
                wait_time = min(consecutive_errors * 5, 60)  # Backoff
                logger.warning(f"Poll Network Error ({consecutive_errors}/{MAX_RETRIES}): {e}. Sleeping {wait_time}s.")

                if consecutive_errors > MAX_RETRIES:
                    error_message = "Max network retries exceeded"
                    logger.error("Max network retries exceeded. Assuming fatal network loss.")
                    shutdown_event.set()
                    break
                time.sleep(wait_time)

            except Exception as e:
                logger.critical(f"Unexpected Loop Error: {e}", exc_info=True)
                consecutive_errors += 1
                if consecutive_errors > 3:
                    error_message = f"Unexpected Error: {e}"
                    logger.critical("Too many critical errors. Exiting.")
                    shutdown_event.set()
                    break
                time.sleep(10)

    if not error_message:
        logger.info("Reporting CLEAN SHUTDOWN to fleet manager.")
        notify_fleet_manager("stopping")
    else:
        logger.error("Reporting UNEXPECTED FAILURE to fleet manager.")
        notify_fleet_manager("failed", error=error_message)

    logger.info("Worker process finished.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Worker crashed: {e}", exc_info=True)
        # Try one last gasp to report failure
        notify_fleet_manager("failed", error=str(e))
