"""Gerenciador de conexões WebSocket do chat, em memória — mesmo raciocínio do
rate_limit.py: não é distribuído entre instâncias, mas é suficiente para uma
única instância (plano free do Render). A conexão só existe enquanto o
candidato/empresa está com a tela da conversa aberta; não há nada em segundo
plano rodando sem uma tela de chat aberta."""
from collections import defaultdict

from fastapi import WebSocket


class GerenciadorChat:
    def __init__(self):
        self._conexoes: dict[int, set[WebSocket]] = defaultdict(set)

    async def conectar(self, conversa_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._conexoes[conversa_id].add(websocket)

    def desconectar(self, conversa_id: int, websocket: WebSocket) -> None:
        conexoes = self._conexoes.get(conversa_id)
        if not conexoes:
            return
        conexoes.discard(websocket)
        if not conexoes:
            self._conexoes.pop(conversa_id, None)

    async def transmitir(self, conversa_id: int, mensagem: dict) -> None:
        conexoes = list(self._conexoes.get(conversa_id, ()))
        for websocket in conexoes:
            try:
                await websocket.send_json(mensagem)
            except Exception:
                self.desconectar(conversa_id, websocket)


gerenciador_chat = GerenciadorChat()
