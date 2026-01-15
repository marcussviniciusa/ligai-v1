"""
Configurações do LigAI
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    # API Keys
    DEEPGRAM_API_KEY: str = os.getenv("DEEPGRAM_API_KEY", "")
    MURF_API_KEY: str = os.getenv("MURF_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # WebSocket Server
    WEBSOCKET_HOST: str = os.getenv("WEBSOCKET_HOST", "0.0.0.0")
    WEBSOCKET_PORT: int = int(os.getenv("WEBSOCKET_PORT", "8765"))

    # Audio Settings
    SAMPLE_RATE: int = 8000  # Taxa padrão para telefonia
    CHANNELS: int = 1
    SAMPLE_WIDTH: int = 2  # 16-bit

    # Deepgram Settings
    DEEPGRAM_MODEL: str = "nova-2"
    DEEPGRAM_LANGUAGE: str = "pt-BR"
    DEEPGRAM_ENCODING: str = "linear16"
    DEEPGRAM_SAMPLE_RATE: int = 8000

    # Murf AI Settings
    MURF_VOICE_ID: str = os.getenv("MURF_VOICE_ID", "pt-BR-isadora")
    MURF_STYLE: str = "conversational"

    # LLM Settings
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4.1-nano")
    LLM_MAX_TOKENS: int = 500
    LLM_TEMPERATURE: float = 0.7

    # Paths
    AUDIO_DIR: str = "/audio"
    LOGS_DIR: str = "/logs"

    # Timeouts
    SILENCE_TIMEOUT: float = 2.0  # segundos de silêncio para considerar fim de fala
    MAX_CALL_DURATION: int = 3600  # 1 hora máximo

    # Web Server
    WEB_PORT: int = int(os.getenv("WEB_PORT", "8000"))

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://ligai:ligai123@localhost:5432/ligai"
    )

    # Limits
    MAX_CONCURRENT_CALLS: int = int(os.getenv("MAX_CONCURRENT_CALLS", "15"))

    def validate(self) -> list[str]:
        """Valida configurações obrigatórias"""
        errors = []
        if not self.DEEPGRAM_API_KEY:
            errors.append("DEEPGRAM_API_KEY não configurada")
        if not self.MURF_API_KEY:
            errors.append("MURF_API_KEY não configurada")
        if not self.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY não configurada")
        return errors


settings = Settings()
