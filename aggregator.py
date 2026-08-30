"""Clean multi-source listing aggregator for Logeo.
Each provider is isolated: a provider failure never blocks the others.
"""
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
import re

@dataclass
class Listing:
    source: str
    source_url: str
    title: str = ""
    description: str = ""
    price: Optional[float] = None
    surface: Optional[float] = None
    city: str = ""
    photos: List[str] = None
    raw: Dict[str, Any] = None
    confidence: float = 0.0

    def __post_init__(self):
        self.photos = self.photos or []
        self.raw = self.raw or {}

class Provider:
    name = "base"
    def fetch(self, url: str) -> Optional[Listing]:
        raise NotImplementedError

def clean_text(value: Any) -> str:
    if value is None: return ""
    s = re.sub(r"\s+", " ", str(value)).strip()
    return s

def merge_listings(items: List[Listing]) -> Optional[Listing]:
    """Merge providers without losing the richest description/photos."""
    valid = [x for x in items if x]
    if not valid: return None
    valid.sort(key=lambda x: (len(x.description), len(x.photos), x.confidence), reverse=True)
    best = valid[0]
    photos=[]; seen=set()
    for x in valid:
        for p in x.photos:
            if p and p not in seen: seen.add(p); photos.append(p)
    data=asdict(best); data["photos"]=photos
    for field in ("title","description","city"):
        vals=[clean_text(getattr(x,field,"")) for x in valid]
        if max(vals,key=len,default=""): data[field]=max(vals,key=len)
    for field in ("price","surface"):
        if data.get(field) is None:
            for x in valid:
                if getattr(x,field,None) is not None: data[field]=getattr(x,field); break
    data["raw"]={x.source:x.raw for x in valid}
    data["sources"]=[x.source for x in valid]
    return data
