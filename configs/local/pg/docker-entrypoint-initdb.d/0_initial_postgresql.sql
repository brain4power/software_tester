-- PostgreSQL

CREATE DATABASE app_core
    WITH OWNER = app_user
    ENCODING = 'UTF8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1
    LC_COLLATE ='en_US.UTF-8'
    LC_CTYPE ='en_US.UTF-8'
    TEMPLATE template0;

\c app_core
CREATE EXTENSION pgcrypto;