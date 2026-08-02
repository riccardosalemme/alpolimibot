-- -----------------------------------------------------------
-- POLO
-- -----------------------------------------------------------
CREATE TABLE polo (
    csim        CHAR(2)         PRIMARY KEY,
    nome        VARCHAR(100)    NOT NULL,
    visibile    CHAR(1)         NOT NULL DEFAULT 'S' CHECK (visibile IN ('S', 'N'))
);

-- -----------------------------------------------------------
-- SEDE
-- -----------------------------------------------------------
CREATE TABLE sede (
    csis        CHAR(3)         PRIMARY KEY,
    csim        CHAR(2)         NOT NULL REFERENCES polo(csim) ON DELETE CASCADE,
    nome        VARCHAR(100)    NOT NULL,
    visibile    CHAR(1)         NOT NULL DEFAULT 'S' CHECK (visibile IN ('S', 'N')),
    show        BOOLEAN         NOT NULL DEFAULT FALSE -- aggiunto io per il bot
);

-- -----------------------------------------------------------
-- CAMPUS
-- -----------------------------------------------------------
CREATE TABLE campus (
    csic        CHAR(5)         PRIMARY KEY,
    csis        CHAR(3)         NOT NULL REFERENCES sede(csis) ON DELETE CASCADE,
    nome        VARCHAR(100)    NOT NULL,
    visibile    CHAR(1)         NOT NULL DEFAULT 'S' CHECK (visibile IN ('S', 'N'))
);

-- -----------------------------------------------------------
-- EDIFICIO
-- -----------------------------------------------------------
CREATE TABLE edificio (
    csie                    CHAR(7)         PRIMARY KEY,
    csic                    CHAR(5)         NOT NULL REFERENCES campus(csic) ON DELETE CASCADE,
    nome                    VARCHAR(100)    NOT NULL,
    id_edificio             INTEGER, -- la api restituisce una string
    id_campus               INTEGER, -- la api restituisce una stringa
    indirizzo               VARCHAR(150),
    cap                     CHAR(5),
    provincia               CHAR(2),
    citta_edificio          VARCHAR(100),
    nome_storico            VARCHAR(150),
    -- ente_gestore            VARCHAR(150), -- è sempre il poli, scritto in 3 forme diverse (Politecnico di MIlano, Politecnico, Politecnico di Milano)
    ente_proprietario       VARCHAR(150),
    titolo_godimento        VARCHAR(150),
    note_accesso_disabili   TEXT,
    note_accesso            TEXT,
    prefisso_toponomastico  VARCHAR(20),
    numero_civico           VARCHAR(10),
    -- etichetta_mappa         VARCHAR(50),
    visibile                CHAR(1)         NOT NULL DEFAULT 'S' CHECK (visibile IN ('S', 'N')),
    anno_costruzione        INTEGER, -- restituisce -2147483648 per null
    anno_attivazione        INTEGER -- //
);

-- -----------------------------------------------------------
-- PIANO
-- -----------------------------------------------------------
CREATE TABLE piano (
    csip        CHAR(10)         PRIMARY KEY,
    csie        CHAR(7)     NOT NULL REFERENCES edificio(csie) ON DELETE CASCADE,
    nome        VARCHAR(50)     NOT NULL,
    n           INTEGER, -- la api restituisce una stringa
    visibile    CHAR(1)         NOT NULL DEFAULT 'S' CHECK (visibile IN ('S', 'N'))
);

