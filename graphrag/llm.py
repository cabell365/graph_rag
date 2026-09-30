import requests
from .config import Settings

class Ollama:
    def __init__(self, settings=None):
        self.s = settings or Settings()

    def embed(self, texts, query=False):
        prefix = 'search_query: ' if query else 'search_document: '
        response = requests.post(self.s.ollama + '/api/embed', json={
            'model': self.s.embed_model, 'input': [prefix + t for t in texts],
            'truncate': False}, timeout=240)
        if not response.ok:
            raise RuntimeError(f'Ollama embedding error {response.status_code}: {response.text[:500]}')
        return response.json()['embeddings']

    def stream(self, messages):
        with requests.post(self.s.ollama + '/api/chat', json={
            'model': self.s.chat_model, 'messages': messages, 'stream': True,
            'options': {'temperature': 0, 'num_ctx': 16384}}, timeout=300, stream=True) as response:
            response.raise_for_status()
            import json
            for line in response.iter_lines():
                if line:
                    item = json.loads(line)
                    if item.get('error'):
                        raise RuntimeError(item['error'])
                    yield item.get('message', {}).get('content', '')

    def health(self):
        response = requests.get(self.s.ollama + '/api/tags', timeout=5)
        response.raise_for_status()
        return [m['name'] for m in response.json()['models']]
