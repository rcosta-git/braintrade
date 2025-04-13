import logging
import os
import sys

def setup_logging(log_level=logging.DEBUG, log_dir='logs', log_filename='braintrade_monitor.log'):
    """Configures logging to file and console."""

    # Ensure log directory exists
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
        except OSError as e:
            print(f"Error creating log directory {log_dir}: {e}", file=sys.stderr)
            # Optionally fall back to logging only to console or raise error
            # For now, we'll continue and file logging might fail
            pass

    log_file_path = os.path.join(log_dir, log_filename)

    # Configure root logger
    # Use basicConfig only if no handlers are configured yet
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(level=log_level,
                            format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s',
                            handlers=[logging.FileHandler(log_file_path, mode='a')]) # File handler added here

        # Add console handler
        console_handler = logging.StreamHandler(sys.stdout) # Use stdout
        console_handler.setLevel(log_level)
        # Use a simpler format for console
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        logging.getLogger().addHandler(console_handler)

        logging.info("Logging configured: File handler added, Console handler added.")
    else:
         logging.info("Logging already configured.")

if __name__ == '__main__':
    # Example usage/test
    setup_logging()
    logging.info("This is an info message from logging_setup test.")
    logging.warning("This is a warning message from logging_setup test.")
    logging.error("This is an error message from logging_setup test.")