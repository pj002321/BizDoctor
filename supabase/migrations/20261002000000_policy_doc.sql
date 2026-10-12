create extension if not exists vector with schema extensions;

create table policy_doc (
  doc_id         text primary key,
  title          text not null,
  content        text not null,
  agency         text,
  target         text,
  limit_amount   text,
  rate           text,
  apply_period   text,
  url            text,
  risk_type_tags text[] not null check (
    cardinality(risk_type_tags) > 0
    and risk_type_tags <@ array['정상_유지형','단기_매출_정체형','원가_상승_부담형',
                                '매출_폭락형','고금리_과다채무형','상권_침체_붕괴형']
  ),
  embedding      extensions.vector(1536),
  fts            tsvector generated always as
                   (to_tsvector('simple', title || ' ' || content)) stored
);

create index policy_doc_tags_gin on policy_doc using gin (risk_type_tags);
create index policy_doc_fts_gin  on policy_doc using gin (fts);