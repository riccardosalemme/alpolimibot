-- -----------------------------------------------------------
-- REPORT: flag per segnare le segnalazioni già gestite
-- -----------------------------------------------------------
ALTER TABLE report ADD COLUMN IF NOT EXISTS gestito BOOLEAN NOT NULL DEFAULT FALSE;


-- -----------------------------------------------------------
-- AULA: nome mostrato dal bot (di default uguale alla sigla)
-- -----------------------------------------------------------
ALTER TABLE aula ADD COLUMN IF NOT EXISTS nome VARCHAR(50);

UPDATE aula
SET nome = sigla
WHERE nome IS NULL;
