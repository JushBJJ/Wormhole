--
-- PostgreSQL database dump
--

-- Dumped from database version 16.4 (Debian 16.4-1.pgdg120+1)
-- Dumped by pg_dump version 16.4 (Debian 16.4-1.pgdg120+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: admins; Type: TABLE; Schema: public; Owner: jushbjj
--

CREATE TABLE public.admins (
    user_id character varying(255) NOT NULL
);


ALTER TABLE public.admins OWNER TO jushbjj;

--
-- Name: attachmenthistory; Type: TABLE; Schema: public; Owner: jushbjj
--

CREATE TABLE public.attachmenthistory (
    hash character varying(255) NOT NULL,
    attachment_link character varying(255),
    user_id character varying(255),
    "timestamp" double precision NOT NULL
);


ALTER TABLE public.attachmenthistory OWNER TO jushbjj;

--
-- Name: bannedservers; Type: TABLE; Schema: public; Owner: jushbjj
--

CREATE TABLE public.bannedservers (
    server_id integer NOT NULL
);


ALTER TABLE public.bannedservers OWNER TO jushbjj;

--
-- Name: bannedusers; Type: TABLE; Schema: public; Owner: jushbjj
--

CREATE TABLE public.bannedusers (
    user_id character varying(255) NOT NULL
);


ALTER TABLE public.bannedusers OWNER TO jushbjj;

--
-- Name: channellist; Type: TABLE; Schema: public; Owner: jushbjj
--

CREATE TABLE public.channellist (
    channel_name character varying(255) NOT NULL
);


ALTER TABLE public.channellist OWNER TO jushbjj;

--
-- Name: channels; Type: TABLE; Schema: public; Owner: jushbjj
--

CREATE TABLE public.channels (
    channel_id character varying(255) NOT NULL,
    server_id character varying(255) NOT NULL,
    channel_category character varying(255) NOT NULL,
    react boolean DEFAULT false
);


ALTER TABLE public.channels OWNER TO jushbjj;

--
-- Name: dataset; Type: TABLE; Schema: public; Owner: jushbjj
--

CREATE TABLE public.dataset (
    id character varying(255) NOT NULL,
    predicted text,
    actual text
);


ALTER TABLE public.dataset OWNER TO jushbjj;

--
-- Name: messagehistory; Type: TABLE; Schema: public; Owner: jushbjj
--

CREATE TABLE public.messagehistory (
    hash character varying(255) NOT NULL,
    message_link character varying(255)[],
    user_id character varying(255),
    "timestamp" double precision NOT NULL
);


ALTER TABLE public.messagehistory OWNER TO jushbjj;

--
-- Name: roles; Type: TABLE; Schema: public; Owner: jushbjj
--

CREATE TABLE public.roles (
    name character varying(50) NOT NULL,
    color character varying(7) NOT NULL
);


ALTER TABLE public.roles OWNER TO jushbjj;

--
-- Name: servers; Type: TABLE; Schema: public; Owner: jushbjj
--

CREATE TABLE public.servers (
    server_id integer NOT NULL,
    server_name character varying(255) NOT NULL
);


ALTER TABLE public.servers OWNER TO jushbjj;

--
-- Name: tempcommandmessagehistory; Type: TABLE; Schema: public; Owner: jushbjj
--

CREATE TABLE public.tempcommandmessagehistory (
    message_id integer NOT NULL,
    user_id character varying(255),
    content text NOT NULL
);


ALTER TABLE public.tempcommandmessagehistory OWNER TO jushbjj;

--
-- Name: tempcommandmessagehistory_message_id_seq; Type: SEQUENCE; Schema: public; Owner: jushbjj
--

CREATE SEQUENCE public.tempcommandmessagehistory_message_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tempcommandmessagehistory_message_id_seq OWNER TO jushbjj;

--
-- Name: tempcommandmessagehistory_message_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jushbjj
--

ALTER SEQUENCE public.tempcommandmessagehistory_message_id_seq OWNED BY public.tempcommandmessagehistory.message_id;


--
-- Name: usernames; Type: TABLE; Schema: public; Owner: jushbjj
--

CREATE TABLE public.usernames (
    user_id character varying(255) NOT NULL,
    name character varying(255),
    id integer NOT NULL
);


ALTER TABLE public.usernames OWNER TO jushbjj;

--
-- Name: usernames_id_seq; Type: SEQUENCE; Schema: public; Owner: jushbjj
--

CREATE SEQUENCE public.usernames_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.usernames_id_seq OWNER TO jushbjj;

--
-- Name: usernames_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jushbjj
--

ALTER SEQUENCE public.usernames_id_seq OWNED BY public.usernames.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: jushbjj
--

CREATE TABLE public.users (
    hash character varying(255) NOT NULL,
    user_id character varying(255) DEFAULT '0'::character varying,
    role character varying(50) DEFAULT 'user'::character varying,
    profile_picture character varying(255),
    difficulty double precision DEFAULT 0,
    difficulty_penalty double precision DEFAULT 0,
    can_send_message boolean DEFAULT true,
    nonce integer DEFAULT 0
);


ALTER TABLE public.users OWNER TO jushbjj;

--
-- Name: tempcommandmessagehistory message_id; Type: DEFAULT; Schema: public; Owner: jushbjj
--

ALTER TABLE ONLY public.tempcommandmessagehistory ALTER COLUMN message_id SET DEFAULT nextval('public.tempcommandmessagehistory_message_id_seq'::regclass);


--
-- Name: usernames id; Type: DEFAULT; Schema: public; Owner: jushbjj
--

ALTER TABLE ONLY public.usernames ALTER COLUMN id SET DEFAULT nextval('public.usernames_id_seq'::regclass);


--
-- Name: admins admins_pkey; Type: CONSTRAINT; Schema: public; Owner: jushbjj
--

ALTER TABLE ONLY public.admins
    ADD CONSTRAINT admins_pkey PRIMARY KEY (user_id);


--
-- Name: attachmenthistory attachmenthistory_pkey; Type: CONSTRAINT; Schema: public; Owner: jushbjj
--

ALTER TABLE ONLY public.attachmenthistory
    ADD CONSTRAINT attachmenthistory_pkey PRIMARY KEY (hash);


--
-- Name: bannedservers bannedservers_pkey; Type: CONSTRAINT; Schema: public; Owner: jushbjj
--

ALTER TABLE ONLY public.bannedservers
    ADD CONSTRAINT bannedservers_pkey PRIMARY KEY (server_id);


--
-- Name: bannedusers bannedusers_pkey; Type: CONSTRAINT; Schema: public; Owner: jushbjj
--

ALTER TABLE ONLY public.bannedusers
    ADD CONSTRAINT bannedusers_pkey PRIMARY KEY (user_id);


--
-- Name: channellist channellist_pkey; Type: CONSTRAINT; Schema: public; Owner: jushbjj
--

ALTER TABLE ONLY public.channellist
    ADD CONSTRAINT channellist_pkey PRIMARY KEY (channel_name);


--
-- Name: channels channels_pkey; Type: CONSTRAINT; Schema: public; Owner: jushbjj
--

ALTER TABLE ONLY public.channels
    ADD CONSTRAINT channels_pkey PRIMARY KEY (channel_id);


--
-- Name: dataset dataset_pkey; Type: CONSTRAINT; Schema: public; Owner: jushbjj
--

ALTER TABLE ONLY public.dataset
    ADD CONSTRAINT dataset_pkey PRIMARY KEY (id);


--
-- Name: messagehistory messagehistory_pkey; Type: CONSTRAINT; Schema: public; Owner: jushbjj
--

ALTER TABLE ONLY public.messagehistory
    ADD CONSTRAINT messagehistory_pkey PRIMARY KEY (hash);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: jushbjj
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (name);


--
-- Name: servers servers_pkey; Type: CONSTRAINT; Schema: public; Owner: jushbjj
--

ALTER TABLE ONLY public.servers
    ADD CONSTRAINT servers_pkey PRIMARY KEY (server_id);


--
-- Name: tempcommandmessagehistory tempcommandmessagehistory_pkey; Type: CONSTRAINT; Schema: public; Owner: jushbjj
--

ALTER TABLE ONLY public.tempcommandmessagehistory
    ADD CONSTRAINT tempcommandmessagehistory_pkey PRIMARY KEY (message_id);


--
-- Name: usernames unique_user_id_name; Type: CONSTRAINT; Schema: public; Owner: jushbjj
--

ALTER TABLE ONLY public.usernames
    ADD CONSTRAINT unique_user_id_name UNIQUE (user_id, name);


--
-- Name: usernames usernames_pkey; Type: CONSTRAINT; Schema: public; Owner: jushbjj
--

ALTER TABLE ONLY public.usernames
    ADD CONSTRAINT usernames_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: jushbjj
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (hash);


--
-- Name: users users_user_id_key; Type: CONSTRAINT; Schema: public; Owner: jushbjj
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_user_id_key UNIQUE (user_id);


--
-- Name: admins admins_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jushbjj
--

ALTER TABLE ONLY public.admins
    ADD CONSTRAINT admins_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: attachmenthistory attachmenthistory_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jushbjj
--

ALTER TABLE ONLY public.attachmenthistory
    ADD CONSTRAINT attachmenthistory_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: messagehistory messagehistory_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jushbjj
--

ALTER TABLE ONLY public.messagehistory
    ADD CONSTRAINT messagehistory_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: tempcommandmessagehistory tempcommandmessagehistory_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jushbjj
--

ALTER TABLE ONLY public.tempcommandmessagehistory
    ADD CONSTRAINT tempcommandmessagehistory_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: usernames usernames_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jushbjj
--

ALTER TABLE ONLY public.usernames
    ADD CONSTRAINT usernames_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

-- Insert default roles
INSERT INTO Roles (name, color) VALUES 
('admin', '#FF0000'),
('user', '#0000FF')
ON CONFLICT (name) DO NOTHING;

-- Insert default channel names
INSERT INTO ChannelList (channel_name) VALUES 
('general'), 
('wormhole'), 
('happenings'), 
('qotd'), 
('memes'), 
('computers'), 
('finance'), 
('music'), 
('cats'), 
('spam-can'), 
('test')
ON CONFLICT (channel_name) DO NOTHING;