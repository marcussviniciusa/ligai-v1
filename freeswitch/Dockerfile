# FreeSWITCH com mod_audio_fork para LigAI
# A imagem drachtio já inclui mod_audio_fork para streaming de áudio via WebSocket

FROM drachtio/drachtio-freeswitch-mrf:v1.10.1-full

# Criar diretórios necessários
RUN mkdir -p /var/lib/freeswitch/sounds/custom /var/log/freeswitch

# Expor portas
EXPOSE 5060/udp 5060/tcp 5080/udp 5080/tcp 8021/tcp 16384-32768/udp

# Variáveis de ambiente
ENV PATH="/usr/local/freeswitch/bin:$PATH"

# Comando de inicialização
CMD ["/usr/local/freeswitch/bin/freeswitch", "-nonat", "-nf"]
