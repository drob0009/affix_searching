from ExileAPI import ExileAPI
import logging

api = ExileAPI(log_level=logging.ERROR)

find_by_tag = set([
    affix
    for affix in api.find_affix_by_tag(["chaos"])
    if affix.craftable
])

find_by_slot = set([
    affix
    for affix in api.find_affix_by_type(["bow", "gloves"])
    if affix.craftable
])

results = find_by_tag.intersection(find_by_slot)

for affix in sorted(list(results), key=lambda x: x.influence if x.influence is not None else ""):
    affix.print_table()