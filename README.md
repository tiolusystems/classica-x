# Clássica X

Aplicação local e independente para salvar vídeos públicos individuais de `x.com` e `twitter.com` quando houver autorização ou fundamento legal.

Não solicita senhas, não gerencia cookies, não contorna DRM, CAPTCHA ou restrições de acesso e não baixa timelines, perfis ou lotes. O usuário confirma a autorização antes de qualquer ação.

## Executar

```powershell
py -m venv .venv
.\.venv\Scripts\python -m pip install -e . pytest
.\.venv\Scripts\classica-x
```

Requer `ffmpeg` e `ffprobe` no `PATH`. Dados ficam em `%LOCALAPPDATA%\ClassicaX` no Windows (ou no diretório de dados equivalente do sistema); mídia vai para a pasta escolhida pelo usuário.

## Atualizações

Atualize manualmente por uma nova pasta/pacote versionado. A aplicação não se atualiza silenciosamente e não lê, grava ou atualiza arquivos do Clássica YouTube.
