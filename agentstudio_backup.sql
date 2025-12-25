--
-- PostgreSQL database dump
--

\restrict E500vfthbQiXyAdyIWd1rR9RAEF484ja7KaJJZhtHNwplJreV2DiwAqAqTXaekz

-- Dumped from database version 15.15
-- Dumped by pg_dump version 15.15

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

--
-- Name: agentstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.agentstatus AS ENUM (
    'DRAFT',
    'DEPLOYED',
    'ARCHIVED'
);


ALTER TYPE public.agentstatus OWNER TO postgres;

--
-- Name: credentialprovider; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.credentialprovider AS ENUM (
    'openai',
    'anthropic',
    'google',
    'azure_openai',
    'custom',
    'redis',
    'postgresql',
    'mongodb'
);


ALTER TYPE public.credentialprovider OWNER TO postgres;

--
-- Name: deploymentenvironment; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.deploymentenvironment AS ENUM (
    'DEVELOPMENT',
    'STAGING',
    'PRODUCTION'
);


ALTER TYPE public.deploymentenvironment OWNER TO postgres;

--
-- Name: deploymentstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.deploymentstatus AS ENUM (
    'PENDING',
    'DEPLOYING',
    'ACTIVE',
    'FAILED',
    'STOPPED'
);


ALTER TYPE public.deploymentstatus OWNER TO postgres;

--
-- Name: toolstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.toolstatus AS ENUM (
    'ACTIVE',
    'DEPRECATED'
);


ALTER TYPE public.toolstatus OWNER TO postgres;

--
-- Name: tooltype; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.tooltype AS ENUM (
    'BUILT_IN',
    'API',
    'CUSTOM',
    'mcp'
);


ALTER TYPE public.tooltype OWNER TO postgres;

--
-- Name: toolvisibility; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.toolvisibility AS ENUM (
    'PUBLIC',
    'PRIVATE',
    'ORGANIZATION'
);


ALTER TYPE public.toolvisibility OWNER TO postgres;

--
-- Name: userrole; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.userrole AS ENUM (
    'ADMIN',
    'CREATOR',
    'VIEWER'
);


