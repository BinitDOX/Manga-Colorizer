# run_worker.py

import os
import sys
import time
import logging
import threading
import requests

sys.path.append(os.getcwd())

from app_ai.main import app
from pyngrok import ngrok, conf
from kaggle_secrets import UserSecretsClient
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
        secrets = UserSecretsClient()
        janitor_secret = secrets.get_secret("WORKER_JANITOR_SECRET")
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
        secrets = UserSecretsClient()
        manager_url = secrets.get_secret("FLEET_MANAGER_URL")
        secret = secrets.get_secret("WORKER_REGISTRATION_SECRET")

        payload = {
            "worker_id": worker_id,
            "status": status,
            "public_url": url,
            "error_message": error
        }
        headers = {
            "Authorization": f"Bearer {secret}"
        }

        logger.info(f"Notifying Fleet Manager: status={status}, worker_id={worker_id}")
        response = requests.post(manager_url, json=payload, headers=headers, timeout=15)

        if response.status_code not in [200, 202]:
            logger.error(f"Failed to notify Fleet Manager. Status: {response.status_code}, Body: {response.text}")
        else:
            logger.info("Successfully notified Fleet Manager.")

    except Exception as e:
        logger.error(f"An exception occurred while notifying Fleet Manager: {e}", exc_info=True)


@app.post("/stop", dependencies=[Depends(verify_janitor_secret)])
async def stop_worker():
    logger.warning("Received shutdown signal from Janitor. Terminating worker...")
    shutdown_event.set()
    return {"message": "Shutdown signal received. Worker is terminating."}


# --- Main Worker Logic ---
def main():
    try:
        secrets = UserSecretsClient()
        worker_id = int(secrets.get_secret("WORKER_ID"))
        ngrok_auth_token = secrets.get_secret("NGROK_AUTH_TOKEN")
        logger.info(f"Secrets loaded for worker_id: {worker_id}")
    except Exception as e:
        logger.fatal(f"FATAL: Could not retrieve secrets from Kaggle: {e}", exc_info=True)
        sys.exit(1)

    try:
        notify_fleet_manager(worker_id, 'BOOTING')

        def run_fastapi():
            logger.info("Starting FastAPI server using uvicorn...")
            import uvicorn
            uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)

        api_thread = threading.Thread(target=run_fastapi, daemon=True)
        api_thread.start()

        logger.info("Waiting for models to load...")
        time.sleep(30)
        logger.info("FastAPI server thread started and models should be loaded.")

        # Start ngrok tunnel
        conf.get_default().auth_token = ngrok_auth_token
        public_url = ngrok.connect(8000).public_url
        logger.info(f"Ngrok tunnel established at: {public_url}")

        notify_fleet_manager(worker_id, 'ACTIVE', url=public_url)

        logger.info("Worker is fully operational. Entering keep-alive loop.")
        while not shutdown_event.is_set():
            time.sleep(5)

        logger.warning("Shutdown event is set. Exiting keep-alive loop and terminating.")

    except Exception as e:
        logger.error(f"A critical error occurred in the main loop: {e}", exc_info=True)
        notify_fleet_manager(worker_id, 'FAILED', error=str(e))
    finally:
        logger.info("Shutting down worker.")
        ngrok.kill()
        notify_fleet_manager(worker_id, 'STOPPING')
        logger.info("Script finished.")


if __name__ == "__main__":
    main()
