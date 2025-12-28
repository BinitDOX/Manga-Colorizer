# run_worker.py

import os
import sys
import time
import logging
import threading
import requests
import argparse
import subprocess
import re

sys.path.append(os.getcwd())

from app_ai.main import app
from pyngrok import ngrok, conf
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# --- Basic Setup ---
logger = logging.getLogger("KaggleWorker")
logger.setLevel("INFO")

# --- Global Shutdown Signal ---
shutdown_event = threading.Event()

# --- Security Dependency for Shutdown Endpoint ---
bearer_scheme = HTTPBearer()


def verify_janitor_secret(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    """A FastAPI dependency to protect the /stop endpoint."""
    try:
        janitor_secret = os.environ["JANITOR_SECRET"]
        if credentials.scheme != "Bearer" or credentials.credentials != janitor_secret:
            logger.warning("Unauthorized attempt to access /stop endpoint.")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid janitor token")
        return True
    except Exception as e:
        logger.error(f"Could not verify janitor secret: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not verify secret")


# --- Fleet Manager Communication ---
def notify_fleet_manager(worker_id, status: str, url: str = None, error: str = None):
    """Securely notifies the Fleet Manager of the worker's status."""
    try:
        manager_url = os.environ["FLEET_MANAGER_URL"]
        secret = os.environ["REGISTRATION_SECRET"]

        payload = {"worker_id": worker_id, "status": status, "public_url": url, "error_message": error}
        headers = {"Authorization": f"Bearer {secret}", "User-Agent": f"Hydra-Kaggle-Worker/{worker_id}"}

        logger.info(f"Notifying Fleet Manager: status={status}, worker_id={worker_id}")
        response = requests.post(manager_url, json=payload, headers=headers, timeout=15)

        if response.status_code not in [200, 202]:
            logger.error(f"Failed to notify Fleet Manager. Status: {response.status_code}, Body: {response.text}")
        else:
            logger.info("Successfully notified Fleet Manager.")
    except KeyError as e:
        logger.critical(f"FATAL: Missing required environment variable: {e}. Cannot call home.")
        raise
    except Exception as e:
        logger.error(f"An exception occurred while notifying Fleet Manager: {e}", exc_info=True)


@app.post("/stop", dependencies=[Depends(verify_janitor_secret)])
async def stop_worker():
    logger.warning("Received shutdown signal from Janitor. Terminating worker...")
    shutdown_event.set()
    return {"message": "Shutdown signal received. Worker is terminating."}


# ---------------- Tunnel helpers ----------------

def start_ngrok(port: int, auth_token: str):
    conf.get_default().auth_token = auth_token
    public_url = ngrok.connect(port).public_url
    logger.info(f"Ngrok tunnel established at: {public_url}")

    def cleanup():
        try:
            ngrok.kill()
            logger.info("Ngrok tunnel stopped")
        except Exception as e:
            logger.warning(f"Ngrok cleanup skipped: {e}")

    return public_url, cleanup


def start_zrok(port: int, auth_token: str):

    try:
        proc_enable = subprocess.Popen(
            ["zrok", "enable", auth_token],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        for line in proc_enable.stdout:
            print(line, end="")
        proc_enable.wait()
        logger.info("zrok enabled")
    except Exception as e:
        logger.warning(f"zrok enable failed or already enabled: {e}")

    proc = subprocess.Popen(
        ["zrok", "share", "public", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    public_url = None
    url_re = re.compile(r"https://[^\s│]+")
    for line in proc.stdout:
        print(line, end="")
        match = url_re.search(line)
        if match:
            public_url = match.group(0).strip()
            break

    if not public_url:
        proc.terminate()
        raise RuntimeError("Failed to obtain zrok public URL")

    logger.info(f"Zrok tunnel established at: {public_url}")

    def cleanup():
        if proc.poll() is None:
            proc.terminate()
            logger.info("Zrok tunnel stopped")

    return public_url, cleanup



# --- Main Worker Logic ---
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tunnel",
        choices=["ngrok", "zrok"],
        default=os.environ.get("TUNNEL", "ngrok"),
        help="Tunnel provider (default: ngrok)"
    )
    args = parser.parse_args()

    tunnel_cleanup = None

    try:
        worker_id = int(os.environ["WORKER_ID"])
        auth_token = os.environ["AUTH_TOKEN"]
        logger.info(f"Secrets loaded from environment for worker_id: {worker_id}")
    except Exception as e:
        logger.critical(f"FATAL: Could not retrieve required configuration from environment: {e}. Terminating.")
        sys.exit(1)

    try:
        notify_fleet_manager(worker_id, 'booting')

        def run_fastapi():
            logger.info("Starting FastAPI server using uvicorn...")
            import uvicorn
            uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)

        api_thread = threading.Thread(target=run_fastapi, daemon=True)
        api_thread.start()

        logger.info("Waiting for models to load...")
        time.sleep(30)
        logger.info("FastAPI server thread started and models should be loaded.")

        # --- Tunnel selection ---
        if args.tunnel == "ngrok":
            public_url, tunnel_cleanup = start_ngrok(8000, auth_token)
        else:
            public_url, tunnel_cleanup = start_zrok(8000, auth_token)

        notify_fleet_manager(worker_id, 'active', url=public_url)

        logger.info("Worker is fully operational. Entering keep-alive loop.")
        while not shutdown_event.is_set():
            time.sleep(5)

        logger.warning("Shutdown event is set. Exiting keep-alive loop and terminating.")

    except Exception as e:
        logger.error(f"A critical error occurred in the main loop: {e}", exc_info=True)
        notify_fleet_manager(worker_id, 'failed', error=str(e))
    finally:
        logger.info("Shutting down worker.")
        if tunnel_cleanup:
            tunnel_cleanup()
        notify_fleet_manager(worker_id, 'stopping')
        logger.info("Script finished.")


if __name__ == "__main__":
    main()
