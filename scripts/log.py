import logging


def get_logger(
    name, *, filename=None, console_level=logging.INFO, file_level=logging.WARNING
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    c_handler = logging.StreamHandler()
    c_handler.setLevel(console_level)
    c_format = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
    c_handler.setFormatter(c_format)
    logger.addHandler(c_handler)

    if filename:
        f_handler = logging.FileHandler(filename)
        f_handler.setLevel(file_level)
        f_format = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        f_handler.setFormatter(f_format)
        logger.addHandler(f_handler)

    return logger
