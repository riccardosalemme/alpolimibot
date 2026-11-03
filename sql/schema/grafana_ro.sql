SELECT format('CREATE ROLE grafana_ro LOGIN PASSWORD %L', :'pw')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'grafana_ro') \gexec
ALTER ROLE grafana_ro PASSWORD :'pw';
GRANT USAGE ON SCHEMA public TO grafana_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO grafana_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO grafana_ro;