-- -----------------------------------------------------------
-- AULA
-- -----------------------------------------------------------
CREATE TABLE aula (
    idaula                      INTEGER        PRIMARY KEY,
    sigla                       VARCHAR(50),
    csiv                        VARCHAR(30),
    csip                        CHAR(10)       REFERENCES piano(csip) ON DELETE SET NULL,
    csie                        CHAR(7)        REFERENCES edificio(csie) ON DELETE SET NULL,
    csis                        CHAR(3)        REFERENCES sede(csis) ON DELETE SET NULL, -- per trovare facilmente le aule delle rispettive sedi
    id_vano                     INTEGER,
    -- handle                      VARCHAR(50), -- è sempre null
    esterna                     CHAR(1)      CHECK (esterna IN ('S', 'N')),
    indir_esterna               VARCHAR(200),
    ubicazione_esterna          VARCHAR(200),
    -- c_istituto                  VARCHAR(20), -- 0 o null poco rilevante
    -- tipo_istituto               VARCHAR(50), -- sempre null
    note                        TEXT,
    uso_test                    CHAR(1)      CHECK (uso_test IN ('S', 'N')),
    -- fittizia                    CHAR(1)      CHECK (fittizia IN ('S', 'N')), -- sono tutte N (non fittizie)
    -- conferma_ate                CHAR(1)      CHECK (conferma_ate IN ('S', 'N')), -- sono tutte S
    capienza_ate                INTEGER,
    morfologia                  CHAR(1),
    posti_disabili              INTEGER,
    idfoto                      INTEGER,
    -- datafoto                    TIMESTAMP, -- sono tutte null
    numero_postazioni_attive    INTEGER,
    capienza                    INTEGER,
    competenza                  CHAR(3),
    -- denominazione               VARCHAR(150), compilato solo per aule A. e uguale alla sigla
    categoria                   CHAR(1), -- M L A D C P
    tipologia                   CHAR(1), -- F D A N S
    attivazione                 TIMESTAMP,
    -- disattivazione              TIMESTAMP, -- è sempre null, è stato probabilmente previsto per il futuro
    numero_postazioni           INTEGER,
    -- tipo_postazioni             VARCHAR(50), -- è sempre null
    descrizione                 TEXT,

    has_power_sockets           BOOLEAN      NOT NULL DEFAULT FALSE, -- salvo qui per ottimizzare
    has_network_sockets         BOOLEAN      NOT NULL DEFAULT FALSE, -- //
    visible                     BOOLEAN      NOT NULL DEFAULT TRUE, -- per il bot
    sort                        INTEGER      NOT NULL DEFAULT 0 -- per il bot
);

-- -----------------------------------------------------------
-- TIPO_DOTAZIONE
-- -----------------------------------------------------------
CREATE TABLE tipo_dotazione (
    id      INTEGER      PRIMARY KEY,
    it      VARCHAR(150) NOT NULL,
    en      VARCHAR(150) NOT NULL
);

-- -----------------------------------------------------------
-- AULA_DOTAZIONE  (M:N  aula ↔ tipo_dotazione)
-- -----------------------------------------------------------
CREATE TABLE aula_dotazione (
    idaula              INTEGER  NOT NULL REFERENCES aula(idaula)        ON DELETE CASCADE,
    id_tipo_dotazione   INTEGER  NOT NULL REFERENCES tipo_dotazione(id)  ON DELETE CASCADE,
    PRIMARY KEY (idaula, id_tipo_dotazione)
);

-- -----------------------------------------------------------
-- OCCUPAZIONE_GIORNO  (un record per aula × giorno scaricato)
-- -----------------------------------------------------------
CREATE TABLE occupazione_giorno (
    id              SERIAL      PRIMARY KEY,
    idaula          INTEGER     NOT NULL REFERENCES aula(idaula) ON DELETE CASCADE,
    data            DATE        NOT NULL,
    scaricato_il    TIMESTAMP   NOT NULL DEFAULT NOW(),
    UNIQUE (idaula, data)
);

-- -----------------------------------------------------------
-- OCCUPAZIONE_SLOT  (fasce orarie occupate per quel giorno)
-- -----------------------------------------------------------
CREATE TABLE occupazione_slot (
    id          SERIAL      PRIMARY KEY,
    id_giorno   INTEGER     NOT NULL REFERENCES occupazione_giorno(id) ON DELETE CASCADE,
    inizio      TIME        NOT NULL,
    fine        TIME        NOT NULL,
    corso       VARCHAR(500),
    UNIQUE (id_giorno, inizio)
);

