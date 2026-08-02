<div align="center">
  <img src="data/img/logo_rounded.png" height="100px" alt="logo">
</div>

<h3 align="center">@alpolimibot</h3>

<p align="center"> 
  Trova le <b>aule libere</b> e guarda lo stato di occupazione della <b>biblioteca</b> direttamente da Telegram
  <br> 
  <br>
</p>


[**@alpolimibot**](https://t.me/alpolimibot) è un Bot Telegram non ufficiale per consultare la **disponibilità delle aule del Politecnico di Milano**. Permette di verificare quali aule sono libere nel momento della ricerca o in un giorno e ora futuri. Inoltre è possibile consultare anche lo **stato di occupazione delle biblioteche** di ateneo in tempo reale.

[![Telegram](https://img.shields.io/badge/Telegram-24A1DE?style=for-the-badge&logoColor=white&logo=Telegram)](https://t.me/alpolimibot)


## Funzionalità <a name = "features"></a>

- Stato di **occupazione delle biblioteche** di ateneo in tempo reale
- Disponibilità di **prese elettriche e di rete** nelle aule
- **Immagini** delle aule
- Ricerca di disponibilità in un giorno e fascia oraria futura
- **Aule preferite** 


## Comandi disponibili <a name = "commands"></a>

| Comando | Descrizione |
| --- | --- |
| `/start` | Benvenuto e riepilogo dei comandi disponibili |
| `/settings` | Impostazione sede e lingua predefinite |
| `/now` | Mostra le aule attualmente libere nella sede preferita |
| `/search` | Cerca aule libere in un periodo futuro nella sede preferita |
| `/fav` | Elenco delle aule preferite, con stato di occupazione attuale |
| `/report` | Invio di una segnalazione anonima (solo testo e data, nessun mittente) |
| `/biblio` | Mostra l'occupazione in tempo reale della biblioteca |
| `/help` | Elenco dei comandi disponibili |
| `/about` | Informazioni sul bot |
| `/userinfo` | Mostra i dati che Telegram espone sull'utente e quelli che il bot memorizza |

Si può **cercare un'aula digitando direttamente la sigla**, ad esempio `T.1.2` oppure `T12`.

## Todos <a name = "todo"></a>

- [ ] Gestione delle aule di cui le fasce di occupazione sui servizi online sono distribuite su più righe per lo stesso giorno. L'attuale parser non le supporta. In queste situazioni le fasce di occupazione registrate sono corrette, ma manca il nome del corso.
- [ ] Dashboard Grafana per monitoring

## Architettura <a name = "structure"></a>

**Tutti i dati relativi all'accupazione delle aule vengono scaricati in anticipo.** Questo rende il bot estremamente veloce nelle risposte e permette di verificare la disponibilità delle aule in giorni successivi. Il progetto si basa sull'idea che tutti i dati restituiti dal bot siano sempre presenti in locale e ottenuti in anticipo. **Il bot accede sempre e solo ai dati di occupazione registrati in locale.**

| Cartella | Descrizione |
| --- | --- |
| `bot/` | Codice del bot Telegram (`config.py` raccoglie tutte le costanti, `db/` l'accesso al database) |
| `jobs/` | Script per scaricare i dati di occupazione e le foto delle aule |
| `sql/` | Schema del database e raccolta di query utili |
| `data/` | Foto delle aule e varie |
| `misc/` | File vari e script di supporto |


## Sviluppo in locale <a name = "developement"></a>

### Prerequisiti

- [uv](https://docs.astral.sh/uv/)
- [postgres](https://www.postgresql.org/)

### Configurazione

Crea un file `.env` nella root del progetto:

```env
BOT_TOKEN=<bot_token>
PGHOST=localhost
PGPORT=5432
PGDATABASE=postgres
PGUSER=postgres
PGPASSWORD=postgres
```

### Installazione e avvio

#### Installazione delle dipendenze
```sh
uv sync
```

#### Download elenco aule, piani, sedi, ecc...
```sh
uv run jobs/spazi/1_spazi.py
```

#### Download elenco delle dotazioni per aula (prese elettriche e di rete)
```sh
uv run jobs/spazi/2_dotazioni.py --workers 6
```

#### Download foto delle aule (opzionale)
```sh
uv run jobs/spazi/3_foto.py
```

#### Download delle fasce orarie di occupazione per i prossimi 7 giorni
```sh
uv run jobs/spazi/4_occupazione.py --giorni 7 --workers 6
```

#### Download nomi di corso per le fasce orarie di occupazione (arricchisce i dati scaricati dallo script precedente)
```sh
uv run jobs/spazi/5_arricchisci_occupazione.py --giorni 7 --workers 6
```

#### Avvio del bot
```sh
uv run bot/main.py
```

---

## Database

Il database PostgreSQL è strutturato attorno alla gerarchia degli spazi fisici del Politecnico a cui si aggiungono tabelle per la gestione delle occupazioni e delle preferenze utente.

### Gerarchia spaziale

```
polo → sede → campus → edificio → piano → aula
```

| Tabella | Chiave | Descrizione |
| --- | --- | --- |
| `polo` | `csim` | Polo universitario (es. Milano, Lecco) |
| `sede` | `csis` | Sede dentro un polo |
| `campus` | `csic` | Campus dentro una sede |
| `edificio` | `csie` | Edificio con indirizzo, ente gestore, ecc. |
| `piano` | `csip` | Piano dell'edificio |
| `aula` | `idaula` | Aula con capienza, categoria, tipologia, dotazioni |

### Dotazioni aule

| Tabella | Descrizione |
| --- | --- |
| `tipo_dotazione` | Catalogo attrezzature (nome IT/EN) |
| `aula_dotazione` | Relazione M:N tra aula e dotazioni |

### Occupazioni

| Tabella | Descrizione |
| --- | --- |
| `occupazione_giorno` | Registra per quale aula e giorno sono stati scaricati i dati |
| `occupazione_slot` | Fasce orarie occupate per quel giorno (`inizio`, `fine`) |

### Utenti

| Tabella | Descrizione |
| --- | --- |
| `user_preference` | Preferenze utente Telegram: sede e lingua |
| `user_favourite` | Aule preferite per utente (max 50, `MAX_PREFERITI` in `bot/config.py`) |
| `report` | Segnalazioni anonime: solo testo e data di invio |
| `activity_log` | Statistiche d'uso anonime: azione, parametri e timestamp, senza alcun identificativo utente |


## Notes

### Tipologie e categorie aule

#### Tipologia

| Tag | Descrizione |
| --- | --- |
| `F` | PLATEA FRONTALE |
| `D` | DISEGNO |
| `A` | ALTRO |
| `N` | INFORMATIZZATA |
| `S` | STUDIO INDIVIDUALE |

#### Categoria

| Tag | Descrizione |
| --- | --- |
| `M` | AULA MAGNA |
| `L` | LABORATORIO |
| `D` | AULA DIDATTICA |
| `A` | AULA STUDIO |
| `C` | AULA CONVEGNI |
| `P` | AULA DIPARTIMENTALE |

---

## Systemd Bot Service

Creazione dell'utente

```sh
sudo useradd --system --no-create-home --shell /usr/sbin/nologin polimibot
sudo mkdir -p /home/polimibot
sudo chown -R polimibot:polimibot /opt/polimibot
sudo usermod -s /bin/bash polimibot

sudo mkdir -p /opt/polimibot
sudo chown polimibot:polimibot /home/polimibot
```

Accedere alla shell dell'utente

```sh
sudo -u polimibot bash -l
```

Installzione di uv e clonazione del repository

```sh
TODO - installazione uv e clone del repo
```

Creazione del servizio e abilitazione

```sh
sudo cp polimibot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now polimibot
```

Comandi utili di gestione

```sh
systemctl status polimibot        # stato
journalctl -u polimibot -f        # log in tempo reale
systemctl restart polimibot       # riavvia
systemctl stop polimibot          # ferma
```

Log del servizio

```sh
# Follow live logs
journalctl -u myservice -f

# Last 100 lines
journalctl -u myservice -n 100

# Since a specific time
journalctl -u myservice --since "2024-01-01 10:00" --until "2024-01-01 11:00"

# Since boot
journalctl -u myservice -b

# Only errors
journalctl -u myservice -p err

# Without pager (plain output)
journalctl -u myservice --no-pager
```


Servizio

```bash
# /etc/systemd/system/polimibot.service
#
# Deploy:
#   sudo cp polimibot.service /etc/systemd/system/
#   sudo systemctl daemon-reload
#   sudo systemctl enable --now polimibot

[Unit]
Description=Aule Libere Polimi (Telegram Bot)
After=network.target

[Service]
Type=simple
User=polimibot
Group=polimibot

WorkingDirectory=/opt/polimibot/
ExecStart=uv run bot/main.py
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target

```



