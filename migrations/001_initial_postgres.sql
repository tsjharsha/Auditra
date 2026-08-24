create table if not exists worlds (
    world_id text primary key,
    dataset_id text not null,
    payload jsonb not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists datasets (
    dataset_id text primary key,
    payload jsonb not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists merchants (
    merchant_id text primary key,
    dataset_id text not null,
    payload jsonb not null
);

create table if not exists orders (
    order_id text primary key,
    dataset_id text not null,
    merchant_id text not null,
    amount numeric(18, 2) not null,
    currency text not null,
    created_at timestamptz not null,
    payload jsonb not null
);

create table if not exists payments (
    payment_id text primary key,
    dataset_id text not null,
    order_id text,
    merchant_id text not null,
    amount numeric(18, 2) not null,
    currency text not null,
    captured_at timestamptz not null,
    payload jsonb not null
);

create table if not exists settlements (
    settlement_id text primary key,
    dataset_id text not null,
    payment_id text not null,
    merchant_id text not null,
    amount numeric(18, 2) not null,
    currency text not null,
    settled_at timestamptz not null,
    payload jsonb not null
);

create table if not exists refunds (
    refund_id text primary key,
    dataset_id text not null,
    payment_id text not null,
    merchant_id text not null,
    amount numeric(18, 2) not null,
    currency text not null,
    refunded_at timestamptz not null,
    payload jsonb not null
);

create table if not exists fee_rules (
    fee_rule_id text primary key,
    dataset_id text not null,
    merchant_id text not null,
    currency text not null,
    percent_bps integer not null,
    fixed_fee numeric(18, 2) not null,
    payload jsonb not null
);

create table if not exists transaction_links (
    link_id bigserial primary key,
    dataset_id text not null,
    source_entity text not null,
    source_id text not null,
    relationship text not null,
    target_entity text not null,
    target_id text not null,
    evidence_id text
);

create table if not exists reconciliation_cases (
    case_id text primary key,
    run_id text not null,
    dataset_id text not null,
    payment_id text not null,
    status text not null,
    risk_score numeric(8, 2) not null default 0,
    payload jsonb not null
);

create table if not exists investigations (
    investigation_id text primary key,
    case_id text not null,
    provider text not null,
    model text not null,
    payload jsonb not null
);

create table if not exists hypotheses (
    hypothesis_id text primary key,
    investigation_id text not null,
    label text not null,
    status text not null,
    confidence numeric(8, 4) not null,
    payload jsonb not null
);

create table if not exists evidence_items (
    evidence_id text primary key,
    case_id text not null,
    entity_type text not null,
    entity_id text not null,
    payload jsonb not null
);

create table if not exists agent_tool_calls (
    call_id text primary key,
    run_id text not null,
    case_id text not null,
    tool_name text not null,
    started_at timestamptz not null,
    finished_at timestamptz not null,
    payload jsonb not null
);

create table if not exists controller_decisions (
    case_id text primary key,
    run_id text not null,
    payment_id text not null,
    status text not null,
    confidence_score numeric(8, 4) not null,
    payload jsonb not null
);

create table if not exists verification_results (
    case_id text primary key,
    run_id text not null,
    passed boolean not null,
    payload jsonb not null
);

create table if not exists audit_events (
    event_id text primary key,
    run_id text not null,
    actor text not null,
    action text not null,
    entity text not null,
    entity_id text not null,
    timestamp timestamptz not null,
    payload jsonb not null
);

create table if not exists controller_runs (
    run_id text primary key,
    dataset_id text not null,
    payload jsonb not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists evaluation_runs (
    evaluation_run_id text primary key,
    controller_run_id text not null,
    dataset_id text not null,
    payload jsonb not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists ground_truth_cases (
    dataset_id text not null,
    payment_id text not null,
    expected_status text not null,
    scenario text not null,
    payload jsonb not null,
    primary key (dataset_id, payment_id)
);

create table if not exists human_reviews (
    review_id bigserial primary key,
    case_id text not null,
    payload jsonb not null,
    created_at timestamptz not null default now()
);

create index if not exists idx_payments_dataset on payments(dataset_id);
create index if not exists idx_payments_order on payments(order_id);
create index if not exists idx_payments_merchant on payments(merchant_id);
create index if not exists idx_settlements_payment on settlements(payment_id);
create index if not exists idx_refunds_payment on refunds(payment_id);
create index if not exists idx_cases_run on reconciliation_cases(run_id);
create index if not exists idx_cases_status on reconciliation_cases(status);
create index if not exists idx_tool_calls_case on agent_tool_calls(case_id);
create index if not exists idx_evaluations_controller_run on evaluation_runs(controller_run_id);
