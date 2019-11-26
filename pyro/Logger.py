import logging


class Logger:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname).4s] %(message)s')
    log = logging.getLogger()

    @staticmethod
    def print_list(label: str, items: list, item_format: str = '+ "{}"') -> None:
        Logger.log.info(label)
        for item in items:
            Logger.log.info(item_format.format(item))
