
import logging
import os
import json
import requests
from collections import defaultdict
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin


class AffixDesc():
    def __init__(self, path, logger):
        self.logger = logger

        self.translations = self.__parse_translations(path)

    def __parse_translations(self, path):
        self.logger.debug(f"Opening {path}")
        translations = {}
        translation_data = None
        with open(path, "r") as f:
            translation_data = json.load(f)

        fmts = defaultdict(list)

        for entry in translation_data:
            translation_string = ""
            ids = entry["ids"]

            for e2 in entry["English"]:
                for i in range(len(ids)):
                    fmt_data = {}
                    fmt_data["condition"] = e2["condition"][i]
                    fmt_data["format"] = e2["format"][i]
                    fmt_data["ih"] = e2["index_handlers"][i]
                    tmp = e2["string"]
                    for j in range(len(ids)):
                        tmp = tmp.replace(f"{{{j}}}", f"{{{ids[j]}}}")
                    fmt_data["string"] = tmp
                    fmts[ids[i]].append(fmt_data)
        return dict(fmts)

    def get_translation(self, id: str, amin: int, amax: int, base_str):
        def replace_string(v1=None, v2=None, s=None, fmt=None, fs=None):
            if fs == "ignore":
                return s
            elif f"{{{fmt}}}" not in s:
                raise Exception(f"{fmt} not in {s}")
            if v1 is not None and v2 is not None:
                return s.replace(f"{{{fmt}}}", f"({v1}-{v2})")
            if v1 is not None:
                return s.replace(f"{{{fmt}}}", f"{v1}")
            raise ValueError(f"No match found: {v1} {v2} {s} {fmt} {fs}")

        entries = self.translations.get(id, None)
        if entries is None:
            self.logger.warning(f"No translations found for {id}")
            return base_str

        for entry in entries:
            cmin = entry["condition"].get("min")
            cmax = entry["condition"].get("max")
            fs = entry["format"]
            if cmin and cmax:
                if cmin <= amin <= cmax:
                    if cmin <= amax <= cmax:
                        return replace_string(amin, amax, base_str, id, fs)
            elif cmin:
                if cmin <= amin and cmin <= amax:
                    return replace_string(amin, amax, base_str, id, fs)

            elif cmax:
                if amin <= cmax and amax <= cmax:
                    return replace_string(amin, amax, base_str, id, fs)
            elif cmin is None and cmax is None:
                return replace_string(amin, amax, base_str, id, fs)

        raise KeyError(f"No matching condition: {id} - min {amin} max {amax}")

    def get_raw(self, id: str, amin: int, amax: int):
        try:
            entries = self.translations[id]
        except KeyError:
            self.logger.warning(f"No translations found for {id}")
            return ""
        for entry in entries:
            cmin = entry["condition"].get("min")
            cmax = entry["condition"].get("max")
            fs = entry["format"]
            rstr = entry["string"]
            if cmin and cmax:
                if cmin <= amin <= cmax:
                    if cmin <= amax <= cmax:
                        return rstr
            elif cmin:
                if cmin <= amin and cmin <= amax:
                    return rstr
            elif cmax:
                if amin <= cmax and amax <= cmax:
                    return rstr
            elif cmin is None and cmax is None:
                return rstr

class Affix():
    def __init__(
        self,
        logger,
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
        self.logger = logger
        self.name = name
        self.group = group
        self.type = a_type
        self.tags = set(tags)
        self.stats = stats
        self.domain = domain
        self.essence = essence
        self.weights = weights
        self.full_types = [w["tag"] for w in self.weights if w.get("weight", 0) > 0]
        self.influence = self.parse_influence(self.full_types)
        self.base_types = self.parse_types(self.full_types)        
        self.craftable = self.is_craftable()
        self.desc = ""
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
                self.logger.error("KE")
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
                self.logger.error(f"{e}:\n\t{stat}")
                raise e
        self.desc = base_str

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
            (self.type == "suffix" or self.type == "prefix")
            and self.domain == "item"
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
        print("\n")


class ExileAPI():
    def __init__(
        self,
        affix_file: Optional[str] = None,
        translation_file: Optional[str] = None,
        log_level=logging.ERROR,
    ):
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

        self.base = "https://api.pathofexile.com"
        self.__logger_setup(log_level)
        self.translations = AffixDesc(translation_file, self.logger)
        self.affixes = self.__parse_affixes(affix_file)
        self.logger.debug(f"{len(self.affixes)} affixes loaded")



    def __parse_affixes(self, path):
        self.logger.debug(f"Opening {path}")
        affix_data = None
        with open(path, "r") as f:
            affix_data = json.load(f)
        self.logger.debug("Parsing affixes")
        affixes = []
        for k, d in affix_data.items():
            try:
                a = Affix(
                    self.logger,
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
            except Exception as e:
                self.logger.error(f"{k} - {d} failed")
                raise e
           
        self.logger.debug("Affix parse complete")
        return affixes

    def __logger_setup(self, log_level):
        log_format = logging.Formatter(
            "[%(levelname)s]:%(filename)s:%(lineno)d - %(message)s"
        )
        ch = logging.StreamHandler()
        # ch.setLevel(log_level)
        ch.setFormatter(log_format)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.addHandler(ch)
        self.logger.setLevel(log_level)

    def find_affix_by_tag(self, tags: List[str]) -> List[Affix]:
        results = []
        for affix in self.affixes:
            intersect = affix.tags.intersection(set(tags))
            if len(intersect) == len(tags):
                results.append(affix)
        return results

    def find_affix_by_type(self, types: List[str]) -> List[Affix]:
        results = []
        for affix in self.affixes:
            intersect = affix.base_types.intersection(set(types))
            if len(intersect) > 0:
                results.append(affix)
        return results
