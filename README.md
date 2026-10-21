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

## Windows 10/11 — versão pronta

Use o ZIP da [versão oficial v1.1.0](https://github.com/tiolusystems/classica-x/releases/tag/v1.1.0), arquivo `ClassicaX-1.1.0-Windows-x64.zip`. Extraia **toda a pasta**; não mova o executável isoladamente. Não é necessário instalar Python. O pacote ainda não tem assinatura digital; os releases incluem SHA-256 para conferir a integridade.

O aplicativo pode ser instalado ou atualizado pela opção **Plataformas** do Clássica 2.3.0, quando essa versão estiver publicada. A atualização do módulo é opcional e não altera o Clássica YouTube.


## Interface integrada (1.1.0)

Quando iniciado pela central Clássica com a variável de sessão local
`CLASSICA_X_EMBED_READY_FILE`, o módulo X não abre uma nova janela de navegador.
Sua interface aparece na aba X da aplicação principal, mantendo execução,
API autenticada, arquivos e histórico próprios. Iniciar o executável X diretamente
continua abrindo uma página própria, sem depender do YouTube.
