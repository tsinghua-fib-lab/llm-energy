import subprocess
import signal
import os
import sys

# List to save processes
processes = []
MODEL_YAML = "" # Model configuration file in llamafactory
PARALLEL = 4 # Number of parallel services

def start_services():
    try:
        # Start the first service
        for i in range(PARALLEL):
            proc = subprocess.Popen(
                f"API_PORT=800{i} CUDA_VISIBLE_DEVICES={i} llamafactory-cli api {MODEL_YAML}",
                shell=True,
                preexec_fn=os.setsid  # Use a separate process group
            )
            processes.append(proc)

    except Exception as e:
        print(f"Error occurred while starting services: {e}")

def stop_services(signum, frame):
    print("Stopping all services...")
    for proc in processes:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)  # Terminate the entire process group
        except Exception as e:
            print(f"Error occurred while stopping process {proc.pid}: {e}")
    sys.exit(0)

if __name__ == "__main__":
    # Capture termination signals (e.g., SIGTERM or SIGINT)
    signal.signal(signal.SIGTERM, stop_services)
    signal.signal(signal.SIGINT, stop_services)

    try:
        # Start all services
        start_services()

        # Keep the script running in the background
        print("Services are running. Waiting for termination signal...")
        signal.pause()  # Wait for signal

    finally:
        # Stop all services when the script ends
        print("Service terminated")
        stop_services(None, None)
