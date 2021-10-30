import logging
import os
import json

from collections import defaultdict
from typing import Any, Dict, List, Optional


class AffixDesc():
    def __init__(self, path):

        self.translations = self.__parse_translations(path)

    def __parse_translations(self, path):
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
