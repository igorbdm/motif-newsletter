# Music Weekly

Uma newsletter semanal, simples, com apresentações musicais completas publicadas no YouTube.

O projeto usa a YouTube Data API v3 para ler os uploads de cada canal, seleciona os vídeos desejados e envia um e-mail em HTML.

> Antes usava os feeds RSS públicos do YouTube, mas esse feed só retorna os 15 uploads mais recentes de cada canal, então vídeos podiam ficar de fora quando um canal postava bastante coisa na semana. A API resolve isso porque permite paginar e buscar todos os uploads dos últimos 7 dias, não só os 15 mais recentes.

## Como funciona

1. Lê os canais definidos em `src/channels.py`.
2. Para cada canal, busca os uploads recentes via YouTube Data API.
3. Mantém títulos que contenham alguma palavra em `keep` e descarta os que contenham uma palavra em `ignore`.
4. Considera apenas vídeos publicados nos últimos sete dias que ainda não foram enviados.
5. Gera o e-mail, obtém os destinatários, envia-o e só então registra os vídeos no histórico (removendo automaticamente do histórico qualquer vídeo com mais de 7 dias, já que ele nunca mais seria consultado de qualquer forma).

## Configuração da API do YouTube

1. Crie uma chave de API gratuita no Google Cloud Console (Biblioteca de APIs → ative "YouTube Data API v3" → Credenciais → Criar credenciais → Chave de API).
2. Copie `.env.example` para um arquivo chamado `.env` e cole a chave em `YOUTUBE_API_KEY`.
3. No GitHub, adicione a mesma chave como um "Repository secret" chamado `YOUTUBE_API_KEY` (Settings → Secrets and variables → Actions). O workflow já está configurado para usá-la.

## Configuração do e-mail

Copie `.env.example` para um arquivo chamado `.env` e preencha os dados do SMTP. Esse arquivo não é enviado ao GitHub.

> Para Gmail, use uma senha de aplicativo — não a sua senha normal.

Antes de executar, disponibilize essas variáveis no terminal com `set -a; source .env; set +a`.

### Kit

Para enviar pelo Kit, configure estas variáveis:

```bash
EMAIL_DELIVERY_PROVIDER=kit
KIT_API_KEY=sua-chave-v4
KIT_TAG_NAME=music-weekly
KIT_SENDER_EMAIL=oi@igorbdm.com
KIT_PUBLISH_TO_WEB=false
```

O Kit gerencia os assinantes da tag; por isso `EMAIL_TO` não é usado nesse modo. A tag precisa existir antes da execução. O padrão mantém a versão web desativada.

## Executar manualmente

Instale as dependências:

```bash
python3 -m pip install -r requirements.txt
```

Depois de definir as configurações de e-mail e da API do YouTube, execute:

```bash
python3 src/main.py
```

O arquivo `newsletter.html` também é criado localmente como uma cópia para conferência. Se o envio falhar, nenhum vídeo é adicionado ao histórico.

## Arquitetura de envio

O núcleo não depende de SMTP nem de uma origem específica de assinantes:

- `src/newsletter_sender.py` define o contrato de entrega de uma edição;
- `src/mailer.py` e `src/subscribers.py` mantêm o caminho SMTP compatível com `EMAIL_TO`;
- `src/kit.py` integra broadcasts do Kit a uma tag da audiência;
- `src/bootstrap.py` escolhe o provedor a partir de `EMAIL_DELIVERY_PROVIDER`.

Por enquanto, `EMAIL_TO` aceita um endereço (como antes) ou uma lista separada por vírgulas. No Kit, a audiência fica na tag configurada. Ao escolher outro provedor, implemente um novo remetente e altere apenas `bootstrap.py`.

## GitHub Actions

O workflow inicia a preparação às 07:59 de segunda-feira no horário de Brasília e agenda o envio no Kit para 08:00. Ele também pode ser iniciado manualmente pela aba **Actions**. Antes de ativá-lo, crie no GitHub os secrets `YOUTUBE_API_KEY` e `KIT_API_KEY`. Após o Kit aceitar a campanha, o workflow cria um commit com o histórico atualizado.

## Adicionar ou ajustar canais

Edite `src/channels.py`. Cada canal tem o ID do YouTube, palavras para manter (`keep`) e palavras para ignorar (`ignore`).
