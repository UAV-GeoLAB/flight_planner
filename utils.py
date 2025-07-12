import os
import time
import traceback

def save_error():
    error_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'Error_log.txt')
    with open(error_path, 'a') as error_file:
        error_file.write(time.ctime(time.time()) + '\n')
        error_file.write(traceback.format_exc() + '\n')