import logging
import json
import os

from Affix import Affix
from dataclasses import dataclass, field, InitVar
from typing import List


@dataclass
class Item:
    name: str
    domain: str
    tags: List[str]
    item_class: str
    drop_level: int
    affixes: List[Affix] = field(default_factory=list)
    all_affix: InitVar[List[Affix]] = None
    log_level: InitVar[int] = logging.ERROR
    ia_tags: InitVar[set] = None

    def __post_init__(self, all_affix: List[Affix], log_level: int, ia_tags: set):
        self.__logger_setup(log_level)

        # Filter out non-affix tags.
        self.tags = list(set(self.tags) & ia_tags)
        for affix in all_affix:
            for tag in self.tags:
                if tag in affix.item_affix_tags:
                    self.affixes.append(affix)

    def __logger_setup(self, log_level):
        log_format = logging.Formatter(
            "[%(levelname)s]:%(filename)s:%(lineno)d - %(message)s"
        )
        ch = logging.StreamHandler()
        # ch.setLevel(log_level)
        ch.setFormatter(log_format)
        self.__logger = logging.getLogger(self.__class__.__name__)
        if not self.__logger.handlers:
            self.__logger.addHandler(ch)
        self.__logger.setLevel(log_level)
