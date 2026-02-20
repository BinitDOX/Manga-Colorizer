import time
import requests
import os
import sys
import logging
import asyncio
import threading
import random
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
    API_URL = os.environ["FLEET_MANAGER_URL"]
    SECRET = os.environ["REGISTRATION_SECRET"]
    WORKER_ID = int(os.environ["WORKER_ID"])
    MAX_THREADS = int(os.environ.get("MAX_THREADS", 3))
except KeyError as e:
    print(f"FATAL: Missing env var: {e}")
    sys.exit(1)

shutdown_event = threading.Event()

def notify_fleet_manager(status: str, error: str = None):
    """Updates the worker status in the DB via the registration endpoint."""
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

        response = requests.post(API_URL, json=payload, headers=headers, timeout=15)

        if response.status_code not in [200, 202]:
            logger.error(f"LifeCycle: Failed to notify ({status}): {response.status_code}")
        else:
            logger.info(f"LifeCycle: Reported {status.upper()}")

    except Exception as e:
        logger.error(f"LifeCycle: Error notifying fleet: {e}")

def thread_done_callback(future):
    """Reveals exceptions that happen inside threads."""
    try:
        future.result()
    except Exception as e:
        logger.critical(f"THREAD-CRASH: A processing thread died! Error: {e}", exc_info=True)

def process_single_job(job_data: dict):
    """Processes a single colorization/upscale job."""
    job_id = job_data["job_id"]
    headers = {"Authorization": f"Bearer {SECRET}"}
    rid = f"JOB-{job_id[:8]}"

    # Rename current thread for better logs
    threading.current_thread().name = f"Worker-{job_id[:4]}"
    logger.info(f"Starting job {job_id}")

    try:
        # 1. Download
        logger.info(f"Downloading image from GCS...")
        img_resp = requests.get(job_data["input_url"], timeout=45)
        img_resp.raise_for_status()

        # 2. Process AI
        logger.info(f"Executing AI Pipeline for {rid}...")
        result_bytes, width, height = asyncio.run(
            process_image(img_resp.content, ProcessingOptions(**job_data["options"]), rid)
        )

        # 3. Upload Result
        logger.info(f"Uploading result to GCS...")
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

    # --- Polling Tiers (Idle Time -> Sleep Range) ---
    SLEEP_TIERS = [
        (0.5 * 60, (1, 1)),  # < 30 sec idle -> INSTANT (Poll every 1s)
        (1 * 60, (1, 3)),   # < 1 min idle  → SUPER FAST (Burst Mode)
        (5 * 60, (4, 8)),   # 1-5 min idle  → FAST
        (10 * 60, (8, 14)),  # 5-10 min idle → MEDIUM
        (20 * 60, (14, 22)), # 10-20 min idle→ SLOW
        (float("inf"), (22, 30)) # > 20 min idle → CAPPED
    ]

    consecutive_errors = 0
    MAX_RETRIES = 5

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        last_job_time = time.monotonic()

        while not shutdown_event.is_set():
            try:
                resp = requests.post(
                    f"{API_URL}/poll",
                    json={"worker_id": WORKER_ID},
                    headers=headers,
                    timeout=30
                )

                consecutive_errors = 0 # Reset on network success

                if resp.status_code != 200:
                    logger.warning(f"Poll non-200: {resp.status_code}. Sleeping 10s.")
                    time.sleep(10)
                    continue

                data = resp.json()
                command = data.get("command")

                # Handle Shutdown
                if command == "shutdown":
                    logger.warning("Intentional SHUTDOWN command received.")
                    clean_exit = True
                    shutdown_event.set()
                    break

                # Handle Processing
                if command == "process" and data.get("job"):
                    job = data["job"]
                    logger.info(f"Dispatched Job: {job['job_id']}")
                    future = executor.submit(process_single_job, job)
                    future.add_done_callback(thread_done_callback)

                    # Reset idle timer because we just took work
                    last_job_time = time.monotonic()

                # --- Adaptive Idle Sleep Calculation ---
                now = time.monotonic()
                idle_duration = now - last_job_time
                sleep_time = 5 # default fallback

                for threshold, (low, high) in SLEEP_TIERS:
                    if idle_duration < threshold:
                        sleep_time = random.uniform(low, high)
                        break

                # Small delay before next poll based on current activity level
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
        logger.info("Reporting CLEAN SHUTDOWN to fleet manager.")
        notify_fleet_manager("stopping")
    else:
        logger.error(f"Reporting UNEXPECTED FAILURE to fleet manager: {error_message}")
        notify_fleet_manager("failed", error=error_message)

    logger.info("Worker process finished.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Top-level Crash: {e}", exc_info=True)
        notify_fleet_manager("failed", error=f"Unhandled Exception: {str(e)}")