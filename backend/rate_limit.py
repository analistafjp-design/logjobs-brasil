import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

_registros = defaultdict(deque)


def limitar_por_ip(request: Request, chave: str, max_pedidos: int = 5, janela_segundos: int = 600):
    """Limitador simples em memória: no máximo `max_pedidos` por IP a cada `janela_segundos`.
    Não é distribuído entre instâncias, mas é suficiente para uma única instância (plano free)."""
    ip = request.client.host if request.client else "desconhecido"
    agora = time.monotonic()
    fila = _registros[(chave, ip)]

    while fila and agora - fila[0] > janela_segundos:
        fila.popleft()

    if len(fila) >= max_pedidos:
        raise HTTPException(status_code=429, detail="Muitas tentativas. Aguarde alguns minutos e tente novamente.")

    fila.append(agora)
