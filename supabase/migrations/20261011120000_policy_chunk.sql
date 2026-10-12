-- 정책 문서를 문서(1) · 조각(N) 두 테이블로 나눈다.
-- 기존 policy_doc 은 JSON 원본에서 언제든 다시 만들 수 있는 파생 데이터라 지우고 새로 만든다.

drop table if exists policy_doc;

-- 제도 1개 = 1행
-- 사용자에게 보여줄 정보와 필터 조건인 태크,마감일을 담는다.
create table policy_doc (
    doc_id      text primary key,
    title       text not null,
    agency      text not null,
    source_url  text not null,
    apply_start date,
    apply_end   date,
    limit_text  text,               -- 원문 표기 그대로.
    rate_text   text,
    risk_type_tags  text[] not null check (
        cardinality(risk_type_tags) > 0
        and risk_type_tags <@
        array['정상_유지형','단기_매출_정체형','원가_상승_부담형','매출_폭락형','고금리_과다채무형','상권_침체_붕괴형']
    ),
    content_hash    text not null,  -- 바뀐 문서에 대한 해시 처리 기준
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    check (apply_start <= apply_end)    -- 마감된 제도 처리
);

-- 공고문 항목 1개 = 1행. 질문과 비교하는 검색 단위
create table policy_chunk (
    id          bigint generated always as identity primary key,
    doc_id      text not null references policy_doc (doc_id) on delete cascade, -- 없는 제도 조각 검색 방지
    chunk_index int not null,
    section     text not null check (section in (
        '지원대상','지원내용','지원한도','금리및조건',
        '신청기간','신청방법','제출서류','유의사항')),
    body        text not null,      -- "[제도명, 항목명] 본문"
    n_tokens    int not null check (n_tokens>0),
    embedding   extensions.vector(1536),
    embedding_model text,
    fts         tsvector generated always as (to_tsvector('simple',body)) stored,
    unique      (doc_id, chunk_index),
    check       ((embedding is null) = (embedding_model is null))
);

create index policy_doc_tags_gin on policy_doc  using gin (risk_type_tags);
create index policy_chunk_fts_gin on policy_chunk using gin (fts);

-- Supabase는 public 테이블을 REST API로 노출함. rls만 켜서 API 접근을 방지
alter table policy_doc enable row level security;
alter table policy_chunk enable row level security;
