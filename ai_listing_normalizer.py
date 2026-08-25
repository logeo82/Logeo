import os, json, urllib.request

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY') or os.environ.get('OPENAI_API_TOKEN')

SYSTEM = '''Tu es l'IA de normalisation immobilière de LOGEO. Tu reçois des données brutes d'une annonce immobilière. Corrige uniquement l'orthographe, la ponctuation et le format. Structure les informations dans le JSON demandé. N'invente JAMAIS une information absente. Conserve les valeurs numériques exactes. Si une donnée est incertaine ou absente, renvoie une chaîne vide ou null. La ville et le code postal doivent provenir des données source, jamais d'une supposition. Pour la description, améliore la rédaction sans ajouter de faits. Retourne uniquement un JSON valide.'''

SCHEMA = '''{
"title":"","description":"","city":"","postal_code":"","district":"","address":"","price":null,"rent_excl_charges":null,"charges":null,"deposit":null,"surface":null,"rooms":null,"bedrooms":null,"bathrooms":null,"floor":"","floors_total":null,"property_type":"","furnished":null,"lease_type":"","availability":"","parking":null,"garage":null,"balcony":null,"terrace":null,"garden":null,"cellar":null,"elevator":null,"heating":"","air_conditioning":null,"double_glazing":null,"fiber":null,"dpe":"","ges":"","latitude":null,"longitude":null,"features":[],"photos":[],'"'"'source_url'"'"':""}
'''

def normalize_listing(raw):
    if not OPENAI_API_KEY:
        return raw
    prompt = SYSTEM + '\nSchéma exact:\n' + SCHEMA + '\nDonnées brutes:\n' + json.dumps(raw, ensure_ascii=False) + '\nRetourne le JSON.'
    body = {'model': os.environ.get('LOGEO_AI_MODEL','gpt-4o-mini'), 'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':'Schéma exact:\n'+SCHEMA+'\nDonnées brutes:\n'+json.dumps(raw,ensure_ascii=False)}], 'temperature':0, 'response_format':{'type':'json_object'}}
    req=urllib.request.Request('https://api.openai.com/v1/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+OPENAI_API_KEY},method='POST')
    with urllib.request.urlopen(req,timeout=60) as r:
        data=json.loads(r.read().decode())
    return json.loads(data['choices'][0]['message']['content'])
