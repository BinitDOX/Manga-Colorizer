import time
import requests
import os
import sys
import logging
import asyncio
import threading
import random
import time

from concurrent.futures import ThreadPoolExecutor

sys.path.append(os.getcwd())

# Import Service Logic
from app_ai.service.processing_service import process_image, ProcessingOptions

# --- Setup Verbose Logging ---
logging.basicConfig(
    level="INFO",
    format="%(asctime)s | %(levelname)s | [%(threadName)s] | %(message)s",
    force=True
)
logger = logging.getLogger("PullWorker")

# --- Configuration ---
try:
    # Note: In your latest setup, API_URL seems to be the specific endpoint or base
    API_URL = os.environ["FLEET_MANAGER_URL"]
    SECRET = os.environ["REGISTRATION_SECRET"]
    WORKER_ID = int(os.environ["WORKER_ID"])
    MAX_THREADS = int(os.environ.get("MAX_THREADS", 3))
except KeyError as e:
    print(f"FATAL: Missing env var: {e}")
    sys.exit(1)

shutdown_event = threading.Event()

# --- Helper: Fleet Notification ---
def notify_fleet_manager(status: str, error: str = None):
    """Updates the worker status in the DB."""
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

        # We use the provided URL directly as per your requirement
        response = requests.post(API_URL, json=payload, headers=headers, timeout=15)

        if response.status_code not in [200, 202]:
            logger.error(f"LifeCycle: Failed to notify ({status}): {response.status_code}")
        else:
            logger.info(f"LifeCycle: Reported {status.upper()}")

    except Exception as e:
        logger.error(f"LifeCycle: Error notifying fleet: {e}")

# --- Thread Failure Tracker ---
def thread_done_callback(future):
    """Reveals exceptions that happen inside threads."""
    try:
        future.result()
    except Exception as e:
        logger.critical(f"THREAD-CRASH: A processing thread died! Error: {e}", exc_info=True)

# --- Job Processor ---
def process_single_job(job_data: dict):
    job_id = job_data["id"]
    headers = {"Authorization": f"Bearer {SECRET}"}
    rid = f"JOB-{job_id[:8]}"

    # Rename current thread for better logs
    threading.current_thread().name = f"Worker-{job_id[:4]}"
    logger.info(f"Starting job {job_id}")

    try:
        # 1. Download
        logger.info(f"Downloading from GCS: {job_data['input_url'][:50]}...")
        img_resp = requests.get(job_data["input_url"], timeout=45)
        img_resp.raise_for_status()
        logger.info(f"Download complete: {len(img_resp.content)} bytes")

        # 2. Process
        logger.info(f"Executing AI Pipeline for {rid}...")
        result_bytes, width, height = asyncio.run(
            process_image(img_resp.content, ProcessingOptions(**job_data["options"]), rid)
        )
        logger.info(f"AI processing finished: {width}x{height}")

        # 3. Upload
        logger.info(f"Uploading result to: {job_data['upload_url'][:50]}...")
        upload_resp = requests.put(
            job_data["upload_url"],
            data=result_bytes,
            headers={"Content-Type": "image/png"},
            timeout=90
        )
        upload_resp.raise_for_status()

        # 4. Complete
        logger.info(f"Reporting SUCCESS for {job_id}")
        # Note: Added /complete if API_URL is the base, otherwise adjust as needed
        requests.post(f"{API_URL}/complete", json={
            "job_id": job_id, "worker_id": WORKER_ID, "status": "success",
            "meta": {"width": width, "height": height,
                     "upscale_applied": job_data["options"].get("apply_upscale", False)}
        }, headers=headers, timeout=15)

        logger.info(f"DONE: Job {job_id} finalized.")

    except Exception as e:
        logger.error(f"FAILED: Job {job_id} | Error: {e}")
        try:
            requests.post(f"{API_URL}/complete", json={
                "job_id": job_id, "worker_id": WORKER_ID, "status": "failed", "error": str(e)
            }, headers=headers, timeout=15)
        except:
            pass

def main():
    threading.current_thread().name = "Main-Loop"
    headers = {"Authorization": f"Bearer {SECRET}"}
    error_message = None
    clean_exit = False

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

    # 3. Report ACTIVE
    notify_fleet_manager("active")
    logger.info(f"Pull Worker {WORKER_ID} ACTIVE with {MAX_THREADS} threads. Polling {API_URL}...")

    consecutive_errors = 0
    MAX_RETRIES = 5

    SLEEP_TIERS = [
        (5 * 60, (4, 8)),  # < 5 min idle → fast
        (10 * 60, (8, 14)),  # 5–10 min → medium
        (20 * 60, (14, 22)),  # 10–20 min → slower
        (float("inf"), (22, 30))  # 20+ min → capped
    ]

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        last_job_time = time.monotonic()

        while not shutdown_event.is_set():
            try:
                # Assuming /poll if API_URL is the base
                resp = requests.post(
                    f"{API_URL}/poll",
                    json={"worker_id": WORKER_ID},
                    headers=headers,
                    timeout=30
                )

                consecutive_errors = 0

                if resp.status_code != 200:
                    logger.warning(f"Poll returned {resp.status_code}. Sleeping 10s.")
                    time.sleep(10)
                    continue

                data = resp.json()
                command = data.get("command")

                if command == "shutdown":
                    logger.warning("Intentional SHUTDOWN command received from backend.")
                    clean_exit = True
                    shutdown_event.set()
                    break

                if command == "process" and data.get("job"):
                    job = data["job"]
                    logger.info(f"Dispatched Job: {job['id']}")
                    future = executor.submit(process_single_job, job)
                    future.add_done_callback(thread_done_callback)

                    last_job_time = time.monotonic()

                # --- Adaptive idle sleep ---
                now = time.monotonic()
                idle_duration = now - last_job_time

                for threshold, (low, high) in SLEEP_TIERS:
                    if idle_duration < threshold:
                        sleep_time = random.uniform(low, high)
                        break

                logger.debug(
                    f"Idle {idle_duration:.0f}s → sleeping {sleep_time:.2f}s"
                )

                time.sleep(sleep_time)

            except requests.exceptions.RequestException as e:
                consecutive_errors += 1
                wait_time = min(consecutive_errors * 5, 60)
                logger.warning(f"Network Error ({consecutive_errors}/{MAX_RETRIES}): {e}. Sleeping {wait_time}s.")

                if consecutive_errors > MAX_RETRIES:
                    error_message = f"Network Loss: {str(e)}"
                    break
                time.sleep(wait_time)

            except Exception as e:
                logger.critical(f"Critical Loop Error: {e}", exc_info=True)
                consecutive_errors += 1
                if consecutive_errors > 3:
                    error_message = f"Unexpected Failure: {str(e)}"
                    break
                time.sleep(10)

    # 4. Final Cleanup Report
    if clean_exit:
        logger.info("Cleaning up for authorized exit...")
        notify_fleet_manager("stopping")
    else:
        logger.error(f"Cleaning up after error: {error_message}")
        notify_fleet_manager("failed", error=error_message)

    logger.info("Worker script terminated.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Top-level Crash: {e}", exc_info=True)
        notify_fleet_manager("failed", error=f"Unhandled Exception: {str(e)}")