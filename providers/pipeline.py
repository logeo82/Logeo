from typing import Callable, List
from aggregator import Listing, merge_listings

class AggregationPipeline:
    def __init__(self, providers=None):
        self.providers = providers or []

    def add(self, provider):
        self.providers.append(provider)
        return self

    def fetch(self, url: str):
        results: List[Listing] = []
        errors = []
        for provider in self.providers:
            try:
                item = provider.fetch(url)
                if item: results.append(item)
            except Exception as exc:
                errors.append({"provider": getattr(provider, "name", provider.__class__.__name__), "error": str(exc)})
        merged = merge_listings(results)
        return {"listing": merged, "sources": [x.source for x in results], "errors": errors}
