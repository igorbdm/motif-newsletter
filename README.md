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

## Song of the Week (Last.fm)

A seção Song of the Week recomenda uma música a partir do que foi ouvido no Last.fm na última semana (`src/song_of_the_week.py`):

1. Busca as músicas mais ouvidas dos últimos 7 dias.
2. Remove as que já foram recomendadas, conforme o histórico em `data/song_history.json`.
3. Dá preferência a artistas que não foram recomendados nas últimas 4 edições. Se só houver artistas recentes, eles continuam valendo, e a seção nunca fica vazia por causa disso.
4. Sorteia uma entre as 10 mais ouvidas que sobraram. Músicas com mais plays têm um pouco mais de chance (peso = raiz quadrada dos plays).
5. Se não houver nenhuma música nova na semana, tenta o último mês. Se ainda assim não houver, ou se o Last.fm estiver fora do ar, a edição sai sem a seção.

Depois de cada envio de produção, o workflow salva a música no histórico e faz commit em `data/song_history.json`. Envios de teste não alteram o histórico. Para impedir que uma música seja recomendada, basta adicioná-la ao arquivo manualmente.

O cartão da música traz links para Spotify, Apple Music e YouTube Music (`src/streaming_links.py`):

- **Apple Music:** link direto para a faixa, encontrado pela busca da Apple (iTunes Search API, sem chave).
- **YouTube Music:** link direto para a faixa oficial (canal "Artista - Topic"), encontrado pela API do YouTube com a mesma `YOUTUBE_API_KEY` dos vídeos. Cada busca gasta 100 unidades da cota diária.
- **Spotify:** link de busca. Um link direto exigiria um app no Spotify for Developers.

Só valem resultados com o mesmo artista e o mesmo título. Participações ("feat.") são ignoradas, mas versões ao vivo, remixes e covers não. Se a faixa exata não for encontrada, ou a busca falhar, o link daquela plataforma vira um link de busca e a edição sai normalmente.

Configure `LASTFM_API_KEY` e `LASTFM_USERNAME` no `.env`. No GitHub, a chave fica no secret `LASTFM_API_KEY` e o usuário está definido nos workflows. A chave é criada em https://www.last.fm/api/account/create.

## Títulos dos vídeos

No e-mail, o título de cada vídeo é padronizado como **Artista — Programa** (`src/titles.py`), por exemplo "Death Cab For Cutie — Live on KEXP" ou "Elvis Costello — What's In My Bag?". O nome do artista é recortado do título original com os padrões `artist_patterns` de cada canal e mantém a grafia do vídeo. O nome do programa vem de `program`, ou do próprio título quando o canal tem mais de um formato (na La Blogothèque, "A Take Away Show" ou "Live Session"). Se o título não encaixar em nenhum padrão, o vídeo aparece com o título original.

## Gênero musical dos vídeos

Cada vídeo das Live Sessions ganha um selo com o gênero do artista, ao lado do link (`src/genres.py`). Os vídeos do Beyond the Stage não levam selo.

1. O nome do artista é encontrado no título do vídeo, usando os padrões de cada canal (`artist_patterns` em `src/channels.py`). Nomes compostos ("Gillian Welch & David Rawlings") também são tentados por partes, e com e sem acentos.
2. Se o artista estiver em `data/genre_overrides.json`, vale o gênero de lá.
3. Senão, usa o gênero já descoberto em semanas anteriores (`data/artist_genres.json`) ou pergunta ao Last.fm. Só valem marcações que contenham uma palavra de gênero conhecida, o que descarta ruído como "seen live" ou "brazilian".
4. Se nada disso funcionar, usa a categoria do vídeo no YouTube ("Rock", "Jazz", "Pop").

Se o gênero não for encontrado, o vídeo aparece sem selo. Os gêneros descobertos são salvos pelo workflow junto com o histórico de músicas.

Para corrigir um gênero ou esconder o selo de um artista, edite `data/genre_overrides.json`:

```json
{
  "Fera Neném": "MPB",
  "James Blake": "electronic",
  "Artista sem selo": ""
}
```

Para fazer o Last.fm ser consultado de novo para um artista, apague a linha dele em `data/artist_genres.json`. Ao adicionar um canal novo, inclua `artist_patterns` para que os vídeos dele também ganhem o selo.

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

O workflow tenta executar 12 vezes às 09:48, 10:03, 10:18, 10:33, 10:48, 11:03, 11:18, 11:33, 11:48, 12:03, 12:18 e 12:33, sempre às sextas-feiras no fuso `America/Sao_Paulo`. Cada tentativa consulta primeiro o Kit pela identidade da edição e não cria outro Broadcast quando aquela identidade já possui um envio ativo ou concluído. Na produção, a identidade é a sexta-feira; no teste, cada execução manual recebe um ID único do GitHub. O workflow de produção também pode ser iniciado manualmente pela aba **Actions**. O workflow de teste é somente manual e deve ser executado selecionando a branch `test`. Antes de ativá-los, crie no GitHub os secrets `YOUTUBE_API_KEY`, `KIT_API_KEY` e `LASTFM_API_KEY`.

## Adicionar ou ajustar canais

Edite `src/channels.py`. Cada canal tem o ID do YouTube, palavras para manter (`keep`) e palavras para ignorar (`ignore`). Para o título padronizado e o selo de gênero, inclua também `program` e `artist_patterns`; o início do arquivo explica cada campo. Quando palavras não bastam para filtrar, `title_pattern` exige que o título siga um formato. É assim que a La Blogothèque recebe só sessões completas ("Naomi Greene | A Take Away Show") e descarta os vídeos de uma música só ("Rostam - The Road to Death | Live Session").
