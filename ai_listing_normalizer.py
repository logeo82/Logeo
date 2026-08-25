import os, json, urllib.request

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY') or os.environ.get('OPENAI_API_TOKEN')

SYSTEM = '''Tu es l'IA de correction rédactionnelle de LOGEO. Tu ne reconstruis PAS une annonce. Tu modifies uniquement les champs textuels title, description et features. Corrige l'orthographe, la grammaire et la ponctuation sans ajouter de faits. Tous les autres champs doivent être renvoyés strictement identiques aux données source. Les photos doivent être renvoyées strictement à l'identique. N'invente jamais une information.'''

TEXT_KEYS={'title','description','features'}

def normalize_listing(raw):
    if not OPENAI_API_KEY:
        return raw
    original=json.loads(json.dumps(raw,ensure_ascii=False))
    payload={k:original.get(k) for k in TEXT_KEYS}
    body={'model':os.environ.get('LOGEO_AI_MODEL','gpt-4o-mini'),'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':'Corrige uniquement ces champs et retourne uniquement un JSON avec title, description et features.\n'+json.dumps(payload,ensure_ascii=False)}],'temperature':0,'response_format':{'type':'json_object'}}
    req=urllib.request.Request('https://api.openai.com/v1/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+OPENAI_API_KEY},method='POST')
    with urllib.request.urlopen(req,timeout=60) as r: data=json.loads(r.read().decode())
    corrected=json.loads(data['choices'][0]['message']['content'])
    result=original
    for k in TEXT_KEYS:
        if k in corrected and corrected[k] not in (None,''): result[k]=corrected[k]
    result['photos']=original.get('photos',[])
    result['source_url']=original.get('source_url','')
    return result
