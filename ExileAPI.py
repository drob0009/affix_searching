
import logging
import os
import json

from collections import defaultdict
from typing import Any, Dict, List, Optional

import pandas as pd
from Affix import Affix
from AffixDesc import AffixDesc
from Items import Item


class ExileAPI():
    def __init__(
        self,
        affix_file: Optional[str] = None,
        translation_file: Optional[str] = None,
        item_file: Optional[str] = None,
        log_level=logging.ERROR,
    ):
        self.log_level = log_level
        if affix_file is None:
            affix_file = os.path.join(
                os.path.dirname(__file__),
                os.path.join("data", "mods.json")
            )

        if translation_file is None:
            translation_file = os.path.join(
                os.path.dirname(__file__),
                os.path.join("data", "stat_translations.json")
            )
        if item_file is None:
            item_file = os.path.join(
                os.path.dirname(__file__),
                os.path.join("data", "base_items.json")
            )

        self.base = "https://api.pathofexile.com"
        self.__logger_setup(log_level)
        self.translations = AffixDesc(translation_file)

        self.affixes = self.__parse_affixes(affix_file)
        self.item_a_tags = set()
        for a in self.affixes:
            self.item_a_tags |= set(a.item_affix_tags)
        self.__logger.debug(f"{len(self.affixes)} affixes loaded")

        self.items = self.__parse_items(item_file)
        self.affixes_by_class = defaultdict(set)

        for item in self.items:
            self.affixes_by_class[item.item_class] |= set(item.tags)

        self.__logger.debug(f"{len(self.items)} items loaded")

    def __parse_affixes(self, path):
        self.__logger.debug(f"Opening {path}")
        affix_data = None
        with open(path, "r") as f:
            affix_data = json.load(f)
        self.__logger.debug("Parsing affixes")
        affixes = []
        for k, d in affix_data.items():
            try:
                a = Affix(
                    self.translations,
                    d.get("name"),
                    d.get("group"),
                    d.get("implicit_tags"),
                    d.get("generation_type"),
                    d.get("stats"),
                    d.get("domain"),
                    d.get("is_essence_only", False),
                    d.get("spawn_weights"),
                )
                affixes.append(a)
            except TypeError:
                affixes.append(a)
            except Exception as e:
                self.__logger.error(f"{k} - {d} failed")
                raise e
        self.__logger.debug("Affix parse complete")
        return affixes

    def __parse_items(self, path):
        assert len(self.affixes) > 0
        item_data = None
        items = []
        with open(path, "r") as f:
            item_data = json.load(f)
        for k, v in item_data.items():
            i = Item(
                name=v.get("name"),
                domain=v.get("domain"),
                tags=v.get("tags", []),
                item_class=v.get("item_class"),
                drop_level=v.get("drop_level"),
                all_affix=self.affixes,
                log_level=self.log_level,
                ia_tags=self.item_a_tags,
            )
            items.append(i)
        return items

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

    def find_affix_by_tag(self, tags: List[str]) -> List[Affix]:
        results = []
        for affix in self.affixes:
            intersect = affix.tags & set(tags)
            if len(intersect) == len(tags):
                results.append(affix)
        return results

    def find_affix_by_class(
        self,
        item_classes: List[str]
    ) -> List[Affix]:
        all_search_tags = []
        for cl in item_classes:
            all_search_tags += list(self.affixes_by_class[cl])
        self.__logger.debug(f"Searching for {all_search_tags}")
        return self.find_affix_by_ia_tag(all_search_tags)

    def find_affix_by_ia_tag(
        self,
        types: List[str],
    ) -> List[Affix]:
        results = []
        for affix in self.affixes:
            intersect = set(affix.item_affix_tags) & set(types)
            if len(intersect) > 0:
                results.append(affix)
        return results

    @staticmethod
    def as_df(result_list: List[Affix]) -> pd.DataFrame:
        return pd.DataFrame([affix.as_dict() for affix in result_list])
