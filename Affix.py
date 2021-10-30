import logging
import os
import json

from typing import Any, Dict, List, Optional

from AffixDesc import AffixDesc


class Affix(object):
    def __init__(
        self,
        translations: AffixDesc,
        name: str,
        group: str,
        tags: List[str],
        a_type: str,
        stats: List[Dict[str, Any]],
        domain: str,
        essence: bool,
        weights: List[Dict[str, Any]]
    ):
        self.name = name
        self.group = group
        self.type = a_type
        self.tags = set(tags)
        self.weights = weights
        self.item_affix_tags = [w["tag"] for w in self.weights if w.get("weight", 0) > 0]
        self.stats = stats
        self.domain = domain
        self.essence = essence
        self.influence = self.parse_influence(self.weights)
        self.craftable = self.is_craftable()
        self.desc = ""
        self.items = []
        raw_desc = None

        raw_strs = set()
        for stat in self.stats:
            try:
                t = translations.get_raw(
                    stat["id"],
                    stat.get("min"),
                    stat.get("max"),
                )
                if t is not None:
                    raw_strs.add(t)
            except KeyError:
                continue
        base_str = "\n".join(list(raw_strs))

        for stat in self.stats:
            try:
                base_str = translations.get_translation(
                    stat["id"],
                    stat.get("min"),
                    stat.get("max"),
                    base_str
                )
            except KeyError:
                continue
            except TypeError as e:
                raise e
        self.desc = base_str
        if self.domain == "misc":
            raise TypeError("misc domain")

    def as_dict(self):
        return vars(self)

    @staticmethod
    def replace_string(v1, v2, s, fmt, fs):
        if fs == "ignore":
            return s
        elif f"{{{fmt}}}" not in s:
            raise Exception(f"{fmt} not in {s}")
        if v1 and v2:
            return s.replace(f"{{{fmt}}}", f"({v1}-{v2})")
        if v1:
            return s.replace(f"{{{fmt}}}", f"{v1}")

    @staticmethod
    def parse_influence(types):
        influence = set()
        for t in types:
            if "_elder" in t:
                influence.add("elder")
            elif "_shaper" in t:
                influence.add("shaper")
            elif "basilisk" in t:
                influence.add("basilisk")
            elif "_crusader" in t:
                influence.add("crusader")
            elif "_adjudicator" in t:
                influence.add("adjudicator")
            elif "_eyrie" in t:
                influence.add("eyrie")
        if len(influence) > 0:
            return list(influence)[0]
        else:
            return None

    @staticmethod
    def parse_types(types):
        base_types = set()
        for t in types:
            t = t.replace("attack_", "")
            t = t.replace("_elder", "")
            t = t.replace("_shaper", "")
            t = t.replace("_basilisk", "")
            t = t.replace("_crusader", "")
            t = t.replace("_adjudicator", "")
            t = t.replace("_eyrie", "")
            base_types.add(t)
        return base_types

    def is_craftable(self):
        if (
            (
                self.type == "suffix" or
                self.type == "prefix" or
                self.type == "corrupted"
            )
        ):
            craftable = False
            for weight in self.weights:
                if weight.get("weight", 0) > 0:
                    craftable = True
            return craftable

    def print_table(self):
        print(f"Mod: {self.desc}")
        print(f"\tName: {self.name}")
        print(f"\tType: {self.type}")
        print(f"\tTags: {self.tags}")
        print(f"\tCraftable on: {', '.join(self.base_types)}")
        print(f"\tInfluence: {self.influence}")
        print(f"\tEssence Only: {self.essence}")
        print(f"\tDomain: {self.domain}")
        print("\n")

