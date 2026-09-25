from __future__ import annotations

from typing import Any, List

from stix2 import Bundle


def create_bundle(objects: List[Any]) -> Bundle:
    if not objects:
        raise ValueError("Cannot create a STIX bundle with zero objects")
    return Bundle(objects=objects, allow_custom=False)


def bundle_to_json(bundle: Bundle) -> str:
    return bundle.serialize(pretty=False)
