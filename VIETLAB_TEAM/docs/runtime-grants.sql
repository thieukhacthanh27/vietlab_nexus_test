-- Run as schema owner after `python -m app.manage init-db`.
-- Before running: create LOGIN role vl_runtime using an interactive administrator tool
-- with a unique password; never store a real password in this file.
GRANT CONNECT ON DATABASE vietlab TO vl_runtime;
GRANT USAGE ON SCHEMA public TO vl_runtime;
GRANT SELECT, INSERT, UPDATE ON users, methods, samples, tasks TO vl_runtime;
GRANT SELECT, INSERT, DELETE ON sessions, login_attempts TO vl_runtime;
GRANT SELECT, INSERT ON audit, reports TO vl_runtime;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO vl_runtime;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
-- Application role cannot UPDATE / DELETE reports or audit entries.
-- Database owner/superuser still can: external backups and controlled DBA access remain necessary.
