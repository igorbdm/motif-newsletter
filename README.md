# Motif Newsletter

Uma newsletter semanal, simples, com apresentações musicais completas publicadas no YouTube.

O projeto usa a YouTube Data API v3 para ler os uploads de cada canal, seleciona os vídeos desejados e envia um e-mail em HTML.

> Antes usava os feeds RSS públicos do YouTube, mas esse feed só retorna os 15 uploads mais recentes de cada canal, então vídeos podiam ficar de fora quando um canal postava bastante coisa na semana. A API resolve isso porque permite paginar e buscar todos os uploads desde a última edição semanal, não só os 15 mais recentes.

## Como funciona

1. Lê os canais definidos em `src/channels.py`.
2. Para cada canal, busca os uploads recentes via YouTube Data API.
3. Mantém títulos que contenham alguma palavra em `keep` e descarta os que contenham uma palavra em `ignore`.
4. Considera apenas vídeos publicados desde a sexta-feira anterior à edição atual.
5. Gera o e-mail, verifica no Kit se a edição daquela execução já possui um Broadcast e só cria um novo Broadcast quando não existe outro ativo. Na produção, a edição é identificada pela data da sexta-feira; nos testes, cada execução manual recebe um identificador único do GitHub.

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
KIT_SENDER_EMAIL=oi@igorbdm.com
KIT_PUBLISH_TO_WEB=false
```

O Kit gerencia os assinantes da tag; por isso `EMAIL_TO` não é usado nesse modo. As tags `music-weekly` e `test` precisam existir antes das execuções correspondentes. O padrão mantém a versão web desativada.

A audiência do Kit é definida automaticamente pela branch em execução: `main` envia para `music-weekly` e `test` envia para `test`. A branch `test` possui um workflow separado de disparo manual; ela não participa do agendamento automático.

## Executar manualmente

Instale as dependências:

```bash
python3 -m pip install -r requirements.txt
```

Depois de definir as configurações de e-mail e da API do YouTube, execute:

```bash
python3 src/main.py
```

O arquivo `newsletter.html` também é criado localmente como uma cópia para conferência antes do envio.

## Arquitetura de envio

O núcleo não depende de SMTP nem de uma origem específica de assinantes:

- `src/newsletter_sender.py` define o contrato de entrega de uma edição;
- `src/mailer.py` e `src/subscribers.py` mantêm o caminho SMTP compatível com `EMAIL_TO`;
- `src/kit.py` integra broadcasts do Kit a uma tag da audiência;
- `src/bootstrap.py` escolhe o provedor a partir de `EMAIL_DELIVERY_PROVIDER`.

Por enquanto, `EMAIL_TO` aceita um endereço (como antes) ou uma lista separada por vírgulas. No Kit, a audiência é escolhida automaticamente pela branch. Ao escolher outro provedor, implemente um novo remetente e altere apenas `bootstrap.py`.

## GitHub Actions

O workflow tenta executar 12 vezes às 09:48, 10:03, 10:18, 10:33, 10:48, 11:03, 11:18, 11:33, 11:48, 12:03, 12:18 e 12:33, sempre às sextas-feiras no fuso `America/Sao_Paulo`. Cada tentativa consulta primeiro o Kit pela identidade da edição e não cria outro Broadcast quando aquela identidade já possui um envio ativo ou concluído. Na produção, a identidade é a sexta-feira; no teste, cada execução manual recebe um ID único do GitHub. O workflow de produção também pode ser iniciado manualmente pela aba **Actions**. O workflow de teste é somente manual e deve ser executado selecionando a branch `test`. Antes de ativá-los, crie no GitHub os secrets `YOUTUBE_API_KEY` e `KIT_API_KEY`.

## Adicionar ou ajustar canais

Edite `src/channels.py`. Cada canal tem o ID do YouTube, palavras para manter (`keep`) e palavras para ignorar (`ignore`).
