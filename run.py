import os
import multiprocessing

def start_flask():
    os.system("python core/app.py")

def start_datasette():
    os.system("python immunefi-terminal/run.py")

if __name__ == "__main__":
    # Create separate processes for Flask and Datasette
    flask_process = multiprocessing.Process(target=start_flask)
    datasette_process = multiprocessing.Process(target=start_datasette)

    # Start both processes
    flask_process.start()
    datasette_process.start()

    # Wait for both processes to finish
    flask_process.join()
    datasette_process.join()
