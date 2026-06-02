"""Cliente HTTP minimo baseado em urllib (stdlib), evitando a dependencia
`requests`. Usado na comunicacao entre microsservicos (REST/JSON)."""
import json
import urllib.error
import urllib.request


class HttpResponse:
    def __init__(self, status, body):
        self.status = status
        self.body = body

    def json(self):
        try:
            return json.loads(self.body) if self.body else None
        except json.JSONDecodeError:
            return None

    @property
    def ok(self):
        return 200 <= self.status < 300


def request(method, url, json_body=None, headers=None, timeout=5):
    data = None
    hdrs = dict(headers or {})
    if json_body is not None:
        data = json.dumps(json_body).encode()
        hdrs.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return HttpResponse(resp.status, resp.read().decode())
    except urllib.error.HTTPError as exc:
        # Resposta com status de erro (4xx/5xx) ainda traz corpo util.
        return HttpResponse(exc.code, exc.read().decode())
    # urllib.error.URLError e socket.timeout sobem para o chamador tratar.


def get(url, **kwargs):
    return request("GET", url, **kwargs)


def post(url, **kwargs):
    return request("POST", url, **kwargs)
