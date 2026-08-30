from flask import Blueprint, request, jsonify
from providers.pipeline import AggregationPipeline
from providers.jsonld import JsonLdProvider
from providers.html import HtmlProvider
bp=Blueprint('aggregator_api',__name__)
pipeline=AggregationPipeline([JsonLdProvider(),HtmlProvider()])
@bp.post('/api/aggregator/import')
def import_listing():
 url=(request.get_json(silent=True) or {}).get('url','').strip()
 if not url: return jsonify({'error':'url required'}),400
 return jsonify(pipeline.fetch(url))