ALTER TYPE public.userrole OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: agent_executions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.agent_executions (
    id uuid NOT NULL,
    agent_id uuid NOT NULL,
    user_id uuid NOT NULL,
    input json NOT NULL,
    output json,
    tokens_used integer DEFAULT 0 NOT NULL,
    execution_time integer,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.agent_executions OWNER TO postgres;

--
-- Name: agent_versions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.agent_versions (
    id uuid NOT NULL,
    agent_id uuid NOT NULL,
    version_number integer NOT NULL,
    version_tag character varying,
    config json NOT NULL,
    description character varying,
    changelog text,
    created_by uuid NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.agent_versions OWNER TO postgres;

--
-- Name: agents; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.agents (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    creator_id uuid NOT NULL,
    name character varying NOT NULL,
    description character varying,
    config json NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    status public.agentstatus DEFAULT 'DRAFT'::public.agentstatus NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    is_template boolean DEFAULT false NOT NULL,
    is_public_template boolean DEFAULT false NOT NULL,
    template_source_id uuid,
    tags jsonb DEFAULT '[]'::jsonb,
    metadata jsonb DEFAULT '{}'::jsonb,
    deleted_at timestamp without time zone
);


ALTER TABLE public.agents OWNER TO postgres;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.audit_logs (
    id uuid NOT NULL,
    organization_id uuid,
    user_id uuid,
    user_email character varying(255),
    action character varying(100) NOT NULL,
    resource_type character varying(50) NOT NULL,
    resource_id character varying(100),
    resource_name character varying(255),
    old_values jsonb,
    new_values jsonb,
    ip_address inet,
    user_agent text,
    request_id character varying(100),
    metadata jsonb DEFAULT '{}'::jsonb,
    status character varying(20) DEFAULT 'success'::character varying,
    error_message text,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.audit_logs OWNER TO postgres;

--
-- Name: credentials; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.credentials (
    id character varying NOT NULL,
    user_id uuid NOT NULL,
    organization_id uuid NOT NULL,
    name character varying NOT NULL,
    provider public.credentialprovider NOT NULL,
    api_key character varying NOT NULL,
    api_base character varying,
    api_version character varying,
    organization_key character varying,
    is_active character varying DEFAULT 'active'::character varying,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    last_used_at timestamp without time zone
);


ALTER TABLE public.credentials OWNER TO postgres;

--
-- Name: deployments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.deployments (
    id uuid NOT NULL,
    agent_id uuid NOT NULL,
    version character varying NOT NULL,
    environment public.deploymentenvironment DEFAULT 'DEVELOPMENT'::public.deploymentenvironment NOT NULL,
    status public.deploymentstatus DEFAULT 'PENDING'::public.deploymentstatus NOT NULL,
    endpoint_url character varying,
    api_key character varying,
    config json DEFAULT '{}'::json NOT NULL,
    error_message text,
    deployed_by uuid NOT NULL,
    deployed_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    organization_id uuid,
    metadata jsonb DEFAULT '{}'::jsonb,
    deleted_at timestamp without time zone
);


ALTER TABLE public.deployments OWNER TO postgres;

--
-- Name: invitations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.invitations (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    email character varying(255) NOT NULL,
    role_id uuid NOT NULL,
    invited_by uuid,
    token character varying(255) NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    message character varying(500),
    expires_at timestamp without time zone NOT NULL,
    accepted_at timestamp without time zone,
    accepted_user_id uuid,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.invitations OWNER TO postgres;

--
-- Name: organization_usage; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.organization_usage (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    period_start date NOT NULL,
    period_end date NOT NULL,
    users_count integer DEFAULT 0 NOT NULL,
    agents_count integer DEFAULT 0 NOT NULL,
    deployments_count integer DEFAULT 0 NOT NULL,
    tools_count integer DEFAULT 0 NOT NULL,
    credentials_count integer DEFAULT 0 NOT NULL,
    executions_count integer DEFAULT 0 NOT NULL,
    tokens_used bigint DEFAULT '0'::bigint NOT NULL,
    api_calls_count integer DEFAULT 0 NOT NULL,
    llm_cost_cents integer DEFAULT 0 NOT NULL,
    compute_cost_cents integer DEFAULT 0 NOT NULL,
    storage_cost_cents integer DEFAULT 0 NOT NULL,
    total_cost_cents integer DEFAULT 0 NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.organization_usage OWNER TO postgres;

--
-- Name: organizations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.organizations (
    id uuid NOT NULL,
    name character varying NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    slug character varying(100),
    description text,
    logo_url character varying(500),
    subscription_plan_id uuid,
    subscription_status character varying(20) DEFAULT 'trial'::character varying,
    trial_ends_at timestamp without time zone,
    settings jsonb DEFAULT '{}'::jsonb,
    is_active boolean DEFAULT true NOT NULL,
    deleted_at timestamp without time zone,
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.organizations OWNER TO postgres;

--
-- Name: roles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.roles (
    id uuid NOT NULL,
    name character varying(50) NOT NULL,
    display_name character varying(100) NOT NULL,
    description text,
    scope character varying(20) DEFAULT 'organization'::character varying NOT NULL,
    permissions jsonb NOT NULL,
    is_system_role boolean NOT NULL,
    organization_id uuid,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.roles OWNER TO postgres;

--
-- Name: subscription_plans; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.subscription_plans (
    id uuid NOT NULL,
    name character varying(100) NOT NULL,
    display_name character varying(100) NOT NULL,
    description text,
    max_users integer NOT NULL,
    max_agents integer NOT NULL,
    max_deployments integer NOT NULL,
    max_executions_per_month integer NOT NULL,
    max_tools integer NOT NULL,
    max_credentials integer NOT NULL,
    features jsonb NOT NULL,
    price_monthly_cents integer,
    price_yearly_cents integer,
    is_active boolean NOT NULL,
    is_public boolean NOT NULL,
    sort_order integer,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.subscription_plans OWNER TO postgres;

--
-- Name: tool_executions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tool_executions (
    id uuid NOT NULL,
    tool_id uuid NOT NULL,
    execution_id uuid,
    input json NOT NULL,
    output json,
    status character varying NOT NULL,
    error_message character varying,
    execution_time integer,
    cost integer,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.tool_executions OWNER TO postgres;

--
-- Name: tools; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tools (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    creator_id uuid NOT NULL,
    name character varying NOT NULL,
    description character varying,
    type public.tooltype NOT NULL,
    config json NOT NULL,
    visibility public.toolvisibility DEFAULT 'PRIVATE'::public.toolvisibility NOT NULL,
    status public.toolstatus DEFAULT 'ACTIVE'::public.toolstatus NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.tools OWNER TO postgres;

--
-- Name: user_roles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_roles (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    role_id uuid NOT NULL,
    organization_id uuid,
    assigned_by uuid,
    assigned_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.user_roles OWNER TO postgres;

--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id uuid NOT NULL,
    organization_id uuid NOT NULL,
    email character varying NOT NULL,
    hashed_password character varying NOT NULL,
    role public.userrole DEFAULT 'CREATOR'::public.userrole NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    full_name character varying(255),
    avatar_url character varying(500),
    is_platform_admin boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    email_verified boolean DEFAULT false NOT NULL,
    email_verified_at timestamp without time zone,
    password_changed_at timestamp without time zone,
    failed_login_attempts integer DEFAULT 0 NOT NULL,
    locked_until timestamp without time zone,
    last_login_at timestamp without time zone,
    last_login_ip character varying(45),
    metadata jsonb DEFAULT '{}'::jsonb,
    deleted_at timestamp without time zone,
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Data for Name: agent_executions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.agent_executions (id, agent_id, user_id, input, output, tokens_used, execution_time, created_at) FROM stdin;
\.


--
-- Data for Name: agent_versions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.agent_versions (id, agent_id, version_number, version_tag, config, description, changelog, created_by, created_at) FROM stdin;
\.


--
-- Data for Name: agents; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.agents (id, organization_id, creator_id, name, description, config, version, status, created_at, updated_at, is_template, is_public_template, template_source_id, tags, metadata, deleted_at) FROM stdin;
16519f7b-954d-45e1-a608-2da133bf4db1	9d04a956-fdb0-482a-944b-39d717b02366	f4495596-ea2e-4d74-83d4-0c432ce2b697	HrAgent	HR agent description	{"executionSettings": {"timeout": 30000, "retryPolicy": {"maxRetries": 3, "retryDelay": 1000}}, "nodes": [{"id": "input_1765039948559", "type": "InputNode", "position": {"x": 105, "y": -15}, "data": {"label": "Input", "type": "INPUT", "config": {"chatConfig": {"systemMessage": "I am an HR assistant"}}}, "measured": {"width": 120, "height": 48}, "dragging": false, "selected": false}, {"id": "llm_agent_1765039953215", "type": "LLMAgentNode", "position": {"x": 203.5, "y": 69.25}, "data": {"label": "LLM Agent", "type": "LLM_AGENT", "config": {"credentialId": "be4cf149-e4fc-4e53-bb0a-18a5fb0e9eca", "modelConfig": {"model": "gpt-4-turbo", "temperature": 0.7, "maxTokens": 1024}, "systemPrompt": "You are fictious HR Agent answer in comic tone"}}, "measured": {"width": 250, "height": 100}, "dragging": true, "selected": false}, {"id": "output_1765039964751", "type": "OutputNode", "position": {"x": 490.67999999999995, "y": 172.176}, "data": {"label": "Output", "type": "OUTPUT", "config": {"format": "text"}}, "measured": {"width": 120, "height": 48}, "dragging": true, "selected": false}], "edges": [{"animated": false, "style": {"stroke": "#b1b1b7", "strokeWidth": 2}, "type": "default", "source": "input_1765039948559", "target": "llm_agent_1765039953215", "targetHandle": "input", "id": "xy-edge__input_1765039948559-llm_agent_1765039953215input"}, {"animated": false, "style": {"stroke": "#b1b1b7", "strokeWidth": 2}, "type": "default", "source": "llm_agent_1765039953215", "sourceHandle": "output", "target": "output_1765039964751", "id": "xy-edge__llm_agent_1765039953215output-output_1765039964751"}], "status": "draft", "version": 1}	1	DRAFT	2025-12-06 16:53:55.953044	2025-12-06 16:53:55.953049	f	f	\N	[]	{}	\N
\.


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.alembic_version (version_num) FROM stdin;
005
\.


--
-- Data for Name: audit_logs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.audit_logs (id, organization_id, user_id, user_email, action, resource_type, resource_id, resource_name, old_values, new_values, ip_address, user_agent, request_id, metadata, status, error_message, created_at) FROM stdin;
\.


--
-- Data for Name: credentials; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.credentials (id, user_id, organization_id, name, provider, api_key, api_base, api_version, organization_key, is_active, created_at, updated_at, last_used_at) FROM stdin;
be4cf149-e4fc-4e53-bb0a-18a5fb0e9eca	59bfd3e6-b0e1-478b-afa6-a93e1173f468	9d04a956-fdb0-482a-944b-39d717b02366	OpenAiCredentials	openai	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	\N	\N	\N	active	2025-12-06 11:57:54.26194	2025-12-06 11:57:54.261944	\N
6106f77f-a422-4f53-a0cf-81c106c68f24	59bfd3e6-b0e1-478b-afa6-a93e1173f468	9d04a956-fdb0-482a-944b-39d717b02366	agentstudio_redis	redis	{"host": "localhost", "port": 6379, "database": 0}	\N	\N	\N	active	2025-12-06 12:18:32.381352	2025-12-06 12:18:32.381357	\N
\.


--
-- Data for Name: deployments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.deployments (id, agent_id, version, environment, status, endpoint_url, api_key, config, error_message, deployed_by, deployed_at, created_at, updated_at, organization_id, metadata, deleted_at) FROM stdin;
\.


--
-- Data for Name: invitations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.invitations (id, organization_id, email, role_id, invited_by, token, status, message, expires_at, accepted_at, accepted_user_id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: organization_usage; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.organization_usage (id, organization_id, period_start, period_end, users_count, agents_count, deployments_count, tools_count, credentials_count, executions_count, tokens_used, api_calls_count, llm_cost_cents, compute_cost_cents, storage_cost_cents, total_cost_cents, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: organizations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.organizations (id, name, created_at, slug, description, logo_url, subscription_plan_id, subscription_status, trial_ends_at, settings, is_active, deleted_at, updated_at) FROM stdin;
9d04a956-fdb0-482a-944b-39d717b02366	admin@example.com's Organization	2025-11-23 10:57:37.616098	admin@examplecom's-organization-9d04a956	\N	\N	b88ca591-53a8-456a-ad8d-19a91edb9ab2	active	\N	{}	t	\N	2025-12-13 10:11:07.105722
f3d13479-6989-44c7-b065-273d0cd5d58c	acme-corporatop	2025-12-17 02:39:27.057607	acme-corporatop	\N	\N	\N	trial	\N	{}	t	\N	2025-12-17 02:39:27.05761
\.


--
-- Data for Name: roles; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.roles (id, name, display_name, description, scope, permissions, is_system_role, organization_id, created_at, updated_at) FROM stdin;
fb98b072-a017-4d47-8eca-2256d8645fa1	super_admin	Super Admin	Platform administrator with access to all organizations and system settings	platform	["*"]	t	\N	2025-12-13 10:11:07.105722	2025-12-13 10:11:07.105722
15f41308-0836-4cd6-b984-bed004862836	org_owner	Organization Owner	Full organization control including billing and deletion	organization	["org:*", "users:*", "agents:*", "tools:*", "credentials:*", "deployments:*", "analytics:*", "audit:read"]	t	\N	2025-12-13 10:11:07.105722	2025-12-13 10:11:07.105722
9985974c-289b-4c64-8d48-987b8c5d8cc8	org_admin	Organization Admin	Organization management without billing access	organization	["org:read", "org:update", "users:*", "agents:*", "tools:*", "credentials:*", "deployments:*", "analytics:*", "audit:read"]	t	\N	2025-12-13 10:11:07.105722	2025-12-13 10:11:07.105722
ae34af52-9974-4559-991d-c926a08b2fc4	agent_admin	Agent Admin	Manage all agents regardless of creator	organization	["org:read", "users:read", "agents:*", "tools:*", "credentials:read", "deployments:*", "analytics:read"]	t	\N	2025-12-13 10:11:07.105722	2025-12-13 10:11:07.105722
8d9fad7e-a184-4249-8e62-1d96e53ae9d1	developer	Developer	Create and edit own agents and tools	organization	["org:read", "users:read", "agents:create", "agents:read", "agents:update:own", "agents:delete:own", "agents:execute", "tools:create", "tools:read", "tools:update:own", "tools:delete:own", "credentials:create", "credentials:read", "deployments:read", "deployments:create:non_prod", "analytics:read"]	t	\N	2025-12-13 10:11:07.105722	2025-12-13 10:11:07.105722
0ba7b72b-6fb2-4e15-a06c-5e6e9b730b19	operator	Operator	Execute and deploy agents	organization	["org:read", "users:read", "agents:read", "agents:execute", "tools:read", "deployments:*", "analytics:read"]	t	\N	2025-12-13 10:11:07.105722	2025-12-13 10:11:07.105722
44fee42d-98a6-4f89-afb0-af28b7bb2701	viewer	Viewer	Read-only access to organization resources	organization	["org:read", "users:read", "agents:read", "tools:read", "deployments:read", "analytics:read"]	t	\N	2025-12-13 10:11:07.105722	2025-12-13 10:11:07.105722
\.


--
-- Data for Name: subscription_plans; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.subscription_plans (id, name, display_name, description, max_users, max_agents, max_deployments, max_executions_per_month, max_tools, max_credentials, features, price_monthly_cents, price_yearly_cents, is_active, is_public, sort_order, created_at, updated_at) FROM stdin;
b88ca591-53a8-456a-ad8d-19a91edb9ab2	starter	Starter	For small teams getting started	10	25	10	5000	50	20	{"api_access": true, "audit_logs": true, "custom_tools": true}	2900	29000	t	t	2	2025-12-13 10:11:07.105722	2025-12-13 10:11:07.105722
b79d4550-cca3-4c0a-8ae3-79356be8a1b7	professional	Professional	For growing businesses	50	100	50	50000	200	100	{"api_access": true, "audit_logs": true, "custom_tools": true, "advanced_analytics": true}	9900	99000	t	t	3	2025-12-13 10:11:07.105722	2025-12-13 10:11:07.105722
19680406-e31a-4f5f-a271-3ca1349082db	enterprise	Enterprise	Unlimited with premium support	-1	-1	-1	-1	-1	-1	{"sso": true, "api_access": true, "audit_logs": true, "custom_tools": true, "priority_support": true, "advanced_analytics": true}	0	0	t	t	4	2025-12-13 10:11:07.105722	2025-12-13 10:11:07.105722
a291de80-12bd-4e3c-8551-42253dd25298	free	Free tier	Free tier with limited features	3	1	1	5	5	1	{"api_access": true, "audit_logs": false, "custom_tools": false}	0	0	t	t	1	2025-12-13 10:11:07.105722	2025-12-17 02:42:42.126771
\.


--
-- Data for Name: tool_executions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tool_executions (id, tool_id, execution_id, input, output, status, error_message, execution_time, cost, created_at) FROM stdin;
\.


--
-- Data for Name: tools; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tools (id, organization_id, creator_id, name, description, type, config, visibility, status, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: user_roles; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_roles (id, user_id, role_id, organization_id, assigned_by, assigned_at) FROM stdin;
c366f493-56dd-4147-a0bc-3e947acd4595	59bfd3e6-b0e1-478b-afa6-a93e1173f468	9985974c-289b-4c64-8d48-987b8c5d8cc8	9d04a956-fdb0-482a-944b-39d717b02366	\N	2025-12-13 10:11:07.105722
9756bb54-66b7-4039-82d7-fde9d43a739a	f4495596-ea2e-4d74-83d4-0c432ce2b697	8d9fad7e-a184-4249-8e62-1d96e53ae9d1	9d04a956-fdb0-482a-944b-39d717b02366	\N	2025-12-13 10:11:07.105722
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, organization_id, email, hashed_password, role, created_at, full_name, avatar_url, is_platform_admin, is_active, email_verified, email_verified_at, password_changed_at, failed_login_attempts, locked_until, last_login_at, last_login_ip, metadata, deleted_at, updated_at) FROM stdin;
f4495596-ea2e-4d74-83d4-0c432ce2b697	9d04a956-fdb0-482a-944b-39d717b02366	admin@example.com	$2b$12$i7w3/ByVJSU4B..xlj.Mx.XZTa0CkJltyKK.820j7MFnV//OeMcDG	CREATOR	2025-11-23 10:57:37.888585	\N	\N	f	t	f	\N	\N	0	\N	\N	\N	{}	\N	2025-12-13 10:11:07.105722
59bfd3e6-b0e1-478b-afa6-a93e1173f468	9d04a956-fdb0-482a-944b-39d717b02366	azamitsme@gmail.com	$2b$12$SavULycPDwDESWEHCGI7ieYhM3zvlmlfc1G5oCdfqlxNGR0da7Ila	ADMIN	2025-11-24 18:07:21.925109	\N	\N	t	t	f	\N	\N	0	\N	2025-12-17 17:00:01.248815	\N	{}	\N	2025-12-17 17:00:01.250552
\.


--
-- Name: agent_executions agent_executions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_executions
    ADD CONSTRAINT agent_executions_pkey PRIMARY KEY (id);


--
-- Name: agent_versions agent_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_versions
    ADD CONSTRAINT agent_versions_pkey PRIMARY KEY (id);


--
-- Name: agents agents_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT agents_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: credentials credentials_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.credentials
    ADD CONSTRAINT credentials_pkey PRIMARY KEY (id);


--
-- Name: deployments deployments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.deployments
    ADD CONSTRAINT deployments_pkey PRIMARY KEY (id);


--
-- Name: invitations invitations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invitations
    ADD CONSTRAINT invitations_pkey PRIMARY KEY (id);


--
-- Name: invitations invitations_token_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invitations
    ADD CONSTRAINT invitations_token_key UNIQUE (token);


--
-- Name: organization_usage organization_usage_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.organization_usage
    ADD CONSTRAINT organization_usage_pkey PRIMARY KEY (id);


--
-- Name: organizations organizations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT organizations_pkey PRIMARY KEY (id);


--
-- Name: organizations organizations_slug_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT organizations_slug_key UNIQUE (slug);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- Name: subscription_plans subscription_plans_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subscription_plans
    ADD CONSTRAINT subscription_plans_name_key UNIQUE (name);


--
-- Name: subscription_plans subscription_plans_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subscription_plans
    ADD CONSTRAINT subscription_plans_pkey PRIMARY KEY (id);


--
-- Name: tool_executions tool_executions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tool_executions
    ADD CONSTRAINT tool_executions_pkey PRIMARY KEY (id);


--
-- Name: tools tools_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tools
    ADD CONSTRAINT tools_pkey PRIMARY KEY (id);


--
-- Name: agent_versions uq_agent_version; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_versions
    ADD CONSTRAINT uq_agent_version UNIQUE (agent_id, version_number);


--
-- Name: organization_usage uq_org_usage_period; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.organization_usage
    ADD CONSTRAINT uq_org_usage_period UNIQUE (organization_id, period_start);


--
-- Name: roles uq_role_name_org; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT uq_role_name_org UNIQUE (name, organization_id);


--
-- Name: user_roles uq_user_role_org; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT uq_user_role_org UNIQUE (user_id, role_id, organization_id);


--
-- Name: user_roles user_roles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_agent_executions_agent_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_agent_executions_agent_id ON public.agent_executions USING btree (agent_id);


--
-- Name: idx_agent_executions_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_agent_executions_user_id ON public.agent_executions USING btree (user_id);


--
-- Name: idx_agent_versions_agent_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_agent_versions_agent_id ON public.agent_versions USING btree (agent_id);


--
-- Name: idx_agents_creator_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_agents_creator_id ON public.agents USING btree (creator_id);


--
-- Name: idx_agents_org_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_agents_org_status ON public.agents USING btree (organization_id, status);


--
-- Name: idx_agents_organization_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_agents_organization_id ON public.agents USING btree (organization_id);


--
-- Name: idx_agents_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_agents_status ON public.agents USING btree (status);


--
-- Name: idx_agents_templates; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_agents_templates ON public.agents USING btree (is_template, is_public_template);


--
-- Name: idx_audit_action_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_audit_action_created ON public.audit_logs USING btree (action, created_at);


--
-- Name: idx_audit_org_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_audit_org_created ON public.audit_logs USING btree (organization_id, created_at);


--
-- Name: idx_audit_resource; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_audit_resource ON public.audit_logs USING btree (resource_type, resource_id);


--
-- Name: idx_audit_user_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_audit_user_created ON public.audit_logs USING btree (user_id, created_at);


--
-- Name: idx_deployments_agent_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_deployments_agent_id ON public.deployments USING btree (agent_id);


--
-- Name: idx_deployments_agent_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_deployments_agent_status ON public.deployments USING btree (agent_id, status);


--
-- Name: idx_deployments_org_env; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_deployments_org_env ON public.deployments USING btree (organization_id, environment);


--
-- Name: idx_deployments_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_deployments_status ON public.deployments USING btree (status);


--
-- Name: idx_invitations_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_invitations_email ON public.invitations USING btree (email);


--
-- Name: idx_invitations_org_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_invitations_org_status ON public.invitations USING btree (organization_id, status);


--
-- Name: idx_invitations_token; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_invitations_token ON public.invitations USING btree (token);


--
-- Name: idx_org_usage_period; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_org_usage_period ON public.organization_usage USING btree (organization_id, period_start);


--
-- Name: idx_organizations_slug; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_organizations_slug ON public.organizations USING btree (slug);


--
-- Name: idx_tool_executions_tool_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tool_executions_tool_id ON public.tool_executions USING btree (tool_id);


--
-- Name: idx_tools_organization_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tools_organization_id ON public.tools USING btree (organization_id);


--
-- Name: idx_tools_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tools_type ON public.tools USING btree (type);


--
-- Name: idx_user_roles_org; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_roles_org ON public.user_roles USING btree (organization_id);


--
-- Name: idx_user_roles_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_roles_user ON public.user_roles USING btree (user_id);


--
-- Name: idx_users_platform_admin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_platform_admin ON public.users USING btree (is_platform_admin) WHERE (is_platform_admin = true);


--
-- Name: ix_credentials_organization_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_credentials_organization_id ON public.credentials USING btree (organization_id);


--
-- Name: ix_credentials_provider; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_credentials_provider ON public.credentials USING btree (provider);


--
-- Name: ix_credentials_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_credentials_user_id ON public.credentials USING btree (user_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: agent_executions agent_executions_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_executions
    ADD CONSTRAINT agent_executions_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id);


--
-- Name: agent_executions agent_executions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_executions
    ADD CONSTRAINT agent_executions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: agent_versions agent_versions_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_versions
    ADD CONSTRAINT agent_versions_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id) ON DELETE CASCADE;


--
-- Name: agent_versions agent_versions_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_versions
    ADD CONSTRAINT agent_versions_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: agents agents_creator_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT agents_creator_id_fkey FOREIGN KEY (creator_id) REFERENCES public.users(id);


--
-- Name: agents agents_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT agents_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: audit_logs audit_logs_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE SET NULL;


--
-- Name: audit_logs audit_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: credentials credentials_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.credentials
    ADD CONSTRAINT credentials_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: credentials credentials_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.credentials
    ADD CONSTRAINT credentials_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: deployments deployments_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.deployments
    ADD CONSTRAINT deployments_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id) ON DELETE CASCADE;


--
-- Name: deployments deployments_deployed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.deployments
    ADD CONSTRAINT deployments_deployed_by_fkey FOREIGN KEY (deployed_by) REFERENCES public.users(id);


--
-- Name: agents fk_agents_template_source; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT fk_agents_template_source FOREIGN KEY (template_source_id) REFERENCES public.agents(id);


--
-- Name: deployments fk_deployments_organization; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.deployments
    ADD CONSTRAINT fk_deployments_organization FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: organizations fk_organizations_subscription_plan; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT fk_organizations_subscription_plan FOREIGN KEY (subscription_plan_id) REFERENCES public.subscription_plans(id);


--
-- Name: invitations invitations_accepted_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invitations
    ADD CONSTRAINT invitations_accepted_user_id_fkey FOREIGN KEY (accepted_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: invitations invitations_invited_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invitations
    ADD CONSTRAINT invitations_invited_by_fkey FOREIGN KEY (invited_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: invitations invitations_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invitations
    ADD CONSTRAINT invitations_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: invitations invitations_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invitations
    ADD CONSTRAINT invitations_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;


--
-- Name: organization_usage organization_usage_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.organization_usage
    ADD CONSTRAINT organization_usage_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: roles roles_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: tool_executions tool_executions_execution_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tool_executions
    ADD CONSTRAINT tool_executions_execution_id_fkey FOREIGN KEY (execution_id) REFERENCES public.agent_executions(id);


--
-- Name: tool_executions tool_executions_tool_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tool_executions
    ADD CONSTRAINT tool_executions_tool_id_fkey FOREIGN KEY (tool_id) REFERENCES public.tools(id);


--
-- Name: tools tools_creator_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tools
    ADD CONSTRAINT tools_creator_id_fkey FOREIGN KEY (creator_id) REFERENCES public.users(id);


--
-- Name: tools tools_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tools
    ADD CONSTRAINT tools_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: user_roles user_roles_assigned_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_assigned_by_fkey FOREIGN KEY (assigned_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: user_roles user_roles_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: user_roles user_roles_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;


--
-- Name: user_roles user_roles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: users users_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- PostgreSQL database dump complete
--

\unrestrict E500vfthbQiXyAdyIWd1rR9RAEF484ja7KaJJZhtHNwplJreV2DiwAqAqTXaekz

