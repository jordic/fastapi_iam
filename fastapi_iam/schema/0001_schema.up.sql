-- drop schema demo cascade;
-- create schema demo;
-- set schema 'demo';


create type auth_types as ENUM
    ('password', 'provider', 'service-token');


CREATE TABLE IF NOT EXISTS users (
    user_id serial primary key,
    email character varying(254) NOT NULL,
    password character varying(128) NOT NULL,
    username character varying(254) NOT NULL default 'noname',
    is_staff boolean NOT NULL default false,
    is_active boolean NOT NULL default false,
    is_admin boolean NOT NULL default false,
    date_joined timestamp without time zone NOT NULL default now(),
    last_login timestamp without time zone,
    auth_type auth_types NOT NULL default 'password',
    auth_provider varchar,
    props jsonb default '{}'::jsonb,
    UNIQUE (email),
);

CREATE TABLE users_keys (
    id serial primary key,
    user_id integer references users(user_id),
    public_key varchar not null,
    last_used timestamp without time zone,
    comment varchar,
    enabled boolean
);


CREATE type token_type AS ENUM ('register', 'forgot', 'authemail');

CREATE TABLE users_token (
    user_id integer references users(user_id),
    token varchar(32),
    expires timestamp without time zone,
    token_type token_type not null
);

CREATE INDEX users_token_idx on
    users_token using btree(token);


CREATE type ticket_type AS ENUM ('service_token', 'user_token');


CREATE TABLE users_authticket (
    user_id integer references users(user_id),
    token varchar not null,
    expires timestamp without time zone default now() + '30m'::interval,
    refresh_token varchar,
    refresh_token_expires timestamp without time zone
        default now() + '7d'::interval,
    token_type ticket_type default 'user_token'
);


CREATE INDEX users_authticket_idx on
    users_authticket using btree(token);

CREATE INDEX users_authticket_refresh_idx on
    users_authticket using btree(refresh_token);

CREATE TABLE groups (
    group_id serial primary key,
    name character varying(150) NOT NULL,
    unique(name)
);


CREATE TABLE users_group (
    id serial primary key,
    user_id integer references users(user_id),
    group_id integer references groups(group_id) ON DELETE CASCADE,
    UNIQUE (user_id, group_id)
);

create table users_version (
    value integer
);
insert into users_version values (0);


CREATE OR REPLACE FUNCTION trigger_fix_username()
    RETURNS trigger LANGUAGE plpgsql as $$
BEGIN
    new.username = lower(new.username);
    new.email = lower(new.email);
    RETURN new;
END;
$$;

CREATE TRIGGER trigger_updateusers BEFORE
        INSERT OR UPDATE ON users
    FOR EACH ROW EXECUTE PROCEDURE trigger_fix_username();


CREATE or replace function update_groups(v_groups varchar[], v_user_id integer)
    RETURNS varchar[] as $$
DECLARE
    g_id integer;
BEGIN
    DELETE from users_group where user_id=v_user_id;
    FOR g_id in
        SELECT group_id from groups
            where name = ANY(v_groups) LOOP
        EXECUTE 'INSERT INTO users_group VALUES (default, $1, $2)'
                USING v_user_id, g_id;
    END LOOP;
    RETURN v_groups;
END;
$$ LANGUAGE plpgsql;