-- -----------------------------------------------------------
-- USER_PREFERENCE
-- -----------------------------------------------------------
CREATE TABLE user_preference (
    user_id         BIGINT          PRIMARY KEY,
    sede_name       VARCHAR(100),
    sede_csis       VARCHAR(10),
    language        CHAR(2)         NOT NULL DEFAULT 'it',
    aggiornato_il   TIMESTAMP       NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------
-- USER_FAVOURITE  (aule preferite)
-- -----------------------------------------------------------
CREATE TABLE user_favourite (
    user_id         BIGINT      NOT NULL,
    idaula          INTEGER     NOT NULL REFERENCES aula(idaula) ON DELETE CASCADE,
    aggiunto_il     TIMESTAMP   NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, idaula)
);

-- -----------------------------------------------------------
-- REPORT  (anonimo)
-- -----------------------------------------------------------
CREATE TABLE report (
    id              SERIAL      PRIMARY KEY,
    messaggio       TEXT        NOT NULL,
    inviato_il      TIMESTAMP   NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------
-- Log attività (anonimo)
-- -----------------------------------------------------------
CREATE TABLE activity_log (
    id          BIGSERIAL   PRIMARY KEY,
    ts          TIMESTAMP   NOT NULL DEFAULT NOW(),
    action      TEXT        NOT NULL,
    sede_csis   VARCHAR(10),        -- /now, /search, settings_sede
    idaula      INTEGER,            -- dettaglio_aula, occupazione_settimana
    sigla       VARCHAR(50),        -- cerca_aula (testo libero, troncato)
    giorno      DATE,               -- /now, /search
    ora_inizio  TIME,               -- /now, /search
    ora_fine    TIME,               -- /now, /search
    language    CHAR(2)             -- settings_language
);


-- -----------------------------------------------------------
-- Affluences Sites (biblioteche)
-- -----------------------------------------------------------
CREATE TABLE affluences_sites (
    id SERIAL PRIMARY KEY,
    affluences_id UUID UNIQUE NOT NULL,
    name TEXT,
    slug TEXT NOT NULL
);

-- -----------------------------------------------------------
-- Affluences Occupancies
-- -----------------------------------------------------------
CREATE TABLE affluences_occupancies (
    id SERIAL PRIMARY KEY,
    site_id INTEGER REFERENCES affluences_sites(id),
    is_open BOOLEAN,
    occupancy_percent INTEGER,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_affluences_occupancies_site_date ON affluences_occupancies(site_id, fetched_at);


-- -----------------------------------------------------------
-- INDICI
-- -----------------------------------------------------------
CREATE INDEX ON activity_log (action);
CREATE INDEX ON activity_log (ts);
CREATE INDEX ON activity_log (sede_csis) WHERE sede_csis IS NOT NULL;
CREATE INDEX ON activity_log (idaula)    WHERE idaula    IS NOT NULL;

CREATE INDEX idx_sede_csim              ON sede(csim);
CREATE INDEX idx_campus_csis            ON campus(csis);
CREATE INDEX idx_edificio_csic          ON edificio(csic);
CREATE INDEX idx_piano_csie             ON piano(csie);
CREATE INDEX idx_aula_csip              ON aula(csip);
CREATE INDEX idx_aula_csie              ON aula(csie);
CREATE INDEX idx_aula_dotazione_idaula  ON aula_dotazione(idaula);
CREATE INDEX idx_aula_dotazione_tipo    ON aula_dotazione(id_tipo_dotazione);
CREATE INDEX idx_aula_visible           ON aula(visible) WHERE visible = TRUE;
CREATE INDEX idx_occ_giorno_data_aula   ON occupazione_giorno(data, idaula);
CREATE INDEX idx_occ_giorno_aula_data   ON occupazione_giorno(idaula, data);
CREATE INDEX idx_occ_slot_giorno        ON occupazione_slot(id_giorno);
CREATE INDEX idx_report_inviato_il      ON report(inviato_il);
