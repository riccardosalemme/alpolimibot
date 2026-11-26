-- ------------------------------------------------------------------
-- Inserimento delle 3 biblioteche principali
-- ------------------------------------------------------------------
INSERT INTO affluences_sites (affluences_id, name, slug)
VALUES
    ('352d189c-4811-46c1-8da4-705bb42b73f1', 'Biblioteca Bovisa La Masa - Politecnico di Milano', 'biblioteca-bovisa-la-masa'),
    ('208fb078-ca07-4908-8136-3e9c1ba71031', 'Biblioteca Bovisa Candiani - Politecnico di Milano', 'biblioteca-bovisa-candiani'),
    ('334eec6e-69c5-4ef8-b645-5f3085009fb5', 'Biblioteca Campus Leonardo - Politecnico di Milano', 'biblioteca-campus-leonardo')
ON CONFLICT (affluences_id)
DO UPDATE SET
    name = EXCLUDED.name,
    slug = EXCLUDED.slug;


-- ------------------------------------------------------------------
-- Aule nascoste (spazi normalmente non accessibili dagli studenti)
-- ------------------------------------------------------------------

-- Elenco delle aule
-- SELECT sigla, visible, sort, *
-- FROM public.aula
-- where visible = false
-- order by sigla;

UPDATE aula
SET visible = false
WHERE sigla ILIKE ANY (ARRAY[
	'%LAB%',
	'%RIUNIONI%',
	'%AULA DIPARTIMENTALE%',
	'%AULA FASSO%',
	'%AULA INFORMATIZZATA%',
	'%AULA MAGNA%',
	'%EDUCAFE%',
	'%ROGERS%',
	'%SPAZIO LAVORO STUDENTI%',
	-- '%G.0.1%',
	-- '%G.0.2%',
	-- '%A.0.2%',
	'%MEL LAB%'
]);

-- Aule solo prenotabili: nascoste dai risultati, ma trovabili cercandole per sigla.
update aula
set visible = false
where idaula in (
	726,  -- G.1
	2012  -- G.2
);


-- ------------------------------------------------------------------
-- Nomi personalizzati (il job 1_spazi.py non li sovrascrive)
-- ------------------------------------------------------------------

-- '2.2.5 - VIRTUAL LAB': va dopo il blocco '%LAB%', perché deve restare visibile.
update aula
set nome = '2.2.5', visible = true
where idaula = 2328;

-- 'A - ALDO ROSSI', come le aule B, C, D...
update aula
set nome = 'A'
where idaula = 721;

-- Le aule del trifoglio vengono messe in cima.
update aula
set sort = 2
where sigla like '%T.%';


-- ------------------------------------------------------------------
-- Sedi abilitate
-- ------------------------------------------------------------------
update sede
set show = true
where nome ILIKE ANY (ARRAY[
	'%Milano Bovisa%',
	'%Milano Città Studi%',
	'%Como%',
	'%Cremona%'
]);
