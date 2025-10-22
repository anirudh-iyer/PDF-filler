import datetime
import logging
import os
import pytz
import uuid


class CustomLogger:
    def __init__(self, logger_name: str, log_prefix: str):
        """
        Initialize a generic logger with specified configuration.

        Args:
            logger_name (str): Name of the logger instance
            log_prefix (str): Prefix for log filename
        """
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.output_directory = os.path.join(project_root, "logs", log_prefix)
        os.makedirs(self.output_directory, exist_ok=True)

        self.time_stamp = datetime.datetime.now(pytz.UTC).strftime("%m_%d_%y_%H_%M_%S")
        self.unique_id = str(uuid.uuid4())

        self.log_filename = "{}_{}_{}.log".format(
            log_prefix, self.unique_id, self.time_stamp
        )
        self.log_filepath = os.path.join(self.output_directory, self.log_filename)

        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)

        self.logger.handlers = []
        file_handler = logging.FileHandler(self.log_filepath)
        file_handler.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.uuid = self.unique_id
            return record

        logging.setLogRecordFactory(record_factory)
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        print("Log Filename: {}".format(self.log_filename))

    def info(self, message: str) -> None:
        """
        Log info message.
        """
        self.logger.info(message)

    def error(self, message: str) -> None:
        """
        Log error message.
        """
        self.logger.error(message)

    def warning(self, message: str) -> None:
        """
        Log warning message.
        """
        self.logger.warning(message)

    def debug(self, message: str) -> None:
        """
        Log debug message.
        """
        self.logger.debug(message)
 