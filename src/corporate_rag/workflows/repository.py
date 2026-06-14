# ruff: noqa: E501

from corporate_rag.graph.interfaces import BaseGraphReader


def document_count(reader: BaseGraphReader) -> int:
    rows = reader.read(DOCUMENT_COUNT_CYPHER)
    raw_count = rows[0].get("document_count") if rows else 0
    return int(raw_count or 0)


DOCUMENT_COUNT_CYPHER = 'MATCH (w:Work) RETURN count(DISTINCT w) AS document_count'

SUBJECT_OVERVIEW = r"""
MATCH (subject:BusinessSubject {subjectId: $subject_id})
OPTIONAL MATCH (subject)-[:HAS_PHASE]->(phase:Entity)
OPTIONAL MATCH (phase)-[:INSTANCE_OF]->(c:Class)
WITH subject, phase, collect(DISTINCT c.localName) AS phase_classes
CALL (phase) {
  OPTIONAL MATCH (phase)--(boundary_event:Event)
  WHERE boundary_event.eventType IN ['incorporation', 'continuation-in', 'redomiciliation', 'legal-form-conversion', 'continuation-out', 'dissolution', 'liquidation-end', 'striking-off']
    AND boundary_event.effectiveDate IN [
          phase.phase_valid_from, phase.phase_valid_to
        ]
  RETURN collect(DISTINCT boundary_event{
           .entityId, .label, .eventType, .effectiveDate,
           .source_doc, .source_chunk
         }) AS _raw_boundary
}
WITH subject, phase, phase_classes,
     [r IN _raw_boundary WHERE r.source_doc IS NOT NULL
      | {file: r.source_doc, chunk_id: r.source_chunk}] AS sources
CALL (phase) {
  OPTIONAL MATCH (phase)-[attachment:HAS_REGISTERED_ADDRESS]->(addr:Entity)
  WHERE (addr:ConventionalStreetAddress OR addr:PhysicalAddress)
    AND coalesce(addr.lifecycle_status, 'active') <> 'superseded'
  WITH phase, attachment, addr
  WHERE attachment IS NOT NULL
  ORDER BY coalesce(attachment.valid_from, attachment.valid_to, phase.phase_valid_from, '') DESC,
           coalesce(attachment.valid_to, '9999-12-31') DESC,
           coalesce(addr.addressText, addr.street_line, addr.label, '') ASC
  RETURN head(collect({
           address: coalesce(addr.addressText, addr.street_line, addr.label),
           street: addr.street_line,
           city: addr.city,
           country_iso2: coalesce(addr.iso_alpha2, addr.country_code),
           country: coalesce(addr.country_name, addr.name_en, addr.name, addr.country_code)
         })) AS registered_office
}
RETURN subject.subjectId             AS subject_id,
       subject.label                 AS subject,
       phase.entityId                AS phase_id,
       phase.label                   AS phase_label,
       phase_classes                 AS phase_classes,
       phase.phase_valid_from        AS phase_valid_from,
       phase.phase_valid_to          AS phase_valid_to,
       phase.registration_number     AS registration_number,
       phase.registration_scheme     AS registration_scheme,
       phase.legal_form_suffix       AS legal_form,
       phase.governing_law           AS governing_law,
       phase.status                  AS status,
       registered_office             AS registered_office,
       sources                       AS sources
ORDER BY coalesce(phase.phase_valid_from, '')
""".strip()

ORGANIZATION_OVERVIEW = r"""
MATCH (n:Entity:LegalEntity)
WHERE coalesce($organization_id, '') = '' OR n.entityId = $organization_id
CALL {
  WITH n
  OPTIONAL MATCH (n)-[:INSTANCE_OF]->(c:Class)
  RETURN collect(DISTINCT c.localName) AS fibo_classes
}
CALL {
  WITH n
  OPTIONAL MATCH (n)-[:HAS_LEGAL_FORM]->(f)
  RETURN collect(DISTINCT f.label) AS legal_forms
}
CALL {
  WITH n
  OPTIONAL MATCH (n)-[:HAS_LEGAL_NAME]->(ln:OrganizationName)
  RETURN collect(DISTINCT ln.label) AS legal_names
}
CALL {
  WITH n
  OPTIONAL MATCH (n)-[:IS_ORGANIZED_IN|IS_INCORPORATED_IN]->(j:Jurisdiction)
  RETURN collect(DISTINCT j.label) AS jurisdictions
}
CALL {
  WITH n
  OPTIONAL MATCH (n)-[attachment:HAS_REGISTERED_ADDRESS]->(addr)
  WHERE (addr:ConventionalStreetAddress OR addr:PhysicalAddress)
    AND coalesce(addr.lifecycle_status, 'active') <> 'superseded'
  WITH n, attachment, addr
  ORDER BY coalesce(attachment.valid_from, attachment.valid_to, n.phase_valid_from, '') DESC,
           coalesce(attachment.valid_to, '9999-12-31') DESC,
           coalesce(addr.addressText, addr.street_line, addr.label, '') ASC
  WITH head(collect(coalesce(addr.addressText, addr.street_line, addr.label))) AS registered_office
  RETURN CASE
           WHEN registered_office IS NULL THEN []
           ELSE [registered_office]
         END AS registered_offices
}
CALL {
  WITH n
  OPTIONAL MATCH (n)-[:IS_IDENTIFIED_BY|HAS_IDENTIFIER|IS_REGISTERED_BY]->(ri:RegistrationIdentifier)
  WITH n, [v IN collect(DISTINCT coalesce(ri.identifierValue, ri.label)) WHERE v IS NOT NULL] AS rid_values
  RETURN CASE
           WHEN size(rid_values) > 0 THEN rid_values
           WHEN n.registration_number IS NOT NULL THEN [n.registration_number]
           ELSE []
         END AS registration_numbers
}
CALL {
  WITH n
  OPTIONAL MATCH (n)-[:HAS_DATE_OF_INCORPORATION]->(d:Date)
  RETURN head(collect(DISTINCT d.iso_date)) AS doi_edge
}
CALL {
  WITH n
  OPTIONAL MATCH (parent:BusinessSubject)-[:HAS_PHASE]->(n)
  RETURN head(collect(parent.label)) AS subject_family,
         head(collect(parent.subjectId)) AS subject_id
}
CALL {
  WITH n
  OPTIONAL MATCH (chunk:Chunk)-[:EVIDENCES|MENTIONS|RECORDS|DESIGNATES_SIGNATORY]->(n)
  OPTIONAL MATCH (chunk)<-[:HAS_PART]-(chunk_expr:Expression)
                -[:HAS_EMBODIMENT]->(:Manifestation)
                -[:HAS_EXEMPLAR]->(chunk_item:Item)
  WITH n,
       [entry IN collect(DISTINCT
          CASE WHEN chunk IS NULL OR chunk_item.inbox_filename IS NULL THEN NULL
               ELSE {file: chunk_item.inbox_filename, chunk_id: chunk.chunk_id} END)
         WHERE entry IS NOT NULL] AS chunk_mentions
  OPTIONAL MATCH (expr:Expression)-[:EVIDENCES|MENTIONS|RECORDS|DESIGNATES_SIGNATORY]->(n)
  OPTIONAL MATCH (expr)-[:HAS_EMBODIMENT]->(:Manifestation)
                -[:HAS_EXEMPLAR]->(expr_item:Item)
  WITH chunk_mentions,
       [entry IN collect(DISTINCT
          CASE WHEN expr IS NULL OR expr_item.inbox_filename IS NULL THEN NULL
               ELSE {file: expr_item.inbox_filename, chunk_id: null} END)
         WHERE entry IS NOT NULL] AS expression_mentions
  WITH reduce(mentions = [],
              entry IN chunk_mentions + expression_mentions |
                CASE
                  WHEN any(existing IN mentions WHERE existing.file = entry.file) THEN
                    [existing IN mentions |
                      CASE
                        WHEN existing.file <> entry.file THEN existing
                        WHEN existing.chunk_id IS NOT NULL THEN existing
                        ELSE entry
                      END]
                  ELSE mentions + [entry]
                END) AS mentions
  RETURN mentions
}
RETURN n.entityId   AS organization_id,
       n.label      AS label,
       fibo_classes,
       legal_forms,
       legal_names,
       jurisdictions,
       registered_offices,
       registration_numbers,
       coalesce(doi_edge, n.date_of_incorporation) AS date_of_incorporation,
       n.phase_valid_to AS date_of_dissolution,
       n.governing_law AS governing_law,
       n.aliases    AS aliases,
       subject_family,
       subject_id,
       size(mentions)                         AS mention_count,
       mentions                               AS mentions,
       count{ (n)--() }                       AS edge_count
ORDER BY edge_count DESC, label ASC
""".strip()

PERSON_OVERVIEW = r"""
MATCH (person:Entity:Person)
WHERE coalesce($person_id, '') = '' OR person.entityId = $person_id
OPTIONAL MATCH (chunk:Chunk)-[:EVIDENCES|MENTIONS|RECORDS|DESIGNATES_SIGNATORY]->(person)
OPTIONAL MATCH (chunk)<-[:HAS_PART]-(chunk_expr:Expression)
              -[:HAS_EMBODIMENT]->(:Manifestation)
              -[:HAS_EXEMPLAR]->(chunk_item:Item)
WITH person,
     [entry IN collect(DISTINCT
        CASE WHEN chunk IS NULL OR chunk_item.inbox_filename IS NULL THEN NULL
             ELSE {file: chunk_item.inbox_filename, chunk_id: chunk.chunk_id} END)
       WHERE entry IS NOT NULL] AS chunk_mentions
OPTIONAL MATCH (expr:Expression)-[:EVIDENCES|MENTIONS|RECORDS|DESIGNATES_SIGNATORY]->(person)
OPTIONAL MATCH (expr)-[:HAS_EMBODIMENT]->(:Manifestation)
              -[:HAS_EXEMPLAR]->(expr_item:Item)
WITH person, chunk_mentions,
     [entry IN collect(DISTINCT
        CASE WHEN expr IS NULL OR expr_item.inbox_filename IS NULL THEN NULL
             ELSE {file: expr_item.inbox_filename, chunk_id: null} END)
       WHERE entry IS NOT NULL] AS expression_mentions
OPTIONAL MATCH (document:Instance)-[:SIGNED_BY|DESIGNATES_SIGNATORY|AUTHORIZES|HAS_AUTHORIZED_PARTY]->(person)
OPTIONAL MATCH (document)-[:HAS_EMBODIMENT]->(:Manifestation)
              -[:HAS_EXEMPLAR]->(document_item:Item)
WITH person, chunk_mentions, expression_mentions,
     [entry IN collect(DISTINCT
        CASE WHEN document IS NULL OR document_item.inbox_filename IS NULL THEN NULL
             ELSE {file: document_item.inbox_filename, chunk_id: null} END)
       WHERE entry IS NOT NULL] AS document_mentions
WITH person,
     reduce(mentions = [],
            entry IN chunk_mentions + expression_mentions + document_mentions |
              CASE
                WHEN any(existing IN mentions WHERE existing.file = entry.file) THEN
                  [existing IN mentions |
                    CASE
                      WHEN existing.file <> entry.file THEN existing
                      WHEN existing.chunk_id IS NOT NULL THEN existing
                      ELSE entry
                    END]
                ELSE mentions + [entry]
              END) AS mentions
OPTIONAL MATCH (person)-[:IS_IDENTIFIED_BY]->(passport:PassportIdentifier)
WITH person, mentions,
     [value IN collect(DISTINCT coalesce(passport.label, head(passport.aliases)))
        WHERE value IS NOT NULL] AS passport_numbers
RETURN person.entityId          AS person_id,
       person.label             AS person,
       person.date_of_birth     AS date_of_birth,
       person.nationality       AS nationality,
       person.residence         AS residence,
       passport_numbers         AS passport,
       size(mentions)                           AS mention_count,
       mentions                                 AS mentions
ORDER BY mention_count DESC, person.label ASC
""".strip()

DOCUMENTS_SEARCH = r"""
WITH coalesce($doc_type, [])             AS doc_types,
     coalesce($signatory_person_id, '')  AS signatory_id,
     coalesce($subject_id, '')           AS subject_id,
     coalesce($text_query, '')           AS text_query,
     coalesce($file, '')                 AS file_id
WITH doc_types, signatory_id, subject_id, text_query, file_id,
     size(doc_types) > 0 AS has_doc_type,
     signatory_id  <> '' AS has_signatory,
     subject_id    <> '' AS has_subject,
     text_query    <> '' AS has_text,
     file_id       <> '' AS has_file
MATCH (w:Work)-[:HAS_REALIZATION]->(expr:Expression)
MATCH (expr)-[:HAS_EMBODIMENT]->(:Manifestation)-[:HAS_EXEMPLAR]->(item:Item)
WHERE NOT has_doc_type OR w.doc_type IN doc_types
OPTIONAL MATCH (expr)-[:HAS_EFFECTIVE_DATE]->(d:Entity:Date)
WITH w, expr, item, signatory_id, subject_id, text_query, file_id,
     has_signatory, has_subject, has_text, has_file,
     coalesce(w.date, expr.effective_date, toString(d.iso_date)) AS effective_date
WHERE
  (NOT has_file OR item.item_id = file_id OR item.inbox_filename = file_id)
  AND (NOT has_signatory OR EXISTS {
    MATCH (expr)-[:DESIGNATES_SIGNATORY]->(p:Entity {entityId: signatory_id})
  })
  AND (NOT has_subject OR EXISTS {
    MATCH (s:BusinessSubject {subjectId: subject_id})-[:HAS_PHASE]->(phase:Entity)
    MATCH (expr)-[:MENTIONS|RECORDS|DESIGNATES_SIGNATORY|EVIDENCES]->(phase)
  })
  AND (
    NOT has_text
    OR toLower(coalesce(w.title, ''))   CONTAINS toLower(text_query)
    OR toLower(coalesce(w.summary, '')) CONTAINS toLower(text_query)
    OR toLower(coalesce(w.doc_type, '')) CONTAINS toLower(text_query)
  )
RETURN DISTINCT
       w.work_id            AS work_id,
       expr.entityId        AS expression_id,
       item.item_id         AS item_id,
       w.title              AS title,
       w.doc_type           AS doc_type,
       item.inbox_filename  AS file,
       effective_date       AS effective_date,
       coalesce(w.lifecycle_status, 'active')   AS work_lifecycle_status,
       coalesce(expr.lifecycle_status, 'active') AS expression_lifecycle_status,
       coalesce(item.lifecycle_status, 'active') AS item_lifecycle_status,
       w.summary            AS summary,
       CASE WHEN item.inbox_filename IS NULL THEN []
            ELSE [{file: item.inbox_filename, chunk_id: null}]
       END                  AS sources
ORDER BY
  CASE work_lifecycle_status WHEN 'active' THEN 0 ELSE 1 END,
  effective_date DESC, title
LIMIT toInteger($limit)
""".strip()

CAPITAL_EVENTS = r"""
WITH coalesce($subject_id, '')      AS subject_id,
     coalesce($organization_id, '') AS organization_id,
     CASE WHEN coalesce($as_of, '') = '' THEN NULL ELSE $as_of END AS as_of,
     CASE WHEN coalesce($since, '') = '' THEN NULL ELSE $since END AS since_,
     CASE WHEN coalesce($until, '') = '' THEN NULL ELSE $until END AS until_
MATCH (e:Entity:Event)
OPTIONAL MATCH (e)-[:HAS_EFFECTIVE_DATE]->(date_node:Entity:Date)
WITH e, subject_id, organization_id, as_of, since_, until_,
     coalesce(toString(date_node.iso_date), e.effectiveDate) AS effective_date
WHERE CASE
  WHEN e.eventType = 'incorporation' THEN 'corporate_lifecycle'
  WHEN e.eventType = 'constitutional-adoption' THEN 'constitutional_governance'
  WHEN e.eventType = 'articles-amendment' THEN 'constitutional_governance'
  WHEN e.eventType = 'continuation-in' THEN 'corporate_lifecycle'
  WHEN e.eventType = 'continuation-out' THEN 'corporate_lifecycle'
  WHEN e.eventType = 'redomiciliation' THEN 'corporate_lifecycle'
  WHEN e.eventType = 'legal-form-conversion' THEN 'corporate_lifecycle'
  WHEN e.eventType = 'dissolution' THEN 'corporate_lifecycle'
  WHEN e.eventType = 'liquidation-start' THEN 'corporate_lifecycle'
  WHEN e.eventType = 'liquidation-end' THEN 'corporate_lifecycle'
  WHEN e.eventType = 'striking-off' THEN 'corporate_lifecycle'
  WHEN e.eventType = 'board-meeting' THEN 'constitutional_governance'
  WHEN e.eventType = 'board-resolution' THEN 'constitutional_governance'
  WHEN e.eventType = 'shareholder-meeting' THEN 'constitutional_governance'
  WHEN e.eventType = 'shareholder-resolution' THEN 'constitutional_governance'
  WHEN e.eventType = 'director-appointment' THEN 'officers_and_roles'
  WHEN e.eventType = 'director-resignation' THEN 'officers_and_roles'
  WHEN e.eventType = 'officer-appointment' THEN 'officers_and_roles'
  WHEN e.eventType = 'officer-resignation' THEN 'officers_and_roles'
  WHEN e.eventType = 'auditor-appointment' THEN 'officers_and_roles'
  WHEN e.eventType = 'share-issuance' THEN 'capital_and_shares'
  WHEN e.eventType = 'share-allotment' THEN 'capital_and_shares'
  WHEN e.eventType = 'share-transfer' THEN 'capital_and_shares'
  WHEN e.eventType = 'share-cancellation' THEN 'capital_and_shares'
  WHEN e.eventType = 'capital-increase' THEN 'capital_and_shares'
  WHEN e.eventType = 'capital-reduction' THEN 'capital_and_shares'
  WHEN e.eventType = 'capital-contribution-cash' THEN 'capital_and_shares'
  WHEN e.eventType = 'capital-contribution-in-kind' THEN 'capital_and_shares'
  WHEN e.eventType = 'dividend-declaration' THEN 'distributions'
  WHEN e.eventType = 'dividend-payment' THEN 'distributions'
  WHEN e.eventType = 'power-of-attorney-grant' THEN 'authority_and_representation'
  WHEN e.eventType = 'power-of-attorney-revocation' THEN 'authority_and_representation'
  WHEN e.eventType = 'proxy-grant' THEN 'authority_and_representation'
  WHEN e.eventType = 'loan-agreement' THEN 'finance_and_treasury'
  WHEN e.eventType = 'loan-repayment' THEN 'finance_and_treasury'
  WHEN e.eventType = 'loan-forgiveness' THEN 'finance_and_treasury'
  WHEN e.eventType = 'merger' THEN 'reorganization_and_transactions'
  WHEN e.eventType = 'demerger' THEN 'reorganization_and_transactions'
  WHEN e.eventType = 'asset-transfer' THEN 'reorganization_and_transactions'
  WHEN e.eventType = 'intercompany-agreement' THEN 'reorganization_and_transactions'
  WHEN e.eventType = 'tax-ruling-request' THEN 'tax_and_regulatory'
  WHEN e.eventType = 'tax-ruling-grant' THEN 'tax_and_regulatory'
  WHEN e.eventType = 'tax-residence-attestation' THEN 'tax_and_regulatory'
  WHEN e.eventType = 'annual-report-filing' THEN 'tax_and_regulatory'
  WHEN e.eventType = 'annual-report-approval' THEN 'tax_and_regulatory'
  WHEN e.eventType = 'notarial-certification' THEN 'formalities'
  WHEN e.eventType = 'apostille' THEN 'formalities'
  WHEN e.eventType = 'cancellation' THEN 'meta_quality'
  WHEN e.eventType = 'recall-of-decision' THEN 'meta_quality'
  WHEN e.eventType = 'unclassified' THEN 'meta_quality'
  ELSE 'unknown'
END = 'capital_and_shares'
  AND (as_of IS NULL OR effective_date <= as_of)
  AND (since_ IS NULL OR effective_date >= since_)
  AND (until_ IS NULL OR effective_date <= until_)
  AND (
    subject_id = ''
    OR EXISTS {
      MATCH (subject:BusinessSubject {subjectId: subject_id})-[:HAS_PHASE]->(phase:Entity)
      MATCH (e)-[subject_rel]->(phase)
      WHERE type(subject_rel) IN ['HAS_ACTOR', 'HAS_UNDERGOER', 'HAS_COUNTERPARTY',
                                  'INVOLVES_CONTROLLED_THING', 'RELATED_ENDEAVOUR']
        AND (
          effective_date IS NULL
          OR (
            (phase.phase_valid_from IS NULL OR effective_date >= phase.phase_valid_from)
            AND effective_date <= coalesce(phase.phase_valid_to, toString(date()))
          )
        )
    }
    OR EXISTS {
      MATCH (subject:BusinessSubject {subjectId: subject_id})-[:HAS_PHASE]->(phase:Entity)
      MATCH (e)-[subject_shareholding_rel]->(shareholding:Entity:Shareholding)
            -[:IS_ISSUED_BY|HAS_VESTED_IN_IT]->(phase)
      WHERE type(subject_shareholding_rel) IN ['HAS_ACTOR', 'HAS_UNDERGOER',
                                               'HAS_COUNTERPARTY',
                                               'INVOLVES_CONTROLLED_THING',
                                               'RELATED_ENDEAVOUR']
        AND (
          effective_date IS NULL
          OR (
            (phase.phase_valid_from IS NULL OR effective_date >= phase.phase_valid_from)
            AND effective_date <= coalesce(phase.phase_valid_to, toString(date()))
          )
        )
    }
  )
  AND (
    organization_id = ''
    OR EXISTS {
      MATCH (e)-[organization_rel]->(:Entity {entityId: organization_id})
      WHERE type(organization_rel) IN ['HAS_ACTOR', 'HAS_UNDERGOER', 'HAS_COUNTERPARTY',
                                       'INVOLVES_CONTROLLED_THING', 'RELATED_ENDEAVOUR']
    }
    OR EXISTS {
      MATCH (e)-[organization_shareholding_rel]->(shareholding:Entity:Shareholding)
            -[:IS_ISSUED_BY|HAS_VESTED_IN_IT]->(:Entity {entityId: organization_id})
      WHERE type(organization_shareholding_rel) IN ['HAS_ACTOR', 'HAS_UNDERGOER',
                                                    'HAS_COUNTERPARTY',
                                                    'INVOLVES_CONTROLLED_THING',
                                                    'RELATED_ENDEAVOUR']
    }
  )
OPTIONAL MATCH (subj:BusinessSubject)
WHERE subject_id <> '' AND subj.subjectId = subject_id
WITH DISTINCT e, effective_date, subj
OPTIONAL MATCH (e)-[:HAS_ACTOR]->(actor:Entity)
OPTIONAL MATCH (e)-[:HAS_UNDERGOER]->(undergoer:Entity)
OPTIONAL MATCH (e)-[:HAS_COUNTERPARTY]->(counterparty:Entity)
OPTIONAL MATCH (e)-[:HAS_NOTIONAL_AMOUNT]->(amount:Entity)
OPTIONAL MATCH (source_expr:Expression)-[source_rel:RECORDS|MENTIONS|EVIDENCES]->(e)
OPTIONAL MATCH (source_expr)<-[:HAS_REALIZATION]-(w:Work)
OPTIONAL MATCH (source_expr)-[:HAS_EMBODIMENT]->(:Manifestation)-[:HAS_EXEMPLAR]->(item:Item)
WITH e, effective_date, subj, actor, undergoer, counterparty, amount,
     source_rel, w, item,
     CASE
  WHEN w.doc_type IS NULL THEN 'missing_document'
  WHEN e.eventType IS NULL THEN 'unknown_event_type'
  WHEN e.eventType = 'incorporation' AND w.doc_type = 'incorporation_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'incorporation' AND w.doc_type IN ['articles_of_association_or_bylaws'] THEN 'fallback_authority'
  WHEN e.eventType = 'incorporation' AND w.doc_type IN ['good_standing_certificate', 'registry_extract', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'constitutional-adoption' AND w.doc_type = 'articles_of_association_or_bylaws' THEN 'primary_authority'
  WHEN e.eventType = 'constitutional-adoption' AND w.doc_type IN ['incorporation_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'constitutional-adoption' AND w.doc_type IN ['registry_extract', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'articles-amendment' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'articles-amendment' AND w.doc_type IN ['articles_of_association_or_bylaws', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'articles-amendment' AND w.doc_type IN ['registry_extract', 'legal_opinion'] THEN 'weak_or_context'
  WHEN e.eventType = 'continuation-in' AND w.doc_type = 'continuation_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'continuation-in' AND w.doc_type IN ['registry_filing', 'redomiciliation_application'] THEN 'fallback_authority'
  WHEN e.eventType = 'continuation-in' AND w.doc_type IN ['registry_extract', 'good_standing_certificate'] THEN 'weak_or_context'
  WHEN e.eventType = 'continuation-out' AND w.doc_type = 'discontinuance_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'continuation-out' AND w.doc_type IN ['registry_filing', 'redomiciliation_application'] THEN 'fallback_authority'
  WHEN e.eventType = 'continuation-out' AND w.doc_type IN ['registry_extract', 'good_standing_certificate'] THEN 'weak_or_context'
  WHEN e.eventType = 'redomiciliation' AND w.doc_type = 'continuation_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'redomiciliation' AND w.doc_type IN ['discontinuance_certificate', 'redomiciliation_application', 'reorganization_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'redomiciliation' AND w.doc_type IN ['registry_extract', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'legal-form-conversion' AND w.doc_type = 'registry_filing' THEN 'primary_authority'
  WHEN e.eventType = 'legal-form-conversion' AND w.doc_type IN ['reorganization_deed', 'shareholder_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'legal-form-conversion' AND w.doc_type IN ['registry_extract', 'legal_opinion'] THEN 'weak_or_context'
  WHEN e.eventType = 'dissolution' AND w.doc_type = 'dissolution_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'dissolution' AND w.doc_type IN ['registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'dissolution' AND w.doc_type IN ['good_standing_certificate', 'registry_extract'] THEN 'weak_or_context'
  WHEN e.eventType = 'liquidation-start' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'liquidation-start' AND w.doc_type IN ['registry_filing', 'reorganization_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'liquidation-start' AND w.doc_type IN ['registry_extract', 'correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'liquidation-end' AND w.doc_type = 'dissolution_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'liquidation-end' AND w.doc_type IN ['registry_filing', 'administrative_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'liquidation-end' AND w.doc_type IN ['registry_extract', 'correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'striking-off' AND w.doc_type = 'administrative_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'striking-off' AND w.doc_type IN ['registry_filing', 'registry_extract_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'striking-off' AND w.doc_type IN ['registry_extract', 'correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'board-meeting' AND w.doc_type = 'board_meeting_minutes' THEN 'primary_authority'
  WHEN e.eventType = 'board-meeting' AND w.doc_type IN ['board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'board-meeting' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'board-resolution' AND w.doc_type = 'board_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'board-resolution' AND w.doc_type IN ['board_meeting_minutes'] THEN 'fallback_authority'
  WHEN e.eventType = 'board-resolution' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'shareholder-meeting' AND w.doc_type = 'shareholder_meeting_minutes' THEN 'primary_authority'
  WHEN e.eventType = 'shareholder-meeting' AND w.doc_type IN ['shareholder_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'shareholder-meeting' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'shareholder-resolution' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'shareholder-resolution' AND w.doc_type IN ['shareholder_meeting_minutes'] THEN 'fallback_authority'
  WHEN e.eventType = 'shareholder-resolution' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'director-appointment' AND w.doc_type = 'director_appointment' THEN 'primary_authority'
  WHEN e.eventType = 'director-appointment' AND w.doc_type IN ['board_resolution', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'director-appointment' AND w.doc_type IN ['registry_extract', 'good_standing_certificate', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'director-resignation' AND w.doc_type = 'director_resignation' THEN 'primary_authority'
  WHEN e.eventType = 'director-resignation' AND w.doc_type IN ['board_resolution', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'director-resignation' AND w.doc_type IN ['registry_extract', 'good_standing_certificate', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'officer-appointment' AND w.doc_type = 'board_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'officer-appointment' AND w.doc_type IN ['director_appointment', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'officer-appointment' AND w.doc_type IN ['registry_extract', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'officer-resignation' AND w.doc_type = 'board_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'officer-resignation' AND w.doc_type IN ['director_resignation', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'officer-resignation' AND w.doc_type IN ['registry_extract', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'auditor-appointment' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'auditor-appointment' AND w.doc_type IN ['board_resolution', 'engagement_letter'] THEN 'fallback_authority'
  WHEN e.eventType = 'auditor-appointment' AND w.doc_type IN ['annual_accounts_financial_statements', 'registry_extract'] THEN 'weak_or_context'
  WHEN e.eventType = 'share-issuance' AND w.doc_type = 'share_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'share-issuance' AND w.doc_type IN ['share_register', 'shareholder_resolution', 'board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'share-issuance' AND w.doc_type IN ['annual_accounts_financial_statements', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'share-allotment' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'share-allotment' AND w.doc_type IN ['board_resolution', 'share_register', 'share_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'share-allotment' AND w.doc_type IN ['corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'share-transfer' AND w.doc_type = 'share_transfer_agreement' THEN 'primary_authority'
  WHEN e.eventType = 'share-transfer' AND w.doc_type IN ['share_register', 'share_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'share-transfer' AND w.doc_type IN ['corporate_data_sheet', 'registry_extract'] THEN 'weak_or_context'
  WHEN e.eventType = 'share-cancellation' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'share-cancellation' AND w.doc_type IN ['share_register', 'share_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'share-cancellation' AND w.doc_type IN ['annual_accounts_financial_statements', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'capital-increase' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'capital-increase' AND w.doc_type IN ['registry_filing', 'share_register', 'share_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'capital-increase' AND w.doc_type IN ['annual_accounts_financial_statements', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'capital-reduction' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'capital-reduction' AND w.doc_type IN ['registry_filing', 'share_register'] THEN 'fallback_authority'
  WHEN e.eventType = 'capital-reduction' AND w.doc_type IN ['annual_accounts_financial_statements', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'capital-contribution-cash' AND w.doc_type = 'banking_payment_or_credit_record' THEN 'primary_authority'
  WHEN e.eventType = 'capital-contribution-cash' AND w.doc_type IN ['share_contribution_agreement', 'board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'capital-contribution-cash' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'capital-contribution-in-kind' AND w.doc_type = 'share_contribution_agreement' THEN 'primary_authority'
  WHEN e.eventType = 'capital-contribution-in-kind' AND w.doc_type IN ['reorganization_deed', 'legal_declaration', 'board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'capital-contribution-in-kind' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'dividend-declaration' AND w.doc_type = 'board_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'dividend-declaration' AND w.doc_type IN ['shareholder_resolution', 'board_meeting_minutes'] THEN 'fallback_authority'
  WHEN e.eventType = 'dividend-declaration' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'dividend-payment' AND w.doc_type = 'banking_payment_or_credit_record' THEN 'primary_authority'
  WHEN e.eventType = 'dividend-payment' AND w.doc_type IN ['legal_declaration'] THEN 'fallback_authority'
  WHEN e.eventType = 'dividend-payment' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'power-of-attorney-grant' AND w.doc_type = 'power_of_attorney' THEN 'primary_authority'
  WHEN e.eventType = 'power-of-attorney-grant' AND w.doc_type IN ['board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'power-of-attorney-grant' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'power-of-attorney-revocation' AND w.doc_type = 'power_of_attorney' THEN 'primary_authority'
  WHEN e.eventType = 'power-of-attorney-revocation' AND w.doc_type IN ['board_resolution', 'legal_declaration'] THEN 'fallback_authority'
  WHEN e.eventType = 'power-of-attorney-revocation' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'proxy-grant' AND w.doc_type = 'proxy' THEN 'primary_authority'
  WHEN e.eventType = 'proxy-grant' AND w.doc_type IN ['shareholder_meeting_minutes'] THEN 'fallback_authority'
  WHEN e.eventType = 'proxy-grant' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'loan-agreement' AND w.doc_type = 'intercompany_or_other_agreement' THEN 'primary_authority'
  WHEN e.eventType = 'loan-agreement' AND w.doc_type IN ['board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'loan-agreement' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'loan-repayment' AND w.doc_type = 'banking_payment_or_credit_record' THEN 'primary_authority'
  WHEN e.eventType = 'loan-repayment' AND w.doc_type IN ['legal_declaration'] THEN 'fallback_authority'
  WHEN e.eventType = 'loan-repayment' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'loan-forgiveness' AND w.doc_type = 'legal_declaration' THEN 'primary_authority'
  WHEN e.eventType = 'loan-forgiveness' AND w.doc_type IN ['intercompany_or_other_agreement', 'board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'loan-forgiveness' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'merger' AND w.doc_type = 'reorganization_deed' THEN 'primary_authority'
  WHEN e.eventType = 'merger' AND w.doc_type IN ['reorganization_resolution', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'merger' AND w.doc_type IN ['registry_extract', 'legal_opinion'] THEN 'weak_or_context'
  WHEN e.eventType = 'demerger' AND w.doc_type = 'reorganization_deed' THEN 'primary_authority'
  WHEN e.eventType = 'demerger' AND w.doc_type IN ['reorganization_resolution', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'demerger' AND w.doc_type IN ['registry_extract', 'legal_opinion'] THEN 'weak_or_context'
  WHEN e.eventType = 'asset-transfer' AND w.doc_type = 'intercompany_or_other_agreement' THEN 'primary_authority'
  WHEN e.eventType = 'asset-transfer' AND w.doc_type IN ['reorganization_deed', 'legal_declaration'] THEN 'fallback_authority'
  WHEN e.eventType = 'asset-transfer' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'intercompany-agreement' AND w.doc_type = 'intercompany_or_other_agreement' THEN 'primary_authority'
  WHEN e.eventType = 'intercompany-agreement' AND w.doc_type IN ['board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'intercompany-agreement' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'tax-ruling-request' AND w.doc_type = 'tax_document' THEN 'primary_authority'
  WHEN e.eventType = 'tax-ruling-request' AND w.doc_type IN ['correspondence'] THEN 'fallback_authority'
  WHEN e.eventType = 'tax-ruling-request' AND w.doc_type IN ['legal_opinion'] THEN 'weak_or_context'
  WHEN e.eventType = 'tax-ruling-grant' AND w.doc_type = 'tax_document' THEN 'primary_authority'
  WHEN e.eventType = 'tax-ruling-grant' AND w.doc_type IN ['administrative_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'tax-ruling-grant' AND w.doc_type IN ['legal_opinion'] THEN 'weak_or_context'
  WHEN e.eventType = 'tax-residence-attestation' AND w.doc_type = 'tax_document' THEN 'primary_authority'
  WHEN e.eventType = 'tax-residence-attestation' AND w.doc_type IN ['administrative_certificate', 'legal_declaration'] THEN 'fallback_authority'
  WHEN e.eventType = 'tax-residence-attestation' AND w.doc_type IN ['legal_opinion', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'annual-report-filing' AND w.doc_type = 'regulatory_filing' THEN 'primary_authority'
  WHEN e.eventType = 'annual-report-filing' AND w.doc_type IN ['annual_accounts_financial_statements', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'annual-report-filing' AND w.doc_type IN ['corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'annual-report-approval' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'annual-report-approval' AND w.doc_type IN ['shareholder_meeting_minutes', 'annual_accounts_financial_statements'] THEN 'fallback_authority'
  WHEN e.eventType = 'annual-report-approval' AND w.doc_type IN ['corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'notarial-certification' AND w.doc_type = 'administrative_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'notarial-certification' AND w.doc_type IN ['legal_declaration'] THEN 'fallback_authority'
  WHEN e.eventType = 'notarial-certification' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'apostille' AND w.doc_type = 'administrative_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'apostille' AND w.doc_type IN ['registry_extract_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'apostille' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'cancellation' AND w.doc_type = 'legal_declaration' THEN 'primary_authority'
  WHEN e.eventType = 'cancellation' AND w.doc_type IN ['board_resolution', 'shareholder_resolution', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'cancellation' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'recall-of-decision' AND w.doc_type = 'board_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'recall-of-decision' AND w.doc_type IN ['shareholder_resolution', 'legal_declaration', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'recall-of-decision' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'unclassified' AND w.doc_type = 'other' THEN 'primary_authority'
  WHEN e.eventType = 'unclassified' AND w.doc_type IN ['correspondence', 'corporate_data_sheet'] THEN 'weak_or_context'
  ELSE 'non_authoritative'
END AS source_authority_level,
     CASE
  WHEN w.doc_type IS NULL THEN 'missing_document'
  WHEN e.eventType IS NULL THEN 'unknown_event_type'
  WHEN NOT type(source_rel) IN ['RECORDS', 'EVIDENCES'] THEN 'mentioned_only'
  WHEN e.eventType = 'incorporation' AND w.doc_type = 'incorporation_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'incorporation' AND w.doc_type IN ['articles_of_association_or_bylaws'] THEN 'fallback_authority'
  WHEN e.eventType = 'incorporation' AND w.doc_type IN ['good_standing_certificate', 'registry_extract', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'constitutional-adoption' AND w.doc_type = 'articles_of_association_or_bylaws' THEN 'primary_authority'
  WHEN e.eventType = 'constitutional-adoption' AND w.doc_type IN ['incorporation_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'constitutional-adoption' AND w.doc_type IN ['registry_extract', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'articles-amendment' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'articles-amendment' AND w.doc_type IN ['articles_of_association_or_bylaws', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'articles-amendment' AND w.doc_type IN ['registry_extract', 'legal_opinion'] THEN 'weak_or_context'
  WHEN e.eventType = 'continuation-in' AND w.doc_type = 'continuation_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'continuation-in' AND w.doc_type IN ['registry_filing', 'redomiciliation_application'] THEN 'fallback_authority'
  WHEN e.eventType = 'continuation-in' AND w.doc_type IN ['registry_extract', 'good_standing_certificate'] THEN 'weak_or_context'
  WHEN e.eventType = 'continuation-out' AND w.doc_type = 'discontinuance_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'continuation-out' AND w.doc_type IN ['registry_filing', 'redomiciliation_application'] THEN 'fallback_authority'
  WHEN e.eventType = 'continuation-out' AND w.doc_type IN ['registry_extract', 'good_standing_certificate'] THEN 'weak_or_context'
  WHEN e.eventType = 'redomiciliation' AND w.doc_type = 'continuation_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'redomiciliation' AND w.doc_type IN ['discontinuance_certificate', 'redomiciliation_application', 'reorganization_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'redomiciliation' AND w.doc_type IN ['registry_extract', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'legal-form-conversion' AND w.doc_type = 'registry_filing' THEN 'primary_authority'
  WHEN e.eventType = 'legal-form-conversion' AND w.doc_type IN ['reorganization_deed', 'shareholder_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'legal-form-conversion' AND w.doc_type IN ['registry_extract', 'legal_opinion'] THEN 'weak_or_context'
  WHEN e.eventType = 'dissolution' AND w.doc_type = 'dissolution_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'dissolution' AND w.doc_type IN ['registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'dissolution' AND w.doc_type IN ['good_standing_certificate', 'registry_extract'] THEN 'weak_or_context'
  WHEN e.eventType = 'liquidation-start' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'liquidation-start' AND w.doc_type IN ['registry_filing', 'reorganization_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'liquidation-start' AND w.doc_type IN ['registry_extract', 'correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'liquidation-end' AND w.doc_type = 'dissolution_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'liquidation-end' AND w.doc_type IN ['registry_filing', 'administrative_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'liquidation-end' AND w.doc_type IN ['registry_extract', 'correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'striking-off' AND w.doc_type = 'administrative_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'striking-off' AND w.doc_type IN ['registry_filing', 'registry_extract_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'striking-off' AND w.doc_type IN ['registry_extract', 'correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'board-meeting' AND w.doc_type = 'board_meeting_minutes' THEN 'primary_authority'
  WHEN e.eventType = 'board-meeting' AND w.doc_type IN ['board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'board-meeting' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'board-resolution' AND w.doc_type = 'board_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'board-resolution' AND w.doc_type IN ['board_meeting_minutes'] THEN 'fallback_authority'
  WHEN e.eventType = 'board-resolution' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'shareholder-meeting' AND w.doc_type = 'shareholder_meeting_minutes' THEN 'primary_authority'
  WHEN e.eventType = 'shareholder-meeting' AND w.doc_type IN ['shareholder_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'shareholder-meeting' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'shareholder-resolution' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'shareholder-resolution' AND w.doc_type IN ['shareholder_meeting_minutes'] THEN 'fallback_authority'
  WHEN e.eventType = 'shareholder-resolution' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'director-appointment' AND w.doc_type = 'director_appointment' THEN 'primary_authority'
  WHEN e.eventType = 'director-appointment' AND w.doc_type IN ['board_resolution', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'director-appointment' AND w.doc_type IN ['registry_extract', 'good_standing_certificate', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'director-resignation' AND w.doc_type = 'director_resignation' THEN 'primary_authority'
  WHEN e.eventType = 'director-resignation' AND w.doc_type IN ['board_resolution', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'director-resignation' AND w.doc_type IN ['registry_extract', 'good_standing_certificate', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'officer-appointment' AND w.doc_type = 'board_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'officer-appointment' AND w.doc_type IN ['director_appointment', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'officer-appointment' AND w.doc_type IN ['registry_extract', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'officer-resignation' AND w.doc_type = 'board_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'officer-resignation' AND w.doc_type IN ['director_resignation', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'officer-resignation' AND w.doc_type IN ['registry_extract', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'auditor-appointment' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'auditor-appointment' AND w.doc_type IN ['board_resolution', 'engagement_letter'] THEN 'fallback_authority'
  WHEN e.eventType = 'auditor-appointment' AND w.doc_type IN ['annual_accounts_financial_statements', 'registry_extract'] THEN 'weak_or_context'
  WHEN e.eventType = 'share-issuance' AND w.doc_type = 'share_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'share-issuance' AND w.doc_type IN ['share_register', 'shareholder_resolution', 'board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'share-issuance' AND w.doc_type IN ['annual_accounts_financial_statements', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'share-allotment' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'share-allotment' AND w.doc_type IN ['board_resolution', 'share_register', 'share_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'share-allotment' AND w.doc_type IN ['corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'share-transfer' AND w.doc_type = 'share_transfer_agreement' THEN 'primary_authority'
  WHEN e.eventType = 'share-transfer' AND w.doc_type IN ['share_register', 'share_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'share-transfer' AND w.doc_type IN ['corporate_data_sheet', 'registry_extract'] THEN 'weak_or_context'
  WHEN e.eventType = 'share-cancellation' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'share-cancellation' AND w.doc_type IN ['share_register', 'share_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'share-cancellation' AND w.doc_type IN ['annual_accounts_financial_statements', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'capital-increase' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'capital-increase' AND w.doc_type IN ['registry_filing', 'share_register', 'share_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'capital-increase' AND w.doc_type IN ['annual_accounts_financial_statements', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'capital-reduction' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'capital-reduction' AND w.doc_type IN ['registry_filing', 'share_register'] THEN 'fallback_authority'
  WHEN e.eventType = 'capital-reduction' AND w.doc_type IN ['annual_accounts_financial_statements', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'capital-contribution-cash' AND w.doc_type = 'banking_payment_or_credit_record' THEN 'primary_authority'
  WHEN e.eventType = 'capital-contribution-cash' AND w.doc_type IN ['share_contribution_agreement', 'board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'capital-contribution-cash' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'capital-contribution-in-kind' AND w.doc_type = 'share_contribution_agreement' THEN 'primary_authority'
  WHEN e.eventType = 'capital-contribution-in-kind' AND w.doc_type IN ['reorganization_deed', 'legal_declaration', 'board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'capital-contribution-in-kind' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'dividend-declaration' AND w.doc_type = 'board_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'dividend-declaration' AND w.doc_type IN ['shareholder_resolution', 'board_meeting_minutes'] THEN 'fallback_authority'
  WHEN e.eventType = 'dividend-declaration' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'dividend-payment' AND w.doc_type = 'banking_payment_or_credit_record' THEN 'primary_authority'
  WHEN e.eventType = 'dividend-payment' AND w.doc_type IN ['legal_declaration'] THEN 'fallback_authority'
  WHEN e.eventType = 'dividend-payment' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'power-of-attorney-grant' AND w.doc_type = 'power_of_attorney' THEN 'primary_authority'
  WHEN e.eventType = 'power-of-attorney-grant' AND w.doc_type IN ['board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'power-of-attorney-grant' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'power-of-attorney-revocation' AND w.doc_type = 'power_of_attorney' THEN 'primary_authority'
  WHEN e.eventType = 'power-of-attorney-revocation' AND w.doc_type IN ['board_resolution', 'legal_declaration'] THEN 'fallback_authority'
  WHEN e.eventType = 'power-of-attorney-revocation' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'proxy-grant' AND w.doc_type = 'proxy' THEN 'primary_authority'
  WHEN e.eventType = 'proxy-grant' AND w.doc_type IN ['shareholder_meeting_minutes'] THEN 'fallback_authority'
  WHEN e.eventType = 'proxy-grant' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'loan-agreement' AND w.doc_type = 'intercompany_or_other_agreement' THEN 'primary_authority'
  WHEN e.eventType = 'loan-agreement' AND w.doc_type IN ['board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'loan-agreement' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'loan-repayment' AND w.doc_type = 'banking_payment_or_credit_record' THEN 'primary_authority'
  WHEN e.eventType = 'loan-repayment' AND w.doc_type IN ['legal_declaration'] THEN 'fallback_authority'
  WHEN e.eventType = 'loan-repayment' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'loan-forgiveness' AND w.doc_type = 'legal_declaration' THEN 'primary_authority'
  WHEN e.eventType = 'loan-forgiveness' AND w.doc_type IN ['intercompany_or_other_agreement', 'board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'loan-forgiveness' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'merger' AND w.doc_type = 'reorganization_deed' THEN 'primary_authority'
  WHEN e.eventType = 'merger' AND w.doc_type IN ['reorganization_resolution', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'merger' AND w.doc_type IN ['registry_extract', 'legal_opinion'] THEN 'weak_or_context'
  WHEN e.eventType = 'demerger' AND w.doc_type = 'reorganization_deed' THEN 'primary_authority'
  WHEN e.eventType = 'demerger' AND w.doc_type IN ['reorganization_resolution', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'demerger' AND w.doc_type IN ['registry_extract', 'legal_opinion'] THEN 'weak_or_context'
  WHEN e.eventType = 'asset-transfer' AND w.doc_type = 'intercompany_or_other_agreement' THEN 'primary_authority'
  WHEN e.eventType = 'asset-transfer' AND w.doc_type IN ['reorganization_deed', 'legal_declaration'] THEN 'fallback_authority'
  WHEN e.eventType = 'asset-transfer' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'intercompany-agreement' AND w.doc_type = 'intercompany_or_other_agreement' THEN 'primary_authority'
  WHEN e.eventType = 'intercompany-agreement' AND w.doc_type IN ['board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'intercompany-agreement' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'tax-ruling-request' AND w.doc_type = 'tax_document' THEN 'primary_authority'
  WHEN e.eventType = 'tax-ruling-request' AND w.doc_type IN ['correspondence'] THEN 'fallback_authority'
  WHEN e.eventType = 'tax-ruling-request' AND w.doc_type IN ['legal_opinion'] THEN 'weak_or_context'
  WHEN e.eventType = 'tax-ruling-grant' AND w.doc_type = 'tax_document' THEN 'primary_authority'
  WHEN e.eventType = 'tax-ruling-grant' AND w.doc_type IN ['administrative_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'tax-ruling-grant' AND w.doc_type IN ['legal_opinion'] THEN 'weak_or_context'
  WHEN e.eventType = 'tax-residence-attestation' AND w.doc_type = 'tax_document' THEN 'primary_authority'
  WHEN e.eventType = 'tax-residence-attestation' AND w.doc_type IN ['administrative_certificate', 'legal_declaration'] THEN 'fallback_authority'
  WHEN e.eventType = 'tax-residence-attestation' AND w.doc_type IN ['legal_opinion', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'annual-report-filing' AND w.doc_type = 'regulatory_filing' THEN 'primary_authority'
  WHEN e.eventType = 'annual-report-filing' AND w.doc_type IN ['annual_accounts_financial_statements', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'annual-report-filing' AND w.doc_type IN ['corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'annual-report-approval' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'annual-report-approval' AND w.doc_type IN ['shareholder_meeting_minutes', 'annual_accounts_financial_statements'] THEN 'fallback_authority'
  WHEN e.eventType = 'annual-report-approval' AND w.doc_type IN ['corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'notarial-certification' AND w.doc_type = 'administrative_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'notarial-certification' AND w.doc_type IN ['legal_declaration'] THEN 'fallback_authority'
  WHEN e.eventType = 'notarial-certification' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'apostille' AND w.doc_type = 'administrative_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'apostille' AND w.doc_type IN ['registry_extract_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'apostille' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'cancellation' AND w.doc_type = 'legal_declaration' THEN 'primary_authority'
  WHEN e.eventType = 'cancellation' AND w.doc_type IN ['board_resolution', 'shareholder_resolution', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'cancellation' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'recall-of-decision' AND w.doc_type = 'board_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'recall-of-decision' AND w.doc_type IN ['shareholder_resolution', 'legal_declaration', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'recall-of-decision' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'unclassified' AND w.doc_type = 'other' THEN 'primary_authority'
  WHEN e.eventType = 'unclassified' AND w.doc_type IN ['correspondence', 'corporate_data_sheet'] THEN 'weak_or_context'
  ELSE 'non_authoritative'
END AS source_authority_status,
     CASE
  WHEN e.eventType = 'incorporation' THEN 'incorporation_certificate'
  WHEN e.eventType = 'constitutional-adoption' THEN 'articles_of_association_or_bylaws'
  WHEN e.eventType = 'articles-amendment' THEN 'shareholder_resolution'
  WHEN e.eventType = 'continuation-in' THEN 'continuation_certificate'
  WHEN e.eventType = 'continuation-out' THEN 'discontinuance_certificate'
  WHEN e.eventType = 'redomiciliation' THEN 'continuation_certificate'
  WHEN e.eventType = 'legal-form-conversion' THEN 'registry_filing'
  WHEN e.eventType = 'dissolution' THEN 'dissolution_certificate'
  WHEN e.eventType = 'liquidation-start' THEN 'shareholder_resolution'
  WHEN e.eventType = 'liquidation-end' THEN 'dissolution_certificate'
  WHEN e.eventType = 'striking-off' THEN 'administrative_certificate'
  WHEN e.eventType = 'board-meeting' THEN 'board_meeting_minutes'
  WHEN e.eventType = 'board-resolution' THEN 'board_resolution'
  WHEN e.eventType = 'shareholder-meeting' THEN 'shareholder_meeting_minutes'
  WHEN e.eventType = 'shareholder-resolution' THEN 'shareholder_resolution'
  WHEN e.eventType = 'director-appointment' THEN 'director_appointment'
  WHEN e.eventType = 'director-resignation' THEN 'director_resignation'
  WHEN e.eventType = 'officer-appointment' THEN 'board_resolution'
  WHEN e.eventType = 'officer-resignation' THEN 'board_resolution'
  WHEN e.eventType = 'auditor-appointment' THEN 'shareholder_resolution'
  WHEN e.eventType = 'share-issuance' THEN 'share_certificate'
  WHEN e.eventType = 'share-allotment' THEN 'shareholder_resolution'
  WHEN e.eventType = 'share-transfer' THEN 'share_transfer_agreement'
  WHEN e.eventType = 'share-cancellation' THEN 'shareholder_resolution'
  WHEN e.eventType = 'capital-increase' THEN 'shareholder_resolution'
  WHEN e.eventType = 'capital-reduction' THEN 'shareholder_resolution'
  WHEN e.eventType = 'capital-contribution-cash' THEN 'banking_payment_or_credit_record'
  WHEN e.eventType = 'capital-contribution-in-kind' THEN 'share_contribution_agreement'
  WHEN e.eventType = 'dividend-declaration' THEN 'board_resolution'
  WHEN e.eventType = 'dividend-payment' THEN 'banking_payment_or_credit_record'
  WHEN e.eventType = 'power-of-attorney-grant' THEN 'power_of_attorney'
  WHEN e.eventType = 'power-of-attorney-revocation' THEN 'power_of_attorney'
  WHEN e.eventType = 'proxy-grant' THEN 'proxy'
  WHEN e.eventType = 'loan-agreement' THEN 'intercompany_or_other_agreement'
  WHEN e.eventType = 'loan-repayment' THEN 'banking_payment_or_credit_record'
  WHEN e.eventType = 'loan-forgiveness' THEN 'legal_declaration'
  WHEN e.eventType = 'merger' THEN 'reorganization_deed'
  WHEN e.eventType = 'demerger' THEN 'reorganization_deed'
  WHEN e.eventType = 'asset-transfer' THEN 'intercompany_or_other_agreement'
  WHEN e.eventType = 'intercompany-agreement' THEN 'intercompany_or_other_agreement'
  WHEN e.eventType = 'tax-ruling-request' THEN 'tax_document'
  WHEN e.eventType = 'tax-ruling-grant' THEN 'tax_document'
  WHEN e.eventType = 'tax-residence-attestation' THEN 'tax_document'
  WHEN e.eventType = 'annual-report-filing' THEN 'regulatory_filing'
  WHEN e.eventType = 'annual-report-approval' THEN 'shareholder_resolution'
  WHEN e.eventType = 'notarial-certification' THEN 'administrative_certificate'
  WHEN e.eventType = 'apostille' THEN 'administrative_certificate'
  WHEN e.eventType = 'cancellation' THEN 'legal_declaration'
  WHEN e.eventType = 'recall-of-decision' THEN 'board_resolution'
  WHEN e.eventType = 'unclassified' THEN 'other'
  ELSE NULL
END AS primary_document_type
WITH e, effective_date, subj, actor, undergoer, counterparty, amount,
     source_rel, w, item, source_authority_level, source_authority_status,
     primary_document_type,
     coalesce(source_rel.source_authority_rank, CASE
  WHEN source_authority_level = 'primary_authority' AND type(source_rel) IN ['RECORDS', 'EVIDENCES'] THEN 10
  WHEN source_authority_level = 'primary_authority' THEN 15
  WHEN source_authority_level = 'fallback_authority' AND type(source_rel) IN ['RECORDS', 'EVIDENCES'] THEN 20
  WHEN source_authority_level = 'fallback_authority' THEN 25
  WHEN source_authority_level = 'weak_or_context' AND type(source_rel) IN ['RECORDS', 'EVIDENCES'] THEN 30
  WHEN source_authority_level = 'weak_or_context' THEN 35
  WHEN source_authority_level = 'unknown_event_type' THEN 80
  WHEN source_authority_level = 'missing_document' THEN 90
  WHEN type(source_rel) IN ['RECORDS', 'EVIDENCES'] THEN 60
  ELSE 65
END) AS source_authority_rank
WHERE
  $include_cancelled
  OR source_rel IS NULL
  OR (
    coalesce(w.lifecycle_status, 'active') = 'active'
    AND coalesce(item.lifecycle_status, 'active') = 'active'
  )
ORDER BY source_authority_rank, item.inbox_filename
WITH e, effective_date, subj,
     [label IN collect(DISTINCT actor.label) WHERE label IS NOT NULL] AS acting_parties,
     [label IN collect(DISTINCT undergoer.label) WHERE label IS NOT NULL] AS affected_parties,
     [label IN collect(DISTINCT counterparty.label) WHERE label IS NOT NULL] AS counterparties,
     head([value IN collect(DISTINCT amount.amount) WHERE value IS NOT NULL]) AS amount,
     head([value IN collect(DISTINCT amount.currency) WHERE value IS NOT NULL]) AS currency,
     head([value IN collect(DISTINCT amount.entityId) WHERE value IS NOT NULL]) AS monetary_amount_id,
     [source IN collect(DISTINCT
        CASE WHEN item.inbox_filename IS NULL THEN NULL ELSE {
          file: item.inbox_filename,
          chunk_id: CASE WHEN item.inbox_filename = e.source_doc
                         THEN e.source_chunk ELSE NULL END,
          doc_type: w.doc_type,
          link_type: type(source_rel),
          authority_level: source_authority_level,
          authority_status: source_authority_status,
          authority_rank: source_authority_rank,
          is_best_event_source: coalesce(source_rel.is_best_event_source, false)
        } END) WHERE source IS NOT NULL] AS sources,
     [title IN collect(DISTINCT w.title) WHERE title IS NOT NULL] AS source_documents,
     collect(DISTINCT source_authority_status) AS source_authority_statuses,
     primary_document_type
WITH e, effective_date, subj, acting_parties, affected_parties, counterparties,
     amount, currency, monetary_amount_id, sources, source_documents, primary_document_type,
     CASE
       WHEN 'primary_authority' IN source_authority_statuses THEN 'primary_authority'
       WHEN 'fallback_authority' IN source_authority_statuses THEN 'fallback_authority'
       WHEN 'weak_or_context' IN source_authority_statuses THEN 'weak_or_context'
       WHEN 'mentioned_only' IN source_authority_statuses THEN 'mentioned_only'
       WHEN 'missing_document' IN source_authority_statuses THEN 'missing_document'
       ELSE 'non_authoritative'
     END AS authority_status
WITH e, effective_date, subj, acting_parties, affected_parties, counterparties,
     amount, currency, monetary_amount_id, sources, source_documents, primary_document_type,
     authority_status,
     CASE
       WHEN e.eventType = 'incorporation'
         AND effective_date IS NOT NULL
         AND size(affected_parties) = 1
         THEN 'incorporation|' + effective_date + '|' + head(affected_parties)
       ELSE e.entityId
     END AS dedupe_key,
     size(acting_parties) + size(affected_parties) + size(counterparties)
       + CASE WHEN amount IS NULL THEN 0 ELSE 1 END AS row_score
ORDER BY dedupe_key, row_score DESC, e.label, e.entityId
WITH dedupe_key,
     collect({
       subject: subj.label,
       effective_date: effective_date,
       event: e.label,
       event_type: e.eventType,
       acting_parties: acting_parties,
       affected_parties: affected_parties,
       counterparties: counterparties,
       amount: amount,
       currency: currency,
       monetary_amount_id: monetary_amount_id,
       primary_document_type: primary_document_type,
       authority_status: authority_status,
       sources: sources,
       source_documents: source_documents,
       event_id: e.entityId
     })[0] AS row
RETURN row.subject               AS subject,
       row.effective_date        AS effective_date,
       row.event                 AS event,
       row.event_type            AS event_type,
       row.acting_parties        AS acting_parties,
       row.affected_parties      AS affected_parties,
       row.counterparties        AS counterparties,
       row.amount                AS amount,
       row.currency              AS currency,
       row.monetary_amount_id    AS monetary_amount_id,
       row.primary_document_type AS primary_document_type,
       row.authority_status      AS authority_status,
       row.source_documents      AS source_documents,
       row.sources               AS sources,
       row.event_id              AS event_id
ORDER BY effective_date DESC, event DESC
LIMIT toInteger($limit)
""".strip()

POA_REGISTER = r"""
WITH coalesce($subject_id, '') AS subject_id,
     coalesce($involves_person_id, '') AS involves_person_id,
     coalesce($involves_organization_id, '') AS involves_organization_id
WITH subject_id, involves_person_id, involves_organization_id,
     subject_id <> '' AS has_subject,
     involves_person_id <> '' AS has_person,
     involves_organization_id <> '' AS has_org
MATCH (poa:Entity:PowerOfAttorney)
WHERE ($include_cancelled OR coalesce(poa.lifecycle_status, 'active') = 'active')
  AND (NOT has_subject OR EXISTS {
    MATCH (s:BusinessSubject {subjectId: subject_id})-[:HAS_PHASE]->(phase:Entity)
    WHERE (poa)-[:HAS_AUTHORIZING_PARTY]->(phase)
       OR (poa)-[:CONCERNS_ORGANIZATION]->(phase)
       OR EXISTS {
            MATCH (expr:Expression)-[:MENTIONS|RECORDS]->(poa)
            WHERE EXISTS { (expr)-[:MENTIONS|RECORDS|DESIGNATES_SIGNATORY]->(phase) }
          }
  })
MATCH (s:BusinessSubject)-[:HAS_PHASE]->(phase:Entity)
WHERE (poa)-[:HAS_AUTHORIZING_PARTY]->(phase)
   OR (poa)-[:CONCERNS_ORGANIZATION]->(phase)
   OR EXISTS {
        MATCH (expr:Expression)-[:MENTIONS|RECORDS]->(poa)
        WHERE EXISTS { (expr)-[:MENTIONS|RECORDS|DESIGNATES_SIGNATORY]->(phase) }
      }
  AND (NOT has_subject OR s.subjectId = subject_id)
  AND (poa.valid_from IS NULL
       OR poa.valid_from <= coalesce(phase.phase_valid_to, toString(date())))
  AND (poa.valid_to IS NULL
       OR poa.valid_to >= coalesce(phase.phase_valid_from, '0000-01-01'))
WITH DISTINCT s, phase, poa,
              involves_person_id, involves_organization_id,
              has_person, has_org
WHERE (NOT has_person OR EXISTS {
    MATCH (poa)-[:IS_CONFERRED_ON]->(p:Entity {entityId: involves_person_id})
  })
  AND (NOT has_org OR EXISTS {
    MATCH (poa)-[:HAS_CONFERRED_ON_ORGANIZATION|HAS_AUTHORIZING_PARTY|CONCERNS_ORGANIZATION]
          ->(o:Entity {entityId: involves_organization_id})
  })
OPTIONAL MATCH (poa)-[:IS_CONFERRED_ON]->(person:Person)
OPTIONAL MATCH (poa)-[:HAS_CONFERRED_ON_ORGANIZATION]->(org:Entity)
OPTIONAL MATCH (poa)-[:HAS_AUTHORIZING_PARTY]->(princ:Entity)
OPTIONAL MATCH (poa)-[:CONCERNS_ORGANIZATION]->(concerns:Entity)
WITH s, phase, poa,
     [p  IN collect(DISTINCT person)   WHERE p  IS NOT NULL | p.label]  AS grantee_persons,
     [o  IN collect(DISTINCT org)      WHERE o  IS NOT NULL | o.label]  AS firm_grantees,
     [pr IN collect(DISTINCT princ)    WHERE pr IS NOT NULL | pr.label] AS authorizing_parties,
     [c  IN collect(DISTINCT concerns) WHERE c  IS NOT NULL | c.label]  AS concerned_organizations
OPTIONAL MATCH (expr2:Expression)-[:RECORDS|MENTIONS]->(poa)
OPTIONAL MATCH (expr2)<-[:HAS_REALIZATION]-(w:Work)
OPTIONAL MATCH (expr2)-[:HAS_EMBODIMENT]->(:Manifestation)-[:HAS_EXEMPLAR]->(item:Item)
WITH s, phase, poa,
     grantee_persons, firm_grantees,
     authorizing_parties, concerned_organizations,
     collect(DISTINCT w.title)             AS supporting_titles,
     collect(DISTINCT item.inbox_filename) AS supporting_files
WITH s, phase, poa,
     grantee_persons, firm_grantees,
     authorizing_parties, concerned_organizations,
     supporting_titles,
     CASE
       WHEN poa.source_doc IS NOT NULL
         THEN [{file: poa.source_doc, chunk_id: poa.source_chunk}]
              + [f IN supporting_files
                 WHERE f IS NOT NULL AND f <> poa.source_doc
                 | {file: f, chunk_id: null}]
       ELSE [f IN supporting_files
             WHERE f IS NOT NULL
             | {file: f, chunk_id: null}]
     END AS sources
RETURN s.label                  AS subject,
       phase.entityId           AS phase_id,
       phase.label              AS phase,
       phase.phase_valid_from   AS phase_valid_from,
       phase.phase_valid_to     AS phase_valid_to,
       poa.entityId             AS poa_id,
       poa.label                AS poa_label,
       poa.scope                AS scope,
       poa.signature_mode       AS signature_mode,
       poa.valid_from           AS valid_from,
       poa.valid_to             AS valid_to,
       poa.valid_to_event_id    AS valid_to_event_id,
       poa.lifecycle_status     AS lifecycle_status,
       poa.revocation_terms     AS revocation_terms,
       poa.grounding_quote      AS grounding_quote,
       grantee_persons          AS grantee_persons,
       firm_grantees            AS firm_grantees,
       authorizing_parties      AS authorizing_parties,
       concerned_organizations  AS concerned_organizations,
       supporting_titles        AS supporting_titles,
       sources                  AS sources
ORDER BY CASE lifecycle_status WHEN 'active' THEN 0 ELSE 1 END,
         coalesce(poa.valid_from, '') DESC, poa.label
""".strip()

EVENTS_TIMELINE = r"""
MATCH (e:Entity:Event)
OPTIONAL MATCH (e)-[:HAS_EFFECTIVE_DATE]->(d:Entity:Date)
WITH e, coalesce(toString(d.iso_date), e.effectiveDate) AS effective_date
WHERE
  ($since IS NULL OR effective_date >= $since)
  AND ($until IS NULL OR effective_date <= $until)
  AND (
    size(coalesce($event_type, [])) = 0 OR
    e.eventType IN $event_type
  )
  AND (
    size(coalesce($event_domain, [])) = 0 OR
    CASE
  WHEN e.eventType = 'incorporation' THEN 'corporate_lifecycle'
  WHEN e.eventType = 'constitutional-adoption' THEN 'constitutional_governance'
  WHEN e.eventType = 'articles-amendment' THEN 'constitutional_governance'
  WHEN e.eventType = 'continuation-in' THEN 'corporate_lifecycle'
  WHEN e.eventType = 'continuation-out' THEN 'corporate_lifecycle'
  WHEN e.eventType = 'redomiciliation' THEN 'corporate_lifecycle'
  WHEN e.eventType = 'legal-form-conversion' THEN 'corporate_lifecycle'
  WHEN e.eventType = 'dissolution' THEN 'corporate_lifecycle'
  WHEN e.eventType = 'liquidation-start' THEN 'corporate_lifecycle'
  WHEN e.eventType = 'liquidation-end' THEN 'corporate_lifecycle'
  WHEN e.eventType = 'striking-off' THEN 'corporate_lifecycle'
  WHEN e.eventType = 'board-meeting' THEN 'constitutional_governance'
  WHEN e.eventType = 'board-resolution' THEN 'constitutional_governance'
  WHEN e.eventType = 'shareholder-meeting' THEN 'constitutional_governance'
  WHEN e.eventType = 'shareholder-resolution' THEN 'constitutional_governance'
  WHEN e.eventType = 'director-appointment' THEN 'officers_and_roles'
  WHEN e.eventType = 'director-resignation' THEN 'officers_and_roles'
  WHEN e.eventType = 'officer-appointment' THEN 'officers_and_roles'
  WHEN e.eventType = 'officer-resignation' THEN 'officers_and_roles'
  WHEN e.eventType = 'auditor-appointment' THEN 'officers_and_roles'
  WHEN e.eventType = 'share-issuance' THEN 'capital_and_shares'
  WHEN e.eventType = 'share-allotment' THEN 'capital_and_shares'
  WHEN e.eventType = 'share-transfer' THEN 'capital_and_shares'
  WHEN e.eventType = 'share-cancellation' THEN 'capital_and_shares'
  WHEN e.eventType = 'capital-increase' THEN 'capital_and_shares'
  WHEN e.eventType = 'capital-reduction' THEN 'capital_and_shares'
  WHEN e.eventType = 'capital-contribution-cash' THEN 'capital_and_shares'
  WHEN e.eventType = 'capital-contribution-in-kind' THEN 'capital_and_shares'
  WHEN e.eventType = 'dividend-declaration' THEN 'distributions'
  WHEN e.eventType = 'dividend-payment' THEN 'distributions'
  WHEN e.eventType = 'power-of-attorney-grant' THEN 'authority_and_representation'
  WHEN e.eventType = 'power-of-attorney-revocation' THEN 'authority_and_representation'
  WHEN e.eventType = 'proxy-grant' THEN 'authority_and_representation'
  WHEN e.eventType = 'loan-agreement' THEN 'finance_and_treasury'
  WHEN e.eventType = 'loan-repayment' THEN 'finance_and_treasury'
  WHEN e.eventType = 'loan-forgiveness' THEN 'finance_and_treasury'
  WHEN e.eventType = 'merger' THEN 'reorganization_and_transactions'
  WHEN e.eventType = 'demerger' THEN 'reorganization_and_transactions'
  WHEN e.eventType = 'asset-transfer' THEN 'reorganization_and_transactions'
  WHEN e.eventType = 'intercompany-agreement' THEN 'reorganization_and_transactions'
  WHEN e.eventType = 'tax-ruling-request' THEN 'tax_and_regulatory'
  WHEN e.eventType = 'tax-ruling-grant' THEN 'tax_and_regulatory'
  WHEN e.eventType = 'tax-residence-attestation' THEN 'tax_and_regulatory'
  WHEN e.eventType = 'annual-report-filing' THEN 'tax_and_regulatory'
  WHEN e.eventType = 'annual-report-approval' THEN 'tax_and_regulatory'
  WHEN e.eventType = 'notarial-certification' THEN 'formalities'
  WHEN e.eventType = 'apostille' THEN 'formalities'
  WHEN e.eventType = 'cancellation' THEN 'meta_quality'
  WHEN e.eventType = 'recall-of-decision' THEN 'meta_quality'
  WHEN e.eventType = 'unclassified' THEN 'meta_quality'
  ELSE 'unknown'
END IN $event_domain
  )
  AND (
    $q IS NULL OR $q = '' OR
    toLower(coalesce(e.label, '')) CONTAINS toLower($q)
    OR toLower(coalesce(e.eventType, '')) CONTAINS toLower($q)
  )
  AND (
    $subject_id IS NULL OR $subject_id = ''
    OR EXISTS {
      MATCH (s:BusinessSubject {subjectId: $subject_id})-[:HAS_PHASE]->(phase:Entity)
      MATCH (e)-[r]->(phase)
      WHERE type(r) IN ['HAS_ACTOR', 'HAS_UNDERGOER', 'HAS_COUNTERPARTY',
                        'INVOLVES_CONTROLLED_THING', 'RELATED_ENDEAVOUR']
        AND (
          effective_date IS NULL
          OR (
            (phase.phase_valid_from IS NULL OR effective_date >= phase.phase_valid_from)
            AND effective_date <= coalesce(phase.phase_valid_to, toString(date()))
          )
        )
    }
  )
  AND (
    $participant_id IS NULL OR $participant_id = ''
    OR EXISTS {
      MATCH (e)-[:HAS_ACTOR|HAS_UNDERGOER]->(:Entity:LegalEntity {entityId: $participant_id})
    }
  )
  AND (
    $file IS NULL OR $file = ''
    OR EXISTS {
      MATCH (file_expr:Expression)-[:MENTIONS|RECORDS|EVIDENCES]->(e)
      MATCH (file_expr)-[:HAS_EMBODIMENT]->(:Manifestation)-[:HAS_EXEMPLAR]->(file_item:Item)
      WHERE file_item.item_id = $file OR file_item.inbox_filename = $file
    }
    OR EXISTS {
      MATCH (file_chunk:Chunk)-[:EVIDENCES]->(e)
      MATCH (file_chunk)<-[:HAS_PART]-(file_expr2:Expression)
      MATCH (file_expr2)-[:HAS_EMBODIMENT]->(:Manifestation)-[:HAS_EXEMPLAR]->(file_item2:Item)
      WHERE file_item2.item_id = $file OR file_item2.inbox_filename = $file
    }
  )
OPTIONAL MATCH (subj:BusinessSubject {subjectId: $subject_id})
WITH DISTINCT e, effective_date, subj
OPTIONAL MATCH (e)-[:HAS_ACTOR]->(actor:Entity)
OPTIONAL MATCH (e)-[:HAS_UNDERGOER]->(under:Entity)
OPTIONAL MATCH (e)-[:HAS_COUNTERPARTY]->(cp:Entity)
OPTIONAL MATCH (e)-[:HAS_NOTIONAL_AMOUNT]->(amt:Entity)
OPTIONAL MATCH (src:Expression)-[source_rel:RECORDS|MENTIONS|EVIDENCES]->(e)
OPTIONAL MATCH (src)<-[:HAS_REALIZATION]-(w:Work)
OPTIONAL MATCH (src)-[:HAS_EMBODIMENT]->(:Manifestation)-[:HAS_EXEMPLAR]->(item:Item)
WITH e, effective_date, actor, under, cp, amt, src, source_rel, w, item, subj
WITH e, effective_date, actor, under, cp, amt, src, source_rel, w, item, subj,
     CASE
  WHEN w.doc_type IS NULL THEN 'missing_document'
  WHEN e.eventType IS NULL THEN 'unknown_event_type'
  WHEN e.eventType = 'incorporation' AND w.doc_type = 'incorporation_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'incorporation' AND w.doc_type IN ['articles_of_association_or_bylaws'] THEN 'fallback_authority'
  WHEN e.eventType = 'incorporation' AND w.doc_type IN ['good_standing_certificate', 'registry_extract', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'constitutional-adoption' AND w.doc_type = 'articles_of_association_or_bylaws' THEN 'primary_authority'
  WHEN e.eventType = 'constitutional-adoption' AND w.doc_type IN ['incorporation_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'constitutional-adoption' AND w.doc_type IN ['registry_extract', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'articles-amendment' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'articles-amendment' AND w.doc_type IN ['articles_of_association_or_bylaws', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'articles-amendment' AND w.doc_type IN ['registry_extract', 'legal_opinion'] THEN 'weak_or_context'
  WHEN e.eventType = 'continuation-in' AND w.doc_type = 'continuation_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'continuation-in' AND w.doc_type IN ['registry_filing', 'redomiciliation_application'] THEN 'fallback_authority'
  WHEN e.eventType = 'continuation-in' AND w.doc_type IN ['registry_extract', 'good_standing_certificate'] THEN 'weak_or_context'
  WHEN e.eventType = 'continuation-out' AND w.doc_type = 'discontinuance_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'continuation-out' AND w.doc_type IN ['registry_filing', 'redomiciliation_application'] THEN 'fallback_authority'
  WHEN e.eventType = 'continuation-out' AND w.doc_type IN ['registry_extract', 'good_standing_certificate'] THEN 'weak_or_context'
  WHEN e.eventType = 'redomiciliation' AND w.doc_type = 'continuation_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'redomiciliation' AND w.doc_type IN ['discontinuance_certificate', 'redomiciliation_application', 'reorganization_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'redomiciliation' AND w.doc_type IN ['registry_extract', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'legal-form-conversion' AND w.doc_type = 'registry_filing' THEN 'primary_authority'
  WHEN e.eventType = 'legal-form-conversion' AND w.doc_type IN ['reorganization_deed', 'shareholder_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'legal-form-conversion' AND w.doc_type IN ['registry_extract', 'legal_opinion'] THEN 'weak_or_context'
  WHEN e.eventType = 'dissolution' AND w.doc_type = 'dissolution_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'dissolution' AND w.doc_type IN ['registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'dissolution' AND w.doc_type IN ['good_standing_certificate', 'registry_extract'] THEN 'weak_or_context'
  WHEN e.eventType = 'liquidation-start' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'liquidation-start' AND w.doc_type IN ['registry_filing', 'reorganization_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'liquidation-start' AND w.doc_type IN ['registry_extract', 'correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'liquidation-end' AND w.doc_type = 'dissolution_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'liquidation-end' AND w.doc_type IN ['registry_filing', 'administrative_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'liquidation-end' AND w.doc_type IN ['registry_extract', 'correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'striking-off' AND w.doc_type = 'administrative_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'striking-off' AND w.doc_type IN ['registry_filing', 'registry_extract_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'striking-off' AND w.doc_type IN ['registry_extract', 'correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'board-meeting' AND w.doc_type = 'board_meeting_minutes' THEN 'primary_authority'
  WHEN e.eventType = 'board-meeting' AND w.doc_type IN ['board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'board-meeting' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'board-resolution' AND w.doc_type = 'board_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'board-resolution' AND w.doc_type IN ['board_meeting_minutes'] THEN 'fallback_authority'
  WHEN e.eventType = 'board-resolution' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'shareholder-meeting' AND w.doc_type = 'shareholder_meeting_minutes' THEN 'primary_authority'
  WHEN e.eventType = 'shareholder-meeting' AND w.doc_type IN ['shareholder_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'shareholder-meeting' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'shareholder-resolution' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'shareholder-resolution' AND w.doc_type IN ['shareholder_meeting_minutes'] THEN 'fallback_authority'
  WHEN e.eventType = 'shareholder-resolution' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'director-appointment' AND w.doc_type = 'director_appointment' THEN 'primary_authority'
  WHEN e.eventType = 'director-appointment' AND w.doc_type IN ['board_resolution', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'director-appointment' AND w.doc_type IN ['registry_extract', 'good_standing_certificate', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'director-resignation' AND w.doc_type = 'director_resignation' THEN 'primary_authority'
  WHEN e.eventType = 'director-resignation' AND w.doc_type IN ['board_resolution', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'director-resignation' AND w.doc_type IN ['registry_extract', 'good_standing_certificate', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'officer-appointment' AND w.doc_type = 'board_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'officer-appointment' AND w.doc_type IN ['director_appointment', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'officer-appointment' AND w.doc_type IN ['registry_extract', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'officer-resignation' AND w.doc_type = 'board_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'officer-resignation' AND w.doc_type IN ['director_resignation', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'officer-resignation' AND w.doc_type IN ['registry_extract', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'auditor-appointment' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'auditor-appointment' AND w.doc_type IN ['board_resolution', 'engagement_letter'] THEN 'fallback_authority'
  WHEN e.eventType = 'auditor-appointment' AND w.doc_type IN ['annual_accounts_financial_statements', 'registry_extract'] THEN 'weak_or_context'
  WHEN e.eventType = 'share-issuance' AND w.doc_type = 'share_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'share-issuance' AND w.doc_type IN ['share_register', 'shareholder_resolution', 'board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'share-issuance' AND w.doc_type IN ['annual_accounts_financial_statements', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'share-allotment' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'share-allotment' AND w.doc_type IN ['board_resolution', 'share_register', 'share_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'share-allotment' AND w.doc_type IN ['corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'share-transfer' AND w.doc_type = 'share_transfer_agreement' THEN 'primary_authority'
  WHEN e.eventType = 'share-transfer' AND w.doc_type IN ['share_register', 'share_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'share-transfer' AND w.doc_type IN ['corporate_data_sheet', 'registry_extract'] THEN 'weak_or_context'
  WHEN e.eventType = 'share-cancellation' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'share-cancellation' AND w.doc_type IN ['share_register', 'share_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'share-cancellation' AND w.doc_type IN ['annual_accounts_financial_statements', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'capital-increase' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'capital-increase' AND w.doc_type IN ['registry_filing', 'share_register', 'share_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'capital-increase' AND w.doc_type IN ['annual_accounts_financial_statements', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'capital-reduction' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'capital-reduction' AND w.doc_type IN ['registry_filing', 'share_register'] THEN 'fallback_authority'
  WHEN e.eventType = 'capital-reduction' AND w.doc_type IN ['annual_accounts_financial_statements', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'capital-contribution-cash' AND w.doc_type = 'banking_payment_or_credit_record' THEN 'primary_authority'
  WHEN e.eventType = 'capital-contribution-cash' AND w.doc_type IN ['share_contribution_agreement', 'board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'capital-contribution-cash' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'capital-contribution-in-kind' AND w.doc_type = 'share_contribution_agreement' THEN 'primary_authority'
  WHEN e.eventType = 'capital-contribution-in-kind' AND w.doc_type IN ['reorganization_deed', 'legal_declaration', 'board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'capital-contribution-in-kind' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'dividend-declaration' AND w.doc_type = 'board_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'dividend-declaration' AND w.doc_type IN ['shareholder_resolution', 'board_meeting_minutes'] THEN 'fallback_authority'
  WHEN e.eventType = 'dividend-declaration' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'dividend-payment' AND w.doc_type = 'banking_payment_or_credit_record' THEN 'primary_authority'
  WHEN e.eventType = 'dividend-payment' AND w.doc_type IN ['legal_declaration'] THEN 'fallback_authority'
  WHEN e.eventType = 'dividend-payment' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'power-of-attorney-grant' AND w.doc_type = 'power_of_attorney' THEN 'primary_authority'
  WHEN e.eventType = 'power-of-attorney-grant' AND w.doc_type IN ['board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'power-of-attorney-grant' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'power-of-attorney-revocation' AND w.doc_type = 'power_of_attorney' THEN 'primary_authority'
  WHEN e.eventType = 'power-of-attorney-revocation' AND w.doc_type IN ['board_resolution', 'legal_declaration'] THEN 'fallback_authority'
  WHEN e.eventType = 'power-of-attorney-revocation' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'proxy-grant' AND w.doc_type = 'proxy' THEN 'primary_authority'
  WHEN e.eventType = 'proxy-grant' AND w.doc_type IN ['shareholder_meeting_minutes'] THEN 'fallback_authority'
  WHEN e.eventType = 'proxy-grant' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'loan-agreement' AND w.doc_type = 'intercompany_or_other_agreement' THEN 'primary_authority'
  WHEN e.eventType = 'loan-agreement' AND w.doc_type IN ['board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'loan-agreement' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'loan-repayment' AND w.doc_type = 'banking_payment_or_credit_record' THEN 'primary_authority'
  WHEN e.eventType = 'loan-repayment' AND w.doc_type IN ['legal_declaration'] THEN 'fallback_authority'
  WHEN e.eventType = 'loan-repayment' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'loan-forgiveness' AND w.doc_type = 'legal_declaration' THEN 'primary_authority'
  WHEN e.eventType = 'loan-forgiveness' AND w.doc_type IN ['intercompany_or_other_agreement', 'board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'loan-forgiveness' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'merger' AND w.doc_type = 'reorganization_deed' THEN 'primary_authority'
  WHEN e.eventType = 'merger' AND w.doc_type IN ['reorganization_resolution', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'merger' AND w.doc_type IN ['registry_extract', 'legal_opinion'] THEN 'weak_or_context'
  WHEN e.eventType = 'demerger' AND w.doc_type = 'reorganization_deed' THEN 'primary_authority'
  WHEN e.eventType = 'demerger' AND w.doc_type IN ['reorganization_resolution', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'demerger' AND w.doc_type IN ['registry_extract', 'legal_opinion'] THEN 'weak_or_context'
  WHEN e.eventType = 'asset-transfer' AND w.doc_type = 'intercompany_or_other_agreement' THEN 'primary_authority'
  WHEN e.eventType = 'asset-transfer' AND w.doc_type IN ['reorganization_deed', 'legal_declaration'] THEN 'fallback_authority'
  WHEN e.eventType = 'asset-transfer' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'intercompany-agreement' AND w.doc_type = 'intercompany_or_other_agreement' THEN 'primary_authority'
  WHEN e.eventType = 'intercompany-agreement' AND w.doc_type IN ['board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'intercompany-agreement' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'tax-ruling-request' AND w.doc_type = 'tax_document' THEN 'primary_authority'
  WHEN e.eventType = 'tax-ruling-request' AND w.doc_type IN ['correspondence'] THEN 'fallback_authority'
  WHEN e.eventType = 'tax-ruling-request' AND w.doc_type IN ['legal_opinion'] THEN 'weak_or_context'
  WHEN e.eventType = 'tax-ruling-grant' AND w.doc_type = 'tax_document' THEN 'primary_authority'
  WHEN e.eventType = 'tax-ruling-grant' AND w.doc_type IN ['administrative_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'tax-ruling-grant' AND w.doc_type IN ['legal_opinion'] THEN 'weak_or_context'
  WHEN e.eventType = 'tax-residence-attestation' AND w.doc_type = 'tax_document' THEN 'primary_authority'
  WHEN e.eventType = 'tax-residence-attestation' AND w.doc_type IN ['administrative_certificate', 'legal_declaration'] THEN 'fallback_authority'
  WHEN e.eventType = 'tax-residence-attestation' AND w.doc_type IN ['legal_opinion', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'annual-report-filing' AND w.doc_type = 'regulatory_filing' THEN 'primary_authority'
  WHEN e.eventType = 'annual-report-filing' AND w.doc_type IN ['annual_accounts_financial_statements', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'annual-report-filing' AND w.doc_type IN ['corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'annual-report-approval' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'annual-report-approval' AND w.doc_type IN ['shareholder_meeting_minutes', 'annual_accounts_financial_statements'] THEN 'fallback_authority'
  WHEN e.eventType = 'annual-report-approval' AND w.doc_type IN ['corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'notarial-certification' AND w.doc_type = 'administrative_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'notarial-certification' AND w.doc_type IN ['legal_declaration'] THEN 'fallback_authority'
  WHEN e.eventType = 'notarial-certification' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'apostille' AND w.doc_type = 'administrative_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'apostille' AND w.doc_type IN ['registry_extract_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'apostille' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'cancellation' AND w.doc_type = 'legal_declaration' THEN 'primary_authority'
  WHEN e.eventType = 'cancellation' AND w.doc_type IN ['board_resolution', 'shareholder_resolution', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'cancellation' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'recall-of-decision' AND w.doc_type = 'board_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'recall-of-decision' AND w.doc_type IN ['shareholder_resolution', 'legal_declaration', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'recall-of-decision' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'unclassified' AND w.doc_type = 'other' THEN 'primary_authority'
  WHEN e.eventType = 'unclassified' AND w.doc_type IN ['correspondence', 'corporate_data_sheet'] THEN 'weak_or_context'
  ELSE 'non_authoritative'
END AS source_authority_level,
     CASE
  WHEN w.doc_type IS NULL THEN 'missing_document'
  WHEN e.eventType IS NULL THEN 'unknown_event_type'
  WHEN NOT type(source_rel) IN ['RECORDS', 'EVIDENCES'] THEN 'mentioned_only'
  WHEN e.eventType = 'incorporation' AND w.doc_type = 'incorporation_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'incorporation' AND w.doc_type IN ['articles_of_association_or_bylaws'] THEN 'fallback_authority'
  WHEN e.eventType = 'incorporation' AND w.doc_type IN ['good_standing_certificate', 'registry_extract', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'constitutional-adoption' AND w.doc_type = 'articles_of_association_or_bylaws' THEN 'primary_authority'
  WHEN e.eventType = 'constitutional-adoption' AND w.doc_type IN ['incorporation_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'constitutional-adoption' AND w.doc_type IN ['registry_extract', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'articles-amendment' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'articles-amendment' AND w.doc_type IN ['articles_of_association_or_bylaws', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'articles-amendment' AND w.doc_type IN ['registry_extract', 'legal_opinion'] THEN 'weak_or_context'
  WHEN e.eventType = 'continuation-in' AND w.doc_type = 'continuation_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'continuation-in' AND w.doc_type IN ['registry_filing', 'redomiciliation_application'] THEN 'fallback_authority'
  WHEN e.eventType = 'continuation-in' AND w.doc_type IN ['registry_extract', 'good_standing_certificate'] THEN 'weak_or_context'
  WHEN e.eventType = 'continuation-out' AND w.doc_type = 'discontinuance_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'continuation-out' AND w.doc_type IN ['registry_filing', 'redomiciliation_application'] THEN 'fallback_authority'
  WHEN e.eventType = 'continuation-out' AND w.doc_type IN ['registry_extract', 'good_standing_certificate'] THEN 'weak_or_context'
  WHEN e.eventType = 'redomiciliation' AND w.doc_type = 'continuation_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'redomiciliation' AND w.doc_type IN ['discontinuance_certificate', 'redomiciliation_application', 'reorganization_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'redomiciliation' AND w.doc_type IN ['registry_extract', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'legal-form-conversion' AND w.doc_type = 'registry_filing' THEN 'primary_authority'
  WHEN e.eventType = 'legal-form-conversion' AND w.doc_type IN ['reorganization_deed', 'shareholder_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'legal-form-conversion' AND w.doc_type IN ['registry_extract', 'legal_opinion'] THEN 'weak_or_context'
  WHEN e.eventType = 'dissolution' AND w.doc_type = 'dissolution_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'dissolution' AND w.doc_type IN ['registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'dissolution' AND w.doc_type IN ['good_standing_certificate', 'registry_extract'] THEN 'weak_or_context'
  WHEN e.eventType = 'liquidation-start' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'liquidation-start' AND w.doc_type IN ['registry_filing', 'reorganization_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'liquidation-start' AND w.doc_type IN ['registry_extract', 'correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'liquidation-end' AND w.doc_type = 'dissolution_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'liquidation-end' AND w.doc_type IN ['registry_filing', 'administrative_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'liquidation-end' AND w.doc_type IN ['registry_extract', 'correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'striking-off' AND w.doc_type = 'administrative_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'striking-off' AND w.doc_type IN ['registry_filing', 'registry_extract_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'striking-off' AND w.doc_type IN ['registry_extract', 'correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'board-meeting' AND w.doc_type = 'board_meeting_minutes' THEN 'primary_authority'
  WHEN e.eventType = 'board-meeting' AND w.doc_type IN ['board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'board-meeting' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'board-resolution' AND w.doc_type = 'board_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'board-resolution' AND w.doc_type IN ['board_meeting_minutes'] THEN 'fallback_authority'
  WHEN e.eventType = 'board-resolution' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'shareholder-meeting' AND w.doc_type = 'shareholder_meeting_minutes' THEN 'primary_authority'
  WHEN e.eventType = 'shareholder-meeting' AND w.doc_type IN ['shareholder_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'shareholder-meeting' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'shareholder-resolution' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'shareholder-resolution' AND w.doc_type IN ['shareholder_meeting_minutes'] THEN 'fallback_authority'
  WHEN e.eventType = 'shareholder-resolution' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'director-appointment' AND w.doc_type = 'director_appointment' THEN 'primary_authority'
  WHEN e.eventType = 'director-appointment' AND w.doc_type IN ['board_resolution', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'director-appointment' AND w.doc_type IN ['registry_extract', 'good_standing_certificate', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'director-resignation' AND w.doc_type = 'director_resignation' THEN 'primary_authority'
  WHEN e.eventType = 'director-resignation' AND w.doc_type IN ['board_resolution', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'director-resignation' AND w.doc_type IN ['registry_extract', 'good_standing_certificate', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'officer-appointment' AND w.doc_type = 'board_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'officer-appointment' AND w.doc_type IN ['director_appointment', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'officer-appointment' AND w.doc_type IN ['registry_extract', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'officer-resignation' AND w.doc_type = 'board_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'officer-resignation' AND w.doc_type IN ['director_resignation', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'officer-resignation' AND w.doc_type IN ['registry_extract', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'auditor-appointment' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'auditor-appointment' AND w.doc_type IN ['board_resolution', 'engagement_letter'] THEN 'fallback_authority'
  WHEN e.eventType = 'auditor-appointment' AND w.doc_type IN ['annual_accounts_financial_statements', 'registry_extract'] THEN 'weak_or_context'
  WHEN e.eventType = 'share-issuance' AND w.doc_type = 'share_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'share-issuance' AND w.doc_type IN ['share_register', 'shareholder_resolution', 'board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'share-issuance' AND w.doc_type IN ['annual_accounts_financial_statements', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'share-allotment' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'share-allotment' AND w.doc_type IN ['board_resolution', 'share_register', 'share_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'share-allotment' AND w.doc_type IN ['corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'share-transfer' AND w.doc_type = 'share_transfer_agreement' THEN 'primary_authority'
  WHEN e.eventType = 'share-transfer' AND w.doc_type IN ['share_register', 'share_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'share-transfer' AND w.doc_type IN ['corporate_data_sheet', 'registry_extract'] THEN 'weak_or_context'
  WHEN e.eventType = 'share-cancellation' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'share-cancellation' AND w.doc_type IN ['share_register', 'share_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'share-cancellation' AND w.doc_type IN ['annual_accounts_financial_statements', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'capital-increase' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'capital-increase' AND w.doc_type IN ['registry_filing', 'share_register', 'share_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'capital-increase' AND w.doc_type IN ['annual_accounts_financial_statements', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'capital-reduction' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'capital-reduction' AND w.doc_type IN ['registry_filing', 'share_register'] THEN 'fallback_authority'
  WHEN e.eventType = 'capital-reduction' AND w.doc_type IN ['annual_accounts_financial_statements', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'capital-contribution-cash' AND w.doc_type = 'banking_payment_or_credit_record' THEN 'primary_authority'
  WHEN e.eventType = 'capital-contribution-cash' AND w.doc_type IN ['share_contribution_agreement', 'board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'capital-contribution-cash' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'capital-contribution-in-kind' AND w.doc_type = 'share_contribution_agreement' THEN 'primary_authority'
  WHEN e.eventType = 'capital-contribution-in-kind' AND w.doc_type IN ['reorganization_deed', 'legal_declaration', 'board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'capital-contribution-in-kind' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'dividend-declaration' AND w.doc_type = 'board_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'dividend-declaration' AND w.doc_type IN ['shareholder_resolution', 'board_meeting_minutes'] THEN 'fallback_authority'
  WHEN e.eventType = 'dividend-declaration' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'dividend-payment' AND w.doc_type = 'banking_payment_or_credit_record' THEN 'primary_authority'
  WHEN e.eventType = 'dividend-payment' AND w.doc_type IN ['legal_declaration'] THEN 'fallback_authority'
  WHEN e.eventType = 'dividend-payment' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'power-of-attorney-grant' AND w.doc_type = 'power_of_attorney' THEN 'primary_authority'
  WHEN e.eventType = 'power-of-attorney-grant' AND w.doc_type IN ['board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'power-of-attorney-grant' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'power-of-attorney-revocation' AND w.doc_type = 'power_of_attorney' THEN 'primary_authority'
  WHEN e.eventType = 'power-of-attorney-revocation' AND w.doc_type IN ['board_resolution', 'legal_declaration'] THEN 'fallback_authority'
  WHEN e.eventType = 'power-of-attorney-revocation' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'proxy-grant' AND w.doc_type = 'proxy' THEN 'primary_authority'
  WHEN e.eventType = 'proxy-grant' AND w.doc_type IN ['shareholder_meeting_minutes'] THEN 'fallback_authority'
  WHEN e.eventType = 'proxy-grant' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'loan-agreement' AND w.doc_type = 'intercompany_or_other_agreement' THEN 'primary_authority'
  WHEN e.eventType = 'loan-agreement' AND w.doc_type IN ['board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'loan-agreement' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'loan-repayment' AND w.doc_type = 'banking_payment_or_credit_record' THEN 'primary_authority'
  WHEN e.eventType = 'loan-repayment' AND w.doc_type IN ['legal_declaration'] THEN 'fallback_authority'
  WHEN e.eventType = 'loan-repayment' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'loan-forgiveness' AND w.doc_type = 'legal_declaration' THEN 'primary_authority'
  WHEN e.eventType = 'loan-forgiveness' AND w.doc_type IN ['intercompany_or_other_agreement', 'board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'loan-forgiveness' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'merger' AND w.doc_type = 'reorganization_deed' THEN 'primary_authority'
  WHEN e.eventType = 'merger' AND w.doc_type IN ['reorganization_resolution', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'merger' AND w.doc_type IN ['registry_extract', 'legal_opinion'] THEN 'weak_or_context'
  WHEN e.eventType = 'demerger' AND w.doc_type = 'reorganization_deed' THEN 'primary_authority'
  WHEN e.eventType = 'demerger' AND w.doc_type IN ['reorganization_resolution', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'demerger' AND w.doc_type IN ['registry_extract', 'legal_opinion'] THEN 'weak_or_context'
  WHEN e.eventType = 'asset-transfer' AND w.doc_type = 'intercompany_or_other_agreement' THEN 'primary_authority'
  WHEN e.eventType = 'asset-transfer' AND w.doc_type IN ['reorganization_deed', 'legal_declaration'] THEN 'fallback_authority'
  WHEN e.eventType = 'asset-transfer' AND w.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN e.eventType = 'intercompany-agreement' AND w.doc_type = 'intercompany_or_other_agreement' THEN 'primary_authority'
  WHEN e.eventType = 'intercompany-agreement' AND w.doc_type IN ['board_resolution'] THEN 'fallback_authority'
  WHEN e.eventType = 'intercompany-agreement' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'tax-ruling-request' AND w.doc_type = 'tax_document' THEN 'primary_authority'
  WHEN e.eventType = 'tax-ruling-request' AND w.doc_type IN ['correspondence'] THEN 'fallback_authority'
  WHEN e.eventType = 'tax-ruling-request' AND w.doc_type IN ['legal_opinion'] THEN 'weak_or_context'
  WHEN e.eventType = 'tax-ruling-grant' AND w.doc_type = 'tax_document' THEN 'primary_authority'
  WHEN e.eventType = 'tax-ruling-grant' AND w.doc_type IN ['administrative_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'tax-ruling-grant' AND w.doc_type IN ['legal_opinion'] THEN 'weak_or_context'
  WHEN e.eventType = 'tax-residence-attestation' AND w.doc_type = 'tax_document' THEN 'primary_authority'
  WHEN e.eventType = 'tax-residence-attestation' AND w.doc_type IN ['administrative_certificate', 'legal_declaration'] THEN 'fallback_authority'
  WHEN e.eventType = 'tax-residence-attestation' AND w.doc_type IN ['legal_opinion', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'annual-report-filing' AND w.doc_type = 'regulatory_filing' THEN 'primary_authority'
  WHEN e.eventType = 'annual-report-filing' AND w.doc_type IN ['annual_accounts_financial_statements', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'annual-report-filing' AND w.doc_type IN ['corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'annual-report-approval' AND w.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'annual-report-approval' AND w.doc_type IN ['shareholder_meeting_minutes', 'annual_accounts_financial_statements'] THEN 'fallback_authority'
  WHEN e.eventType = 'annual-report-approval' AND w.doc_type IN ['corporate_data_sheet'] THEN 'weak_or_context'
  WHEN e.eventType = 'notarial-certification' AND w.doc_type = 'administrative_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'notarial-certification' AND w.doc_type IN ['legal_declaration'] THEN 'fallback_authority'
  WHEN e.eventType = 'notarial-certification' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'apostille' AND w.doc_type = 'administrative_certificate' THEN 'primary_authority'
  WHEN e.eventType = 'apostille' AND w.doc_type IN ['registry_extract_certificate'] THEN 'fallback_authority'
  WHEN e.eventType = 'apostille' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'cancellation' AND w.doc_type = 'legal_declaration' THEN 'primary_authority'
  WHEN e.eventType = 'cancellation' AND w.doc_type IN ['board_resolution', 'shareholder_resolution', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'cancellation' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'recall-of-decision' AND w.doc_type = 'board_resolution' THEN 'primary_authority'
  WHEN e.eventType = 'recall-of-decision' AND w.doc_type IN ['shareholder_resolution', 'legal_declaration', 'registry_filing'] THEN 'fallback_authority'
  WHEN e.eventType = 'recall-of-decision' AND w.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN e.eventType = 'unclassified' AND w.doc_type = 'other' THEN 'primary_authority'
  WHEN e.eventType = 'unclassified' AND w.doc_type IN ['correspondence', 'corporate_data_sheet'] THEN 'weak_or_context'
  ELSE 'non_authoritative'
END AS source_authority_status,
     CASE
  WHEN e.eventType = 'incorporation' THEN 'corporate_lifecycle'
  WHEN e.eventType = 'constitutional-adoption' THEN 'constitutional_governance'
  WHEN e.eventType = 'articles-amendment' THEN 'constitutional_governance'
  WHEN e.eventType = 'continuation-in' THEN 'corporate_lifecycle'
  WHEN e.eventType = 'continuation-out' THEN 'corporate_lifecycle'
  WHEN e.eventType = 'redomiciliation' THEN 'corporate_lifecycle'
  WHEN e.eventType = 'legal-form-conversion' THEN 'corporate_lifecycle'
  WHEN e.eventType = 'dissolution' THEN 'corporate_lifecycle'
  WHEN e.eventType = 'liquidation-start' THEN 'corporate_lifecycle'
  WHEN e.eventType = 'liquidation-end' THEN 'corporate_lifecycle'
  WHEN e.eventType = 'striking-off' THEN 'corporate_lifecycle'
  WHEN e.eventType = 'board-meeting' THEN 'constitutional_governance'
  WHEN e.eventType = 'board-resolution' THEN 'constitutional_governance'
  WHEN e.eventType = 'shareholder-meeting' THEN 'constitutional_governance'
  WHEN e.eventType = 'shareholder-resolution' THEN 'constitutional_governance'
  WHEN e.eventType = 'director-appointment' THEN 'officers_and_roles'
  WHEN e.eventType = 'director-resignation' THEN 'officers_and_roles'
  WHEN e.eventType = 'officer-appointment' THEN 'officers_and_roles'
  WHEN e.eventType = 'officer-resignation' THEN 'officers_and_roles'
  WHEN e.eventType = 'auditor-appointment' THEN 'officers_and_roles'
  WHEN e.eventType = 'share-issuance' THEN 'capital_and_shares'
  WHEN e.eventType = 'share-allotment' THEN 'capital_and_shares'
  WHEN e.eventType = 'share-transfer' THEN 'capital_and_shares'
  WHEN e.eventType = 'share-cancellation' THEN 'capital_and_shares'
  WHEN e.eventType = 'capital-increase' THEN 'capital_and_shares'
  WHEN e.eventType = 'capital-reduction' THEN 'capital_and_shares'
  WHEN e.eventType = 'capital-contribution-cash' THEN 'capital_and_shares'
  WHEN e.eventType = 'capital-contribution-in-kind' THEN 'capital_and_shares'
  WHEN e.eventType = 'dividend-declaration' THEN 'distributions'
  WHEN e.eventType = 'dividend-payment' THEN 'distributions'
  WHEN e.eventType = 'power-of-attorney-grant' THEN 'authority_and_representation'
  WHEN e.eventType = 'power-of-attorney-revocation' THEN 'authority_and_representation'
  WHEN e.eventType = 'proxy-grant' THEN 'authority_and_representation'
  WHEN e.eventType = 'loan-agreement' THEN 'finance_and_treasury'
  WHEN e.eventType = 'loan-repayment' THEN 'finance_and_treasury'
  WHEN e.eventType = 'loan-forgiveness' THEN 'finance_and_treasury'
  WHEN e.eventType = 'merger' THEN 'reorganization_and_transactions'
  WHEN e.eventType = 'demerger' THEN 'reorganization_and_transactions'
  WHEN e.eventType = 'asset-transfer' THEN 'reorganization_and_transactions'
  WHEN e.eventType = 'intercompany-agreement' THEN 'reorganization_and_transactions'
  WHEN e.eventType = 'tax-ruling-request' THEN 'tax_and_regulatory'
  WHEN e.eventType = 'tax-ruling-grant' THEN 'tax_and_regulatory'
  WHEN e.eventType = 'tax-residence-attestation' THEN 'tax_and_regulatory'
  WHEN e.eventType = 'annual-report-filing' THEN 'tax_and_regulatory'
  WHEN e.eventType = 'annual-report-approval' THEN 'tax_and_regulatory'
  WHEN e.eventType = 'notarial-certification' THEN 'formalities'
  WHEN e.eventType = 'apostille' THEN 'formalities'
  WHEN e.eventType = 'cancellation' THEN 'meta_quality'
  WHEN e.eventType = 'recall-of-decision' THEN 'meta_quality'
  WHEN e.eventType = 'unclassified' THEN 'meta_quality'
  ELSE 'unknown'
END AS event_domain,
     CASE
  WHEN e.eventType = 'incorporation' THEN 'incorporation_certificate'
  WHEN e.eventType = 'constitutional-adoption' THEN 'articles_of_association_or_bylaws'
  WHEN e.eventType = 'articles-amendment' THEN 'shareholder_resolution'
  WHEN e.eventType = 'continuation-in' THEN 'continuation_certificate'
  WHEN e.eventType = 'continuation-out' THEN 'discontinuance_certificate'
  WHEN e.eventType = 'redomiciliation' THEN 'continuation_certificate'
  WHEN e.eventType = 'legal-form-conversion' THEN 'registry_filing'
  WHEN e.eventType = 'dissolution' THEN 'dissolution_certificate'
  WHEN e.eventType = 'liquidation-start' THEN 'shareholder_resolution'
  WHEN e.eventType = 'liquidation-end' THEN 'dissolution_certificate'
  WHEN e.eventType = 'striking-off' THEN 'administrative_certificate'
  WHEN e.eventType = 'board-meeting' THEN 'board_meeting_minutes'
  WHEN e.eventType = 'board-resolution' THEN 'board_resolution'
  WHEN e.eventType = 'shareholder-meeting' THEN 'shareholder_meeting_minutes'
  WHEN e.eventType = 'shareholder-resolution' THEN 'shareholder_resolution'
  WHEN e.eventType = 'director-appointment' THEN 'director_appointment'
  WHEN e.eventType = 'director-resignation' THEN 'director_resignation'
  WHEN e.eventType = 'officer-appointment' THEN 'board_resolution'
  WHEN e.eventType = 'officer-resignation' THEN 'board_resolution'
  WHEN e.eventType = 'auditor-appointment' THEN 'shareholder_resolution'
  WHEN e.eventType = 'share-issuance' THEN 'share_certificate'
  WHEN e.eventType = 'share-allotment' THEN 'shareholder_resolution'
  WHEN e.eventType = 'share-transfer' THEN 'share_transfer_agreement'
  WHEN e.eventType = 'share-cancellation' THEN 'shareholder_resolution'
  WHEN e.eventType = 'capital-increase' THEN 'shareholder_resolution'
  WHEN e.eventType = 'capital-reduction' THEN 'shareholder_resolution'
  WHEN e.eventType = 'capital-contribution-cash' THEN 'banking_payment_or_credit_record'
  WHEN e.eventType = 'capital-contribution-in-kind' THEN 'share_contribution_agreement'
  WHEN e.eventType = 'dividend-declaration' THEN 'board_resolution'
  WHEN e.eventType = 'dividend-payment' THEN 'banking_payment_or_credit_record'
  WHEN e.eventType = 'power-of-attorney-grant' THEN 'power_of_attorney'
  WHEN e.eventType = 'power-of-attorney-revocation' THEN 'power_of_attorney'
  WHEN e.eventType = 'proxy-grant' THEN 'proxy'
  WHEN e.eventType = 'loan-agreement' THEN 'intercompany_or_other_agreement'
  WHEN e.eventType = 'loan-repayment' THEN 'banking_payment_or_credit_record'
  WHEN e.eventType = 'loan-forgiveness' THEN 'legal_declaration'
  WHEN e.eventType = 'merger' THEN 'reorganization_deed'
  WHEN e.eventType = 'demerger' THEN 'reorganization_deed'
  WHEN e.eventType = 'asset-transfer' THEN 'intercompany_or_other_agreement'
  WHEN e.eventType = 'intercompany-agreement' THEN 'intercompany_or_other_agreement'
  WHEN e.eventType = 'tax-ruling-request' THEN 'tax_document'
  WHEN e.eventType = 'tax-ruling-grant' THEN 'tax_document'
  WHEN e.eventType = 'tax-residence-attestation' THEN 'tax_document'
  WHEN e.eventType = 'annual-report-filing' THEN 'regulatory_filing'
  WHEN e.eventType = 'annual-report-approval' THEN 'shareholder_resolution'
  WHEN e.eventType = 'notarial-certification' THEN 'administrative_certificate'
  WHEN e.eventType = 'apostille' THEN 'administrative_certificate'
  WHEN e.eventType = 'cancellation' THEN 'legal_declaration'
  WHEN e.eventType = 'recall-of-decision' THEN 'board_resolution'
  WHEN e.eventType = 'unclassified' THEN 'other'
  ELSE NULL
END AS primary_document_type
WITH e, effective_date, actor, under, cp, amt, src, source_rel, w, item, subj,
     source_authority_level, source_authority_status, event_domain,
     primary_document_type,
     coalesce(source_rel.source_authority_rank, CASE
  WHEN source_authority_level = 'primary_authority' AND type(source_rel) IN ['RECORDS', 'EVIDENCES'] THEN 10
  WHEN source_authority_level = 'primary_authority' THEN 15
  WHEN source_authority_level = 'fallback_authority' AND type(source_rel) IN ['RECORDS', 'EVIDENCES'] THEN 20
  WHEN source_authority_level = 'fallback_authority' THEN 25
  WHEN source_authority_level = 'weak_or_context' AND type(source_rel) IN ['RECORDS', 'EVIDENCES'] THEN 30
  WHEN source_authority_level = 'weak_or_context' THEN 35
  WHEN source_authority_level = 'unknown_event_type' THEN 80
  WHEN source_authority_level = 'missing_document' THEN 90
  WHEN type(source_rel) IN ['RECORDS', 'EVIDENCES'] THEN 60
  ELSE 65
END) AS source_authority_rank
WHERE
  $include_cancelled
  OR src IS NULL
  OR (
    coalesce(w.lifecycle_status, 'active') = 'active'
    AND coalesce(src.lifecycle_status, 'active') = 'active'
    AND coalesce(item.lifecycle_status, 'active') = 'active'
  )
ORDER BY source_authority_rank, item.inbox_filename
WITH e, effective_date, amt, subj, actor, under, cp, source_rel, w, item,
     source_authority_level, source_authority_status, source_authority_rank,
     event_domain, primary_document_type,
     e.source_doc AS event_source_doc,
     e.source_chunk AS event_source_chunk
WITH e, effective_date, amt, subj,
     event_source_doc,
     event_source_chunk,
     [entity_id IN collect(DISTINCT actor.entityId)
        WHERE entity_id IS NOT NULL]       AS actor_ids,
     collect(DISTINCT actor.label)         AS actors,
     [entity_id IN collect(DISTINCT under.entityId)
        WHERE entity_id IS NOT NULL]       AS undergoer_ids,
     collect(DISTINCT under.label)         AS undergoers,
     collect(DISTINCT cp.label)            AS counterparties,
     [source IN collect(DISTINCT
        CASE WHEN item.inbox_filename IS NULL THEN NULL ELSE {
          file: item.inbox_filename,
          chunk_id: CASE WHEN item.inbox_filename = event_source_doc
                         THEN event_source_chunk ELSE NULL END,
          doc_type: w.doc_type,
          link_type: type(source_rel),
          authority_level: source_authority_level,
          authority_status: source_authority_status,
          authority_rank: source_authority_rank,
          is_best_event_source: coalesce(source_rel.is_best_event_source, false)
        } END) WHERE source IS NOT NULL]   AS sources,
     collect(DISTINCT w.title)             AS supporting_titles,
     collect(DISTINCT source_authority_status) AS source_authority_statuses,
     event_domain,
     primary_document_type
WITH e, effective_date, amt, subj, actors, undergoers, counterparties,
     sources, supporting_titles, actor_ids, undergoer_ids,
     event_domain, primary_document_type,
     CASE
       WHEN 'primary_authority' IN source_authority_statuses THEN 'primary_authority'
       WHEN 'fallback_authority' IN source_authority_statuses THEN 'fallback_authority'
       WHEN 'weak_or_context' IN source_authority_statuses THEN 'weak_or_context'
       WHEN 'mentioned_only' IN source_authority_statuses THEN 'mentioned_only'
       WHEN 'missing_document' IN source_authority_statuses THEN 'missing_document'
       ELSE 'non_authoritative'
     END                                     AS authority_status,
     CASE
       WHEN e.eventType = 'incorporation'
         AND effective_date IS NOT NULL
         AND size(undergoer_ids) = 1
         THEN 'incorporation|' + effective_date + '|' + head(undergoer_ids)
       ELSE e.entityId
     END                                     AS dedupe_key,
     CASE
       WHEN size(actor_ids) > 0 THEN 100 ELSE 0
     END
     + CASE
         WHEN amt.amount IS NOT NULL THEN 10 ELSE 0
       END
     + size(counterparties)                  AS row_score
ORDER BY dedupe_key, row_score DESC, e.label, e.entityId
WITH dedupe_key,
     collect({
       actors: actors,
       undergoers: undergoers,
       event: e.label,
       event_type: e.eventType,
       event_domain: event_domain,
       effective_date: effective_date,
       primary_document_type: primary_document_type,
       authority_status: authority_status,
       counterparties: counterparties,
       amount: amt.amount,
       currency: amt.currency,
       sources: sources,
       supporting_titles: supporting_titles,
       subject: subj.label,
       event_id: e.entityId
     })[0]                                   AS row
RETURN
       row.actors                            AS actors,
       row.undergoers                        AS undergoers,
       row.event                             AS event,
       row.event_type                        AS event_type,
       row.event_domain                      AS event_domain,
       row.effective_date                    AS effective_date,
       row.primary_document_type             AS primary_document_type,
       row.authority_status                  AS authority_status,
       row.counterparties                    AS counterparties,
       row.amount                            AS amount,
       row.currency                          AS currency,
       row.sources                           AS sources,
       row.supporting_titles                 AS supporting_titles,
       row.subject                           AS subject,
       row.event_id                          AS event_id
ORDER BY effective_date, event
LIMIT toInteger($limit)
""".strip()

DATA_MODEL_GUIDE = "RETURN 'guide' AS section"

DATA_MODEL_CLASSES = "RETURN 'dev_workflows' AS section"

SUBJECT_IDENTIFIERS = r"""
MATCH (subject:BusinessSubject {subjectId: $subject_id})-[:HAS_PHASE]->(phase:Entity)
WITH subject, phase
CALL {
  WITH phase
  OPTIONAL MATCH (phase)-[:IS_IDENTIFIED_BY]->(rid:Entity)-[:INSTANCE_OF]->(rid_class:Class)
  WHERE rid_class.localName IN ['RegistrationIdentifier', 'LegalEntityIdentifier', 'TaxIdentifier', 'ChamberOfCommerceIdentifier', 'RegulatoryFilingIdentifier', 'BankAccountIdentifier', 'CertificateIdentifier', 'SWIFTIdentifier', 'DocumentReferenceIdentifier', 'RulingIdentifier', 'PassportIdentifier', 'NationalIDIdentifier']
  WITH phase, rid, rid_class,
       EXISTS {
         MATCH (phase)-[:IS_IDENTIFIED_BY]->(:Entity)
               -[:INSTANCE_OF]->(:Class {localName: 'RegistrationIdentifier'})
       } AS has_registration_identifier
  WHERE rid IS NOT NULL
     OR (NOT has_registration_identifier AND phase.registration_number IS NOT NULL)
  RETURN rid.entityId AS identifier_id,
         coalesce(rid.label, phase.registration_number) AS identifier,
         coalesce(rid_class.localName, 'RegistrationIdentifier') AS kind,
         coalesce(rid.scheme, phase.registration_scheme) AS scheme,
         coalesce(rid.lifecycle_status, phase.status, 'active') AS status,
         CASE
           WHEN rid.source_doc IS NULL THEN []
           ELSE [{file: rid.source_doc, chunk_id: rid.source_chunk}]
         END AS sources
}
RETURN subject.subjectId             AS subject_id,
       subject.label                 AS subject,
       phase.entityId                AS phase_id,
       phase.label                   AS phase_label,
       phase.phase_valid_from        AS phase_valid_from,
       phase.phase_valid_to          AS phase_valid_to,
       identifier_id                 AS identifier_id,
       identifier                    AS identifier,
       kind                          AS kind,
       scheme                        AS scheme,
       phase.governing_law           AS governing_law,
       status                        AS status,
       sources                       AS sources
ORDER BY coalesce(phase.phase_valid_from, '') DESC,
         coalesce(phase.phase_valid_to, '9999-12-31') DESC,
         phase.label,
         kind,
         identifier
""".strip()

SUBJECT_BOARD_HISTORY = r"""
MATCH (subject:BusinessSubject {subjectId: $subject_id})-[:HAS_PHASE]->(phase:Entity)
MATCH (board_membership:Entity:BoardMembership)-[membership_edge:INVOLVES_CONTROLLED_THING]->(phase)
MATCH (board_membership)-[:HAS_PARTY_IN_CONTROL]->(person:Entity:Person)
WHERE membership_edge.valid_to IS NULL
  AND NOT toLower(coalesce(board_membership.role_title, '')) IN [
    'chairman',
    'chairperson',
    'chairman of meeting',
    'chairperson of meeting'
  ]
WITH subject, phase, board_membership, person,
     [file IN [
        board_membership.appointment_source_doc,
        board_membership.valid_from_source_doc,
        board_membership.source_doc
      ] WHERE file IS NOT NULL] AS membership_source_files
CALL (membership_source_files) {
  OPTIONAL MATCH (membership_work:Work)-[:HAS_REALIZATION]->(:Expression)
                -[:HAS_EMBODIMENT]->(:Manifestation)-[:HAS_EXEMPLAR]->(membership_item:Item)
  WHERE membership_item.inbox_filename IN membership_source_files
  WITH membership_work, membership_item,
       CASE
         WHEN membership_work.doc_type IN [
           'shareholder_resolution',
           'board_resolution',
           'director_appointment',
           'director_resignation',
           'director_resolution',
           'director_officer_appointment_or_resignation',
           'incorporation_certificate',
           'continuation_certificate',
           'articles_of_association_or_bylaws',
           'registry_filing',
           'registry_extract_or_filing'
         ] THEN 'primary_authority'
         WHEN membership_work.doc_type IN [
           'registry_extract',
           'registry_extract_certificate'
         ] THEN 'fallback_authority'
         ELSE 'weak_or_context'
       END AS membership_authority_status
  RETURN [source IN collect(DISTINCT {
            file: membership_item.inbox_filename,
            chunk_id: NULL,
            doc_type: membership_work.doc_type,
            authority_status: membership_authority_status
          }) WHERE source.file IS NOT NULL] AS membership_sources,
         [doc_type IN collect(DISTINCT membership_work.doc_type)
            WHERE doc_type IS NOT NULL] AS membership_doc_types,
         [title IN collect(DISTINCT membership_work.title)
            WHERE title IS NOT NULL] AS membership_titles,
         [status IN collect(DISTINCT membership_authority_status)
            WHERE status IS NOT NULL] AS membership_authority_statuses
}
WITH subject, phase, board_membership, person, membership_source_files,
     membership_sources, membership_doc_types, membership_titles,
     membership_authority_statuses
WHERE ANY(doc_type IN membership_doc_types WHERE doc_type IN [
  'director_appointment',
  'director_resignation',
  'director_resolution',
  'director_officer_appointment_or_resignation',
  'registry_extract',
  'registry_filing',
  'registry_extract_or_filing',
  'shareholder_resolution',
  'board_resolution',
  'incorporation_certificate',
  'continuation_certificate',
  'registry_extract_certificate',
  'articles_of_association_or_bylaws'
])
CALL (phase, person, membership_source_files) {
  OPTIONAL MATCH (event:Entity:Event)-[event_phase_rel]-(phase)
  WHERE event.eventType IN [
    'director-appointment',
    'director-resignation',
    'officer-appointment',
    'officer-resignation',
    'shareholder-resolution',
    'board-resolution'
  ]
    AND type(event_phase_rel) IN [
      'HAS_ACTOR',
      'HAS_UNDERGOER',
      'HAS_COUNTERPARTY',
      'INVOLVES_CONTROLLED_THING',
      'RELATED_ENDEAVOUR'
    ]
  CALL (event) {
    OPTIONAL MATCH (event_expr:Expression)-[event_source_rel:RECORDS|MENTIONS|EVIDENCES]->(event)
    OPTIONAL MATCH (event_expr)<-[:HAS_REALIZATION]-(event_work:Work)
    OPTIONAL MATCH (event_expr)-[:HAS_EMBODIMENT]->(:Manifestation)-[:HAS_EXEMPLAR]->(event_item:Item)
    WITH event_source_rel, event_work, event_item,
         CASE
  WHEN event_work.doc_type IS NULL THEN 'missing_document'
  WHEN event.eventType IS NULL THEN 'unknown_event_type'
  WHEN NOT type(event_source_rel) IN ['RECORDS', 'EVIDENCES'] THEN 'mentioned_only'
  WHEN event.eventType = 'incorporation' AND event_work.doc_type = 'incorporation_certificate' THEN 'primary_authority'
  WHEN event.eventType = 'incorporation' AND event_work.doc_type IN ['articles_of_association_or_bylaws'] THEN 'fallback_authority'
  WHEN event.eventType = 'incorporation' AND event_work.doc_type IN ['good_standing_certificate', 'registry_extract', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN event.eventType = 'constitutional-adoption' AND event_work.doc_type = 'articles_of_association_or_bylaws' THEN 'primary_authority'
  WHEN event.eventType = 'constitutional-adoption' AND event_work.doc_type IN ['incorporation_certificate'] THEN 'fallback_authority'
  WHEN event.eventType = 'constitutional-adoption' AND event_work.doc_type IN ['registry_extract', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN event.eventType = 'articles-amendment' AND event_work.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN event.eventType = 'articles-amendment' AND event_work.doc_type IN ['articles_of_association_or_bylaws', 'registry_filing'] THEN 'fallback_authority'
  WHEN event.eventType = 'articles-amendment' AND event_work.doc_type IN ['registry_extract', 'legal_opinion'] THEN 'weak_or_context'
  WHEN event.eventType = 'continuation-in' AND event_work.doc_type = 'continuation_certificate' THEN 'primary_authority'
  WHEN event.eventType = 'continuation-in' AND event_work.doc_type IN ['registry_filing', 'redomiciliation_application'] THEN 'fallback_authority'
  WHEN event.eventType = 'continuation-in' AND event_work.doc_type IN ['registry_extract', 'good_standing_certificate'] THEN 'weak_or_context'
  WHEN event.eventType = 'continuation-out' AND event_work.doc_type = 'discontinuance_certificate' THEN 'primary_authority'
  WHEN event.eventType = 'continuation-out' AND event_work.doc_type IN ['registry_filing', 'redomiciliation_application'] THEN 'fallback_authority'
  WHEN event.eventType = 'continuation-out' AND event_work.doc_type IN ['registry_extract', 'good_standing_certificate'] THEN 'weak_or_context'
  WHEN event.eventType = 'redomiciliation' AND event_work.doc_type = 'continuation_certificate' THEN 'primary_authority'
  WHEN event.eventType = 'redomiciliation' AND event_work.doc_type IN ['discontinuance_certificate', 'redomiciliation_application', 'reorganization_resolution'] THEN 'fallback_authority'
  WHEN event.eventType = 'redomiciliation' AND event_work.doc_type IN ['registry_extract', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN event.eventType = 'legal-form-conversion' AND event_work.doc_type = 'registry_filing' THEN 'primary_authority'
  WHEN event.eventType = 'legal-form-conversion' AND event_work.doc_type IN ['reorganization_deed', 'shareholder_resolution'] THEN 'fallback_authority'
  WHEN event.eventType = 'legal-form-conversion' AND event_work.doc_type IN ['registry_extract', 'legal_opinion'] THEN 'weak_or_context'
  WHEN event.eventType = 'dissolution' AND event_work.doc_type = 'dissolution_certificate' THEN 'primary_authority'
  WHEN event.eventType = 'dissolution' AND event_work.doc_type IN ['registry_filing'] THEN 'fallback_authority'
  WHEN event.eventType = 'dissolution' AND event_work.doc_type IN ['good_standing_certificate', 'registry_extract'] THEN 'weak_or_context'
  WHEN event.eventType = 'liquidation-start' AND event_work.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN event.eventType = 'liquidation-start' AND event_work.doc_type IN ['registry_filing', 'reorganization_resolution'] THEN 'fallback_authority'
  WHEN event.eventType = 'liquidation-start' AND event_work.doc_type IN ['registry_extract', 'correspondence'] THEN 'weak_or_context'
  WHEN event.eventType = 'liquidation-end' AND event_work.doc_type = 'dissolution_certificate' THEN 'primary_authority'
  WHEN event.eventType = 'liquidation-end' AND event_work.doc_type IN ['registry_filing', 'administrative_certificate'] THEN 'fallback_authority'
  WHEN event.eventType = 'liquidation-end' AND event_work.doc_type IN ['registry_extract', 'correspondence'] THEN 'weak_or_context'
  WHEN event.eventType = 'striking-off' AND event_work.doc_type = 'administrative_certificate' THEN 'primary_authority'
  WHEN event.eventType = 'striking-off' AND event_work.doc_type IN ['registry_filing', 'registry_extract_certificate'] THEN 'fallback_authority'
  WHEN event.eventType = 'striking-off' AND event_work.doc_type IN ['registry_extract', 'correspondence'] THEN 'weak_or_context'
  WHEN event.eventType = 'board-meeting' AND event_work.doc_type = 'board_meeting_minutes' THEN 'primary_authority'
  WHEN event.eventType = 'board-meeting' AND event_work.doc_type IN ['board_resolution'] THEN 'fallback_authority'
  WHEN event.eventType = 'board-meeting' AND event_work.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN event.eventType = 'board-resolution' AND event_work.doc_type = 'board_resolution' THEN 'primary_authority'
  WHEN event.eventType = 'board-resolution' AND event_work.doc_type IN ['board_meeting_minutes'] THEN 'fallback_authority'
  WHEN event.eventType = 'board-resolution' AND event_work.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN event.eventType = 'shareholder-meeting' AND event_work.doc_type = 'shareholder_meeting_minutes' THEN 'primary_authority'
  WHEN event.eventType = 'shareholder-meeting' AND event_work.doc_type IN ['shareholder_resolution'] THEN 'fallback_authority'
  WHEN event.eventType = 'shareholder-meeting' AND event_work.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN event.eventType = 'shareholder-resolution' AND event_work.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN event.eventType = 'shareholder-resolution' AND event_work.doc_type IN ['shareholder_meeting_minutes'] THEN 'fallback_authority'
  WHEN event.eventType = 'shareholder-resolution' AND event_work.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN event.eventType = 'director-appointment' AND event_work.doc_type = 'director_appointment' THEN 'primary_authority'
  WHEN event.eventType = 'director-appointment' AND event_work.doc_type IN ['board_resolution', 'registry_filing'] THEN 'fallback_authority'
  WHEN event.eventType = 'director-appointment' AND event_work.doc_type IN ['registry_extract', 'good_standing_certificate', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN event.eventType = 'director-resignation' AND event_work.doc_type = 'director_resignation' THEN 'primary_authority'
  WHEN event.eventType = 'director-resignation' AND event_work.doc_type IN ['board_resolution', 'registry_filing'] THEN 'fallback_authority'
  WHEN event.eventType = 'director-resignation' AND event_work.doc_type IN ['registry_extract', 'good_standing_certificate', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN event.eventType = 'officer-appointment' AND event_work.doc_type = 'board_resolution' THEN 'primary_authority'
  WHEN event.eventType = 'officer-appointment' AND event_work.doc_type IN ['director_appointment', 'registry_filing'] THEN 'fallback_authority'
  WHEN event.eventType = 'officer-appointment' AND event_work.doc_type IN ['registry_extract', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN event.eventType = 'officer-resignation' AND event_work.doc_type = 'board_resolution' THEN 'primary_authority'
  WHEN event.eventType = 'officer-resignation' AND event_work.doc_type IN ['director_resignation', 'registry_filing'] THEN 'fallback_authority'
  WHEN event.eventType = 'officer-resignation' AND event_work.doc_type IN ['registry_extract', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN event.eventType = 'auditor-appointment' AND event_work.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN event.eventType = 'auditor-appointment' AND event_work.doc_type IN ['board_resolution', 'engagement_letter'] THEN 'fallback_authority'
  WHEN event.eventType = 'auditor-appointment' AND event_work.doc_type IN ['annual_accounts_financial_statements', 'registry_extract'] THEN 'weak_or_context'
  WHEN event.eventType = 'share-issuance' AND event_work.doc_type = 'share_certificate' THEN 'primary_authority'
  WHEN event.eventType = 'share-issuance' AND event_work.doc_type IN ['share_register', 'shareholder_resolution', 'board_resolution'] THEN 'fallback_authority'
  WHEN event.eventType = 'share-issuance' AND event_work.doc_type IN ['annual_accounts_financial_statements', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN event.eventType = 'share-allotment' AND event_work.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN event.eventType = 'share-allotment' AND event_work.doc_type IN ['board_resolution', 'share_register', 'share_certificate'] THEN 'fallback_authority'
  WHEN event.eventType = 'share-allotment' AND event_work.doc_type IN ['corporate_data_sheet'] THEN 'weak_or_context'
  WHEN event.eventType = 'share-transfer' AND event_work.doc_type = 'share_transfer_agreement' THEN 'primary_authority'
  WHEN event.eventType = 'share-transfer' AND event_work.doc_type IN ['share_register', 'share_certificate'] THEN 'fallback_authority'
  WHEN event.eventType = 'share-transfer' AND event_work.doc_type IN ['corporate_data_sheet', 'registry_extract'] THEN 'weak_or_context'
  WHEN event.eventType = 'share-cancellation' AND event_work.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN event.eventType = 'share-cancellation' AND event_work.doc_type IN ['share_register', 'share_certificate'] THEN 'fallback_authority'
  WHEN event.eventType = 'share-cancellation' AND event_work.doc_type IN ['annual_accounts_financial_statements', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN event.eventType = 'capital-increase' AND event_work.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN event.eventType = 'capital-increase' AND event_work.doc_type IN ['registry_filing', 'share_register', 'share_certificate'] THEN 'fallback_authority'
  WHEN event.eventType = 'capital-increase' AND event_work.doc_type IN ['annual_accounts_financial_statements', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN event.eventType = 'capital-reduction' AND event_work.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN event.eventType = 'capital-reduction' AND event_work.doc_type IN ['registry_filing', 'share_register'] THEN 'fallback_authority'
  WHEN event.eventType = 'capital-reduction' AND event_work.doc_type IN ['annual_accounts_financial_statements', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN event.eventType = 'capital-contribution-cash' AND event_work.doc_type = 'banking_payment_or_credit_record' THEN 'primary_authority'
  WHEN event.eventType = 'capital-contribution-cash' AND event_work.doc_type IN ['share_contribution_agreement', 'board_resolution'] THEN 'fallback_authority'
  WHEN event.eventType = 'capital-contribution-cash' AND event_work.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN event.eventType = 'capital-contribution-in-kind' AND event_work.doc_type = 'share_contribution_agreement' THEN 'primary_authority'
  WHEN event.eventType = 'capital-contribution-in-kind' AND event_work.doc_type IN ['reorganization_deed', 'legal_declaration', 'board_resolution'] THEN 'fallback_authority'
  WHEN event.eventType = 'capital-contribution-in-kind' AND event_work.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN event.eventType = 'dividend-declaration' AND event_work.doc_type = 'board_resolution' THEN 'primary_authority'
  WHEN event.eventType = 'dividend-declaration' AND event_work.doc_type IN ['shareholder_resolution', 'board_meeting_minutes'] THEN 'fallback_authority'
  WHEN event.eventType = 'dividend-declaration' AND event_work.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN event.eventType = 'dividend-payment' AND event_work.doc_type = 'banking_payment_or_credit_record' THEN 'primary_authority'
  WHEN event.eventType = 'dividend-payment' AND event_work.doc_type IN ['legal_declaration'] THEN 'fallback_authority'
  WHEN event.eventType = 'dividend-payment' AND event_work.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN event.eventType = 'power-of-attorney-grant' AND event_work.doc_type = 'power_of_attorney' THEN 'primary_authority'
  WHEN event.eventType = 'power-of-attorney-grant' AND event_work.doc_type IN ['board_resolution'] THEN 'fallback_authority'
  WHEN event.eventType = 'power-of-attorney-grant' AND event_work.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN event.eventType = 'power-of-attorney-revocation' AND event_work.doc_type = 'power_of_attorney' THEN 'primary_authority'
  WHEN event.eventType = 'power-of-attorney-revocation' AND event_work.doc_type IN ['board_resolution', 'legal_declaration'] THEN 'fallback_authority'
  WHEN event.eventType = 'power-of-attorney-revocation' AND event_work.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN event.eventType = 'proxy-grant' AND event_work.doc_type = 'proxy' THEN 'primary_authority'
  WHEN event.eventType = 'proxy-grant' AND event_work.doc_type IN ['shareholder_meeting_minutes'] THEN 'fallback_authority'
  WHEN event.eventType = 'proxy-grant' AND event_work.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN event.eventType = 'loan-agreement' AND event_work.doc_type = 'intercompany_or_other_agreement' THEN 'primary_authority'
  WHEN event.eventType = 'loan-agreement' AND event_work.doc_type IN ['board_resolution'] THEN 'fallback_authority'
  WHEN event.eventType = 'loan-agreement' AND event_work.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN event.eventType = 'loan-repayment' AND event_work.doc_type = 'banking_payment_or_credit_record' THEN 'primary_authority'
  WHEN event.eventType = 'loan-repayment' AND event_work.doc_type IN ['legal_declaration'] THEN 'fallback_authority'
  WHEN event.eventType = 'loan-repayment' AND event_work.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN event.eventType = 'loan-forgiveness' AND event_work.doc_type = 'legal_declaration' THEN 'primary_authority'
  WHEN event.eventType = 'loan-forgiveness' AND event_work.doc_type IN ['intercompany_or_other_agreement', 'board_resolution'] THEN 'fallback_authority'
  WHEN event.eventType = 'loan-forgiveness' AND event_work.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN event.eventType = 'merger' AND event_work.doc_type = 'reorganization_deed' THEN 'primary_authority'
  WHEN event.eventType = 'merger' AND event_work.doc_type IN ['reorganization_resolution', 'registry_filing'] THEN 'fallback_authority'
  WHEN event.eventType = 'merger' AND event_work.doc_type IN ['registry_extract', 'legal_opinion'] THEN 'weak_or_context'
  WHEN event.eventType = 'demerger' AND event_work.doc_type = 'reorganization_deed' THEN 'primary_authority'
  WHEN event.eventType = 'demerger' AND event_work.doc_type IN ['reorganization_resolution', 'registry_filing'] THEN 'fallback_authority'
  WHEN event.eventType = 'demerger' AND event_work.doc_type IN ['registry_extract', 'legal_opinion'] THEN 'weak_or_context'
  WHEN event.eventType = 'asset-transfer' AND event_work.doc_type = 'intercompany_or_other_agreement' THEN 'primary_authority'
  WHEN event.eventType = 'asset-transfer' AND event_work.doc_type IN ['reorganization_deed', 'legal_declaration'] THEN 'fallback_authority'
  WHEN event.eventType = 'asset-transfer' AND event_work.doc_type IN ['annual_accounts_financial_statements'] THEN 'weak_or_context'
  WHEN event.eventType = 'intercompany-agreement' AND event_work.doc_type = 'intercompany_or_other_agreement' THEN 'primary_authority'
  WHEN event.eventType = 'intercompany-agreement' AND event_work.doc_type IN ['board_resolution'] THEN 'fallback_authority'
  WHEN event.eventType = 'intercompany-agreement' AND event_work.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN event.eventType = 'tax-ruling-request' AND event_work.doc_type = 'tax_document' THEN 'primary_authority'
  WHEN event.eventType = 'tax-ruling-request' AND event_work.doc_type IN ['correspondence'] THEN 'fallback_authority'
  WHEN event.eventType = 'tax-ruling-request' AND event_work.doc_type IN ['legal_opinion'] THEN 'weak_or_context'
  WHEN event.eventType = 'tax-ruling-grant' AND event_work.doc_type = 'tax_document' THEN 'primary_authority'
  WHEN event.eventType = 'tax-ruling-grant' AND event_work.doc_type IN ['administrative_certificate'] THEN 'fallback_authority'
  WHEN event.eventType = 'tax-ruling-grant' AND event_work.doc_type IN ['legal_opinion'] THEN 'weak_or_context'
  WHEN event.eventType = 'tax-residence-attestation' AND event_work.doc_type = 'tax_document' THEN 'primary_authority'
  WHEN event.eventType = 'tax-residence-attestation' AND event_work.doc_type IN ['administrative_certificate', 'legal_declaration'] THEN 'fallback_authority'
  WHEN event.eventType = 'tax-residence-attestation' AND event_work.doc_type IN ['legal_opinion', 'corporate_data_sheet'] THEN 'weak_or_context'
  WHEN event.eventType = 'annual-report-filing' AND event_work.doc_type = 'regulatory_filing' THEN 'primary_authority'
  WHEN event.eventType = 'annual-report-filing' AND event_work.doc_type IN ['annual_accounts_financial_statements', 'registry_filing'] THEN 'fallback_authority'
  WHEN event.eventType = 'annual-report-filing' AND event_work.doc_type IN ['corporate_data_sheet'] THEN 'weak_or_context'
  WHEN event.eventType = 'annual-report-approval' AND event_work.doc_type = 'shareholder_resolution' THEN 'primary_authority'
  WHEN event.eventType = 'annual-report-approval' AND event_work.doc_type IN ['shareholder_meeting_minutes', 'annual_accounts_financial_statements'] THEN 'fallback_authority'
  WHEN event.eventType = 'annual-report-approval' AND event_work.doc_type IN ['corporate_data_sheet'] THEN 'weak_or_context'
  WHEN event.eventType = 'notarial-certification' AND event_work.doc_type = 'administrative_certificate' THEN 'primary_authority'
  WHEN event.eventType = 'notarial-certification' AND event_work.doc_type IN ['legal_declaration'] THEN 'fallback_authority'
  WHEN event.eventType = 'notarial-certification' AND event_work.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN event.eventType = 'apostille' AND event_work.doc_type = 'administrative_certificate' THEN 'primary_authority'
  WHEN event.eventType = 'apostille' AND event_work.doc_type IN ['registry_extract_certificate'] THEN 'fallback_authority'
  WHEN event.eventType = 'apostille' AND event_work.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN event.eventType = 'cancellation' AND event_work.doc_type = 'legal_declaration' THEN 'primary_authority'
  WHEN event.eventType = 'cancellation' AND event_work.doc_type IN ['board_resolution', 'shareholder_resolution', 'registry_filing'] THEN 'fallback_authority'
  WHEN event.eventType = 'cancellation' AND event_work.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN event.eventType = 'recall-of-decision' AND event_work.doc_type = 'board_resolution' THEN 'primary_authority'
  WHEN event.eventType = 'recall-of-decision' AND event_work.doc_type IN ['shareholder_resolution', 'legal_declaration', 'registry_filing'] THEN 'fallback_authority'
  WHEN event.eventType = 'recall-of-decision' AND event_work.doc_type IN ['correspondence'] THEN 'weak_or_context'
  WHEN event.eventType = 'unclassified' AND event_work.doc_type = 'other' THEN 'primary_authority'
  WHEN event.eventType = 'unclassified' AND event_work.doc_type IN ['correspondence', 'corporate_data_sheet'] THEN 'weak_or_context'
  ELSE 'non_authoritative'
END AS source_authority_status
    WHERE event_item.inbox_filename IS NOT NULL
    RETURN [file IN collect(DISTINCT event_item.inbox_filename)
              WHERE file IS NOT NULL] AS event_files,
           [status IN collect(DISTINCT source_authority_status)
              WHERE status IS NOT NULL] AS event_statuses
  }
  WITH event, event_files, event_statuses
  WHERE event IS NOT NULL
    AND (
      EXISTS { MATCH (event)-[:HAS_ACTOR|HAS_UNDERGOER|HAS_COUNTERPARTY]->(person) }
      OR ANY(file IN event_files WHERE file IN membership_source_files)
    )
  RETURN [label IN collect(DISTINCT event.label)
            WHERE label IS NOT NULL] AS event_labels,
         [event_type IN collect(DISTINCT event.eventType)
            WHERE event_type IS NOT NULL] AS event_types,
         reduce(acc = [], statuses IN collect(event_statuses) |
           acc + [status IN statuses WHERE NOT status IN acc]
         ) AS event_authority_statuses
}
WITH subject, phase, board_membership, person, membership_sources,
     membership_doc_types, membership_titles, event_labels, event_types,
     membership_authority_statuses + event_authority_statuses AS evidence_statuses
WITH subject, phase, board_membership, person, membership_sources,
     membership_doc_types, membership_titles, event_labels, event_types,
     CASE
       WHEN 'primary_authority' IN evidence_statuses THEN 'primary_authority'
       WHEN 'fallback_authority' IN evidence_statuses THEN 'fallback_authority'
       WHEN 'weak_or_context' IN evidence_statuses THEN 'weak_or_context'
       WHEN 'mentioned_only' IN evidence_statuses THEN 'mentioned_only'
       ELSE 'non_authoritative'
     END AS evidence_status
RETURN subject.label                              AS subject,
       phase.entityId                             AS phase_id,
       phase.label                                AS legal_entity,
       person.label                               AS person,
       person.entityId                            AS person_id,
       board_membership.entityId                  AS board_membership_id,
       board_membership.role_title                AS role,
       board_membership.valid_from                AS valid_from,
       board_membership.valid_to                  AS valid_to,
       coalesce(board_membership.lifecycle_status, 'active') AS status,
       event_labels                               AS events,
       event_types                                AS event_types,
       evidence_status                            AS evidence_status,
       membership_sources                         AS sources,
       membership_doc_types                       AS evidence_doc_types,
       membership_titles                          AS evidence_titles
ORDER BY CASE status WHEN 'active' THEN 0 ELSE 1 END,
         coalesce(valid_from, '') DESC,
         legal_entity,
         person
""".strip()

PERSON_ROLES = r"""
MATCH (p:Entity:Person {entityId: $person_id})
CALL {
  WITH p
  MATCH (p)<-[:HAS_PARTY_IN_CONTROL]-(bm:Entity:BoardMembership)
  OPTIONAL MATCH (bm)-[:INVOLVES_CONTROLLED_THING]->(org)
  OPTIONAL MATCH (bm)-[:HAS_PARTY_ROLE]->(role:Entity:PartyRole)
  WITH p, bm,
       [org_label IN collect(DISTINCT org.label) WHERE org_label IS NOT NULL] AS organizations,
       [role_label IN collect(DISTINCT role.label) WHERE role_label IS NOT NULL] AS role_labels,
       [f IN [bm.appointment_source_doc, bm.valid_from_source_doc, bm.source_doc]
        WHERE f IS NOT NULL] AS all_source_files
  WITH p, bm, organizations, role_labels,
       [i IN range(0, size(all_source_files)-1)
        WHERE NOT all_source_files[i] IN all_source_files[0..i] |
        {file: all_source_files[i],
         chunk_id: CASE WHEN all_source_files[i] = bm.source_doc THEN bm.source_chunk ELSE NULL END}
       ] AS sources
  RETURN p.label              AS person,
         p.entityId           AS person_id,
         bm.entityId          AS fact_id,
         'board_role'         AS tenure_kind,
         coalesce(
           bm.role_title,
           reduce(acc = '', role_label IN role_labels |
                  CASE WHEN acc = '' THEN role_label ELSE acc + ' / ' + role_label END)
         ) AS role,
         CASE
           WHEN size(organizations) = 0 THEN NULL
           ELSE reduce(acc = '', org_label IN organizations |
                       CASE WHEN acc = '' THEN org_label ELSE acc + ' / ' + org_label END)
         END                  AS organization,
         bm.valid_from        AS valid_from,
         bm.valid_to          AS valid_to,
         coalesce(bm.lifecycle_status, 'active') AS lifecycle_status,
         sources
  UNION ALL
  WITH p
  MATCH (p)<-[:HAS_PARTY_IN_CONTROL]-(employment:Entity:Employment)
  OPTIONAL MATCH (employment)-[:INVOLVES_CONTROLLED_THING]->(org)
  OPTIONAL MATCH (employment)-[:HAS_PARTY_ROLE]->(role:Entity:PartyRole)
  WITH p, employment,
       [org_label IN collect(DISTINCT org.label) WHERE org_label IS NOT NULL] AS organizations,
       [role_label IN collect(DISTINCT role.label) WHERE role_label IS NOT NULL] AS role_labels,
       [f IN [employment.appointment_source_doc, employment.valid_from_source_doc, employment.source_doc]
        WHERE f IS NOT NULL] AS all_source_files
  WITH p, employment, organizations, role_labels,
       [i IN range(0, size(all_source_files)-1)
        WHERE NOT all_source_files[i] IN all_source_files[0..i] |
        {file: all_source_files[i],
         chunk_id: CASE WHEN all_source_files[i] = employment.source_doc THEN employment.source_chunk ELSE NULL END}
       ] AS sources
  RETURN p.label              AS person,
         p.entityId           AS person_id,
         employment.entityId  AS fact_id,
         'employment_affiliation' AS tenure_kind,
         coalesce(
           employment.role_title,
           employment.role_code,
           reduce(acc = '', role_label IN role_labels |
                  CASE WHEN acc = '' THEN role_label ELSE acc + ' / ' + role_label END),
           employment.label
         ) AS role,
         CASE
           WHEN size(organizations) = 0 THEN NULL
           ELSE reduce(acc = '', org_label IN organizations |
                       CASE WHEN acc = '' THEN org_label ELSE acc + ' / ' + org_label END)
         END                  AS organization,
         employment.valid_from AS valid_from,
         employment.valid_to   AS valid_to,
         coalesce(employment.lifecycle_status, 'active') AS lifecycle_status,
         sources
}
RETURN person, person_id, fact_id, tenure_kind, role, organization,
       valid_from, valid_to, lifecycle_status, sources
ORDER BY coalesce(valid_from, '') DESC
""".strip()

PERSON_AUTHORITY = r"""
MATCH (p:Entity:Person {entityId: $person_id})
CALL {
  WITH p
  MATCH (poa:Entity:PowerOfAttorney)-[poa_rel:IS_CONFERRED_ON]->(p)
  WHERE $include_cancelled OR coalesce(poa.lifecycle_status, 'active') = 'active'
  OPTIONAL MATCH (poa)-[:HAS_AUTHORIZING_PARTY]->(principal:Entity)
  OPTIONAL MATCH (poa)-[:CONCERNS_ORGANIZATION]->(concerned:Entity)
  WITH p, poa, poa_rel, principal, concerned,
       coalesce(poa_rel.source_doc, poa.source_doc) AS evidence_doc
  OPTIONAL MATCH (source_work:Work)-[:HAS_REALIZATION]->(source_expr:Expression)
    -[:HAS_EMBODIMENT]->(:Manifestation)-[:HAS_EXEMPLAR]->(:Item {inbox_filename: evidence_doc})
  OPTIONAL MATCH (source_expr)-[:HAS_EFFECTIVE_DATE]->(source_date:Date)
  OPTIONAL MATCH (source_event:Entity:Event {source_doc: evidence_doc})
  WITH p, poa, poa_rel, evidence_doc,
       [label IN collect(DISTINCT principal.label) WHERE label IS NOT NULL] AS principals,
       [label IN collect(DISTINCT concerned.label) WHERE label IS NOT NULL] AS concerned_organizations,
       head([doc_type IN collect(DISTINCT source_work.doc_type) WHERE doc_type IS NOT NULL]) AS source_doc_type,
       max(CASE
             WHEN toString(source_date.iso_date) =~ '[0-9]{4}-[0-9]{2}-[0-9]{2}'
                  AND toString(source_date.iso_date) >= '1990-01-01' THEN toString(source_date.iso_date)
             WHEN toString(source_date.iso_date) = 'November 2000' THEN '2000-11-01'
             ELSE NULL
           END) AS source_expression_date,
       min(coalesce(source_event.effective_date, source_event.effectiveDate, source_event.valid_from)) AS source_event_date
  WITH p, poa, poa_rel, evidence_doc, principals, concerned_organizations, source_doc_type,
       coalesce(poa.valid_from, source_event_date, source_expression_date) AS valid_from,
       poa.valid_to AS valid_to,
       CASE
         WHEN poa_rel.evidence_chunks IS NOT NULL AND size(poa_rel.evidence_chunks) > 0 THEN poa_rel.evidence_chunks
         WHEN poa_rel.source_chunk IS NOT NULL THEN [poa_rel.source_chunk]
         WHEN poa.source_chunk IS NOT NULL THEN [poa.source_chunk]
         ELSE []
       END AS evidence_chunks
  OPTIONAL MATCH (evidence_chunk:Chunk)
  WHERE evidence_chunk.chunk_id IN evidence_chunks
  OPTIONAL MATCH (evidence_chunk)<-[:HAS_PART]-(evidence_expr:Expression)
    -[:HAS_EMBODIMENT]->(:Manifestation)-[:HAS_EXEMPLAR]->(evidence_item:Item)
  WITH p, poa, evidence_doc, principals, concerned_organizations, source_doc_type,
       valid_from, valid_to, evidence_chunks,
       [source IN collect(DISTINCT
          CASE WHEN evidence_item.inbox_filename IS NULL THEN NULL
               ELSE {file: evidence_item.inbox_filename, chunk_id: evidence_chunk.chunk_id}
          END)
        WHERE source IS NOT NULL] AS evidence_sources
  RETURN p.label AS person,
         p.entityId AS person_id,
         poa.entityId AS fact_id,
         'authority' AS branch,
         'power_of_attorney' AS fact_type,
         CASE
           WHEN size(concerned_organizations) = 0 THEN poa.label
           ELSE poa.label + ' / ' + reduce(acc = '', value IN concerned_organizations |
                       CASE WHEN acc = '' THEN value ELSE acc + ' / ' + value END)
         END AS relates_to,
         valid_from AS valid_from,
         valid_to AS valid_to,
         CASE
           WHEN coalesce(poa.lifecycle_status, 'active') <> 'active' THEN poa.lifecycle_status
           WHEN valid_to IS NOT NULL AND toString(valid_to) < toString(date()) THEN 'closed'
           ELSE 'active'
         END AS lifecycle_status,
         source_doc_type AS doc_type,
         CASE
           WHEN size(evidence_sources) > 0 THEN evidence_sources
           WHEN evidence_doc IS NOT NULL AND NOT toString(evidence_doc) STARTS WITH '['
             THEN [{file: toString(evidence_doc), chunk_id: null}]
           ELSE []
         END AS sources
  UNION ALL
  WITH p
  MATCH (p)-[authority_rel:HAS_SIGNING_AUTHORITY_FOR]->(target:Entity)
  WITH p, target, authority_rel,
       coalesce(authority_rel.source_doc, target.source_doc) AS evidence_doc
  OPTIONAL MATCH (source_work:Work)-[:HAS_REALIZATION]->(source_expr:Expression)
    -[:HAS_EMBODIMENT]->(:Manifestation)-[:HAS_EXEMPLAR]->(:Item {inbox_filename: evidence_doc})
  OPTIONAL MATCH (source_expr)-[:HAS_EFFECTIVE_DATE]->(source_date:Date)
  OPTIONAL MATCH (source_expr)-[:HAS_PART]->(source_chunk:Chunk)
  OPTIONAL MATCH (source_event:Entity:Event {source_doc: evidence_doc})
  WITH p, target, authority_rel, evidence_doc,
       head([doc_type IN collect(DISTINCT source_work.doc_type) WHERE doc_type IS NOT NULL]) AS source_doc_type,
       max(CASE
             WHEN toString(source_date.iso_date) =~ '[0-9]{4}-[0-9]{2}-[0-9]{2}'
                  AND toString(source_date.iso_date) >= '1990-01-01' THEN toString(source_date.iso_date)
             WHEN toString(source_date.iso_date) = 'November 2000' THEN '2000-11-01'
             ELSE NULL
           END) AS source_expression_date,
       [text IN collect(DISTINCT source_chunk.text) WHERE text IS NOT NULL] AS source_chunk_texts,
       min(coalesce(source_event.effective_date, source_event.effectiveDate, source_event.valid_from)) AS source_event_date
  WITH p, target, authority_rel, evidence_doc, source_doc_type,
       source_event_date, source_expression_date,
       CASE
         WHEN ANY(text IN source_chunk_texts WHERE toLower(text) CONTAINS '20. januar 2005') THEN '2005-01-20'
         WHEN ANY(text IN source_chunk_texts WHERE toLower(text) CONTAINS 'january 6, 2005'
                                             OR toLower(text) CONTAINS '01/06/2005') THEN '2005-01-06'
         WHEN ANY(text IN source_chunk_texts WHERE toLower(text) CONTAINS 'jan. 2003') THEN '2003-01-01'
         WHEN ANY(text IN source_chunk_texts WHERE toLower(text) CONTAINS 'november 2000') THEN '2000-11-01'
         ELSE NULL
       END AS source_chunk_date
  WITH p, target, authority_rel, evidence_doc, source_doc_type,
       coalesce(
         CASE
           WHEN toString(target.valid_from) >= '1990-01-01' THEN toString(target.valid_from)
           ELSE NULL
         END,
         source_event_date,
         source_expression_date,
         source_chunk_date
       ) AS valid_from,
       coalesce(target.valid_to, target.phase_valid_to) AS valid_to,
       CASE
         WHEN authority_rel.evidence_chunks IS NOT NULL AND size(authority_rel.evidence_chunks) > 0 THEN authority_rel.evidence_chunks
         WHEN authority_rel.source_chunk IS NOT NULL THEN [authority_rel.source_chunk]
         WHEN target.source_chunk IS NOT NULL THEN [target.source_chunk]
         ELSE []
       END AS evidence_chunks
  OPTIONAL MATCH (evidence_chunk:Chunk)
  WHERE evidence_chunk.chunk_id IN evidence_chunks
  OPTIONAL MATCH (evidence_chunk)<-[:HAS_PART]-(evidence_expr:Expression)
    -[:HAS_EMBODIMENT]->(:Manifestation)-[:HAS_EXEMPLAR]->(evidence_item:Item)
  WITH p, target, evidence_doc, source_doc_type, valid_from, valid_to,
       [source IN collect(DISTINCT
          CASE WHEN evidence_item.inbox_filename IS NULL THEN NULL
               ELSE {file: evidence_item.inbox_filename, chunk_id: evidence_chunk.chunk_id}
          END)
        WHERE source IS NOT NULL] AS evidence_sources
  RETURN p.label AS person,
         p.entityId AS person_id,
         target.entityId AS fact_id,
         'authority' AS branch,
         'signing_authority' AS fact_type,
         target.label AS relates_to,
         valid_from AS valid_from,
         valid_to AS valid_to,
         CASE
           WHEN coalesce(target.lifecycle_status, 'active') <> 'active' THEN target.lifecycle_status
           WHEN valid_to IS NOT NULL AND toString(valid_to) < toString(date()) THEN 'closed'
           WHEN valid_from IS NOT NULL AND toString(valid_from) < toString(date()) THEN 'closed'
           ELSE 'active'
         END AS lifecycle_status,
         source_doc_type AS doc_type,
         CASE
           WHEN size(evidence_sources) > 0 THEN evidence_sources
           WHEN evidence_doc IS NOT NULL AND NOT toString(evidence_doc) STARTS WITH '['
             THEN [{file: toString(evidence_doc), chunk_id: null}]
           ELSE []
         END AS sources
  UNION ALL
  WITH p
  MATCH (document:Instance)-[rel:SIGNED_BY|DESIGNATES_SIGNATORY|AUTHORIZES|HAS_AUTHORIZED_PARTY]->(p)
  WHERE $include_cancelled OR coalesce(document.lifecycle_status, 'active') = 'active'
  OPTIONAL MATCH (work:Work)-[:HAS_REALIZATION]->(document)
  OPTIONAL MATCH (document)-[:HAS_EMBODIMENT]->(:Manifestation)-[:HAS_EXEMPLAR]->(item:Item)
  OPTIONAL MATCH (document)-[:HAS_EFFECTIVE_DATE]->(document_date:Date)
  OPTIONAL MATCH (document)-[:HAS_PART]->(document_chunk:Chunk)
  WITH p, document, rel, type(rel) AS relation_type,
       head([title IN collect(DISTINCT work.title) WHERE title IS NOT NULL]) AS work_title,
       head([doc_type IN collect(DISTINCT work.doc_type) WHERE doc_type IS NOT NULL]) AS doc_type,
       head([effective_date IN collect(DISTINCT coalesce(work.effective_date, work.effectiveDate)) WHERE effective_date IS NOT NULL]) AS work_effective_date,
       max(CASE
             WHEN toString(document_date.iso_date) =~ '[0-9]{4}-[0-9]{2}-[0-9]{2}'
                  AND toString(document_date.iso_date) >= '1990-01-01' THEN toString(document_date.iso_date)
             WHEN toString(document_date.iso_date) = 'November 2000' THEN '2000-11-01'
             ELSE NULL
           END) AS document_expression_date,
       [text IN collect(DISTINCT document_chunk.text) WHERE text IS NOT NULL] AS chunk_texts,
       [file IN collect(DISTINCT item.inbox_filename) WHERE file IS NOT NULL] AS files
  OPTIONAL MATCH (source_event:Entity:Event)
  WHERE source_event.source_doc IN files
  WITH p, document, rel, relation_type, work_title, doc_type, work_effective_date,
       document_expression_date, chunk_texts, files,
       coalesce(rel.source_doc, document.source_doc, head(files)) AS evidence_doc,
       CASE
         WHEN rel.evidence_chunks IS NOT NULL AND size(rel.evidence_chunks) > 0 THEN rel.evidence_chunks
         WHEN rel.source_chunk IS NOT NULL THEN [rel.source_chunk]
         WHEN document.source_chunk IS NOT NULL THEN [document.source_chunk]
         ELSE []
       END AS evidence_chunks,
       min(coalesce(source_event.effective_date, source_event.effectiveDate, source_event.valid_from)) AS source_event_date
  WITH p, document, relation_type, work_title, doc_type, work_effective_date,
       document_expression_date, chunk_texts, files, evidence_doc, evidence_chunks, source_event_date,
       coalesce(work_title, document.title, document.label, head(files), '') AS title_text
  WITH p, document, relation_type, work_title, doc_type, work_effective_date,
       document_expression_date, chunk_texts, files, evidence_doc, evidence_chunks, source_event_date, title_text,
       [month IN [
         {name: 'January', number: '01'},
         {name: 'February', number: '02'},
         {name: 'March', number: '03'},
         {name: 'April', number: '04'},
         {name: 'May', number: '05'},
         {name: 'June', number: '06'},
         {name: 'July', number: '07'},
         {name: 'August', number: '08'},
         {name: 'September', number: '09'},
         {name: 'October', number: '10'},
         {name: 'November', number: '11'},
         {name: 'December', number: '12'}
       ] WHERE title_text CONTAINS month.name + ' '] AS title_months
  WITH p, document, relation_type, work_title, doc_type, work_effective_date,
       document_expression_date, chunk_texts, files, evidence_doc, evidence_chunks, source_event_date, title_text,
       CASE WHEN size(title_months) = 0 THEN NULL ELSE head(title_months) END AS title_month
  WITH p, document, relation_type, work_title, doc_type, work_effective_date,
       document_expression_date, chunk_texts, files, evidence_doc, evidence_chunks, source_event_date, title_text, title_month,
       CASE
         WHEN title_month IS NULL THEN NULL
         ELSE split(title_text, title_month.name + ' ')[1]
       END AS title_tail
  WITH p, document, relation_type, work_title, doc_type, work_effective_date,
       document_expression_date, chunk_texts, files, evidence_doc, evidence_chunks, source_event_date, title_text, title_month,
       CASE
         WHEN title_tail IS NULL OR NOT title_tail CONTAINS ',' THEN NULL
         ELSE trim(split(title_tail, ',')[0])
       END AS title_day,
       CASE
         WHEN title_tail IS NULL OR NOT title_tail CONTAINS ',' THEN NULL
         ELSE substring(trim(split(title_tail, ',')[1]), 0, 4)
       END AS title_year
  WITH p, document, relation_type, work_title, doc_type, chunk_texts, files, evidence_doc, evidence_chunks,
       CASE
         WHEN title_month IS NULL OR title_day IS NULL OR title_year IS NULL THEN NULL
         WHEN size(title_day) = 1 THEN title_year + '-' + title_month.number + '-0' + title_day
         ELSE title_year + '-' + title_month.number + '-' + title_day
       END AS title_date,
       CASE
         WHEN ANY(text IN chunk_texts WHERE toLower(text) CONTAINS '15 november 2012'
                                      OR toLower(text) CONTAINS '15 nov 2012') THEN '2012-11-15'
         WHEN ANY(text IN chunk_texts WHERE toLower(text) CONTAINS '14 november 2012'
                                      OR toLower(text) CONTAINS '14 nov 2012') THEN '2012-11-14'
         WHEN ANY(text IN chunk_texts WHERE toLower(text) CONTAINS '12 november 2012'
                                      OR toLower(text) CONTAINS 'nov 12 2012') THEN '2012-11-12'
         WHEN ANY(text IN chunk_texts WHERE toLower(text) CONTAINS '18 october 2012'
                                      OR toLower(text) CONTAINS '18 oct 2012') THEN '2012-10-18'
         WHEN ANY(text IN chunk_texts WHERE toLower(text) CONTAINS '17 october 2012'
                                      OR toLower(text) CONTAINS '17th day of october, 2012') THEN '2012-10-17'
         WHEN ANY(text IN chunk_texts WHERE toLower(text) CONTAINS '20. januar 2005') THEN '2005-01-20'
         WHEN ANY(text IN chunk_texts WHERE toLower(text) CONTAINS 'january 6, 2005'
                                      OR toLower(text) CONTAINS '01/06/2005') THEN '2005-01-06'
         WHEN ANY(text IN chunk_texts WHERE toLower(text) CONTAINS 'jan. 2003') THEN '2003-01-01'
         WHEN ANY(text IN chunk_texts WHERE toLower(text) CONTAINS 'november 2000') THEN '2000-11-01'
         ELSE NULL
       END AS chunk_signed_date,
       coalesce(work_effective_date, document.effective_date, document.effectiveDate, document_expression_date, source_event_date) AS graph_date
  WITH p, document, relation_type, work_title, doc_type, files, evidence_doc, evidence_chunks,
       coalesce(graph_date, title_date, chunk_signed_date) AS valid_from
  OPTIONAL MATCH (evidence_chunk:Chunk)
  WHERE evidence_chunk.chunk_id IN evidence_chunks
  OPTIONAL MATCH (evidence_chunk)<-[:HAS_PART]-(evidence_expr:Expression)
    -[:HAS_EMBODIMENT]->(:Manifestation)-[:HAS_EXEMPLAR]->(evidence_item:Item)
  WITH p, document, relation_type, work_title, doc_type, files, evidence_doc,
       valid_from,
       [source IN collect(DISTINCT
          CASE WHEN evidence_item.inbox_filename IS NULL THEN NULL
               ELSE {file: evidence_item.inbox_filename, chunk_id: evidence_chunk.chunk_id}
          END)
        WHERE source IS NOT NULL] AS evidence_sources
  RETURN p.label AS person,
         p.entityId AS person_id,
         document.entityId AS fact_id,
         'document' AS branch,
         CASE relation_type
           WHEN 'SIGNED_BY' THEN 'signed document'
           WHEN 'DESIGNATES_SIGNATORY' THEN 'designated as signatory'
           WHEN 'AUTHORIZES' THEN 'authorized by document'
           WHEN 'HAS_AUTHORIZED_PARTY' THEN 'authorized party'
           ELSE toLower(replace(relation_type, '_', ' '))
         END AS fact_type,
         coalesce(work_title, document.title, document.label, head(files)) AS relates_to,
         valid_from AS valid_from,
         NULL AS valid_to,
         CASE
           WHEN coalesce(document.lifecycle_status, 'active') <> 'active' THEN document.lifecycle_status
           WHEN valid_from IS NOT NULL AND toString(valid_from) < toString(date()) THEN 'closed'
           ELSE 'active'
         END AS lifecycle_status,
         doc_type AS doc_type,
         CASE
           WHEN size(evidence_sources) > 0 THEN evidence_sources
           WHEN evidence_doc IS NOT NULL AND NOT toString(evidence_doc) STARTS WITH '['
             THEN [{file: toString(evidence_doc), chunk_id: null}]
           WHEN size(files) > 0 THEN [file IN files | {file: file, chunk_id: null}]
           ELSE []
         END AS sources
  UNION ALL
  WITH p
  MATCH (event:Entity:Event)-[rel:HAS_ACTOR|HAS_UNDERGOER|HAS_COUNTERPARTY|ELECTS|DESIGNATES_SIGNATORY|CREATOR]->(p)
  WITH p, event, rel, coalesce(rel.source_doc, event.source_doc) AS evidence_doc
  OPTIONAL MATCH (source_work:Work)-[:HAS_REALIZATION]->(source_expr:Expression)
    -[:HAS_EMBODIMENT]->(:Manifestation)-[:HAS_EXEMPLAR]->(:Item {inbox_filename: evidence_doc})
  OPTIONAL MATCH (source_expr)-[:HAS_EFFECTIVE_DATE]->(source_date:Date)
  WITH p, event, rel, evidence_doc,
       head([doc_type IN collect(DISTINCT source_work.doc_type) WHERE doc_type IS NOT NULL]) AS source_doc_type,
       max(CASE
             WHEN toString(source_date.iso_date) =~ '[0-9]{4}-[0-9]{2}-[0-9]{2}'
                  AND toString(source_date.iso_date) >= '1990-01-01' THEN toString(source_date.iso_date)
             WHEN toString(source_date.iso_date) = 'November 2000' THEN '2000-11-01'
             ELSE NULL
          END) AS source_expression_date,
       CASE
         WHEN rel.evidence_chunks IS NOT NULL AND size(rel.evidence_chunks) > 0 THEN rel.evidence_chunks
         WHEN rel.source_chunk IS NOT NULL THEN [rel.source_chunk]
         WHEN event.source_chunk IS NOT NULL THEN [event.source_chunk]
         ELSE []
       END AS evidence_chunks
  WITH p, event, rel, evidence_doc, source_doc_type, evidence_chunks,
       coalesce(event.effective_date, event.effectiveDate, event.valid_from, source_expression_date) AS valid_from
  OPTIONAL MATCH (evidence_chunk:Chunk)
  WHERE evidence_chunk.chunk_id IN evidence_chunks
  OPTIONAL MATCH (evidence_chunk)<-[:HAS_PART]-(evidence_expr:Expression)
    -[:HAS_EMBODIMENT]->(:Manifestation)-[:HAS_EXEMPLAR]->(evidence_item:Item)
  WITH p, event, rel, evidence_doc, source_doc_type, valid_from,
       [source IN collect(DISTINCT
          CASE WHEN evidence_item.inbox_filename IS NULL THEN NULL
               ELSE {file: evidence_item.inbox_filename, chunk_id: evidence_chunk.chunk_id}
          END)
        WHERE source IS NOT NULL] AS evidence_sources
  RETURN p.label AS person,
         p.entityId AS person_id,
         event.entityId AS fact_id,
         'event' AS branch,
         toLower(type(rel)) AS fact_type,
         event.label AS relates_to,
         valid_from AS valid_from,
         NULL AS valid_to,
         'active' AS lifecycle_status,
         source_doc_type AS doc_type,
         CASE
           WHEN size(evidence_sources) > 0 THEN evidence_sources
           WHEN evidence_doc IS NOT NULL AND NOT toString(evidence_doc) STARTS WITH '['
             THEN [{file: toString(evidence_doc), chunk_id: null}]
           ELSE []
         END AS sources
}
RETURN person, person_id, fact_id, branch, fact_type, relates_to,
       valid_from, valid_to, lifecycle_status, doc_type, sources
ORDER BY coalesce(valid_from, '') DESC
""".strip()

ORGANIZATION_IDENTIFIERS = r"""
MATCH (n:Entity:LegalEntity {entityId: $organization_id})
MATCH (n)-[:IS_IDENTIFIED_BY|HAS_IDENTIFIER|IS_REGISTERED_BY]->(rid:Entity)
      -[:INSTANCE_OF]->(rid_class:Class)
WHERE rid_class.localName IN ['RegistrationIdentifier', 'LegalEntityIdentifier', 'TaxIdentifier', 'ChamberOfCommerceIdentifier', 'RegulatoryFilingIdentifier', 'BankAccountIdentifier', 'CertificateIdentifier', 'SWIFTIdentifier', 'DocumentReferenceIdentifier', 'RulingIdentifier', 'PassportIdentifier', 'NationalIDIdentifier']
CALL {
  WITH rid
  WITH rid,
       CASE
         WHEN rid.source_doc IS NULL THEN []
         ELSE [{file: rid.source_doc, chunk_id: rid.source_chunk}]
       END AS node_sources
  OPTIONAL MATCH (chunk:Chunk)-[:EVIDENCES|MENTIONS|RECORDS|DESIGNATES_SIGNATORY]->(rid)
  OPTIONAL MATCH (chunk)<-[:HAS_PART]-(chunk_expr:Expression)
                -[:HAS_EMBODIMENT]->(:Manifestation)
                -[:HAS_EXEMPLAR]->(chunk_item:Item)
  WITH rid,
       node_sources,
       [entry IN collect(DISTINCT
          CASE WHEN chunk IS NULL OR chunk_item.inbox_filename IS NULL THEN NULL
               ELSE {file: chunk_item.inbox_filename, chunk_id: chunk.chunk_id} END)
        WHERE entry IS NOT NULL] AS chunk_sources
  OPTIONAL MATCH (expr:Expression)-[:EVIDENCES|MENTIONS|RECORDS|DESIGNATES_SIGNATORY]->(rid)
  OPTIONAL MATCH (expr)-[:HAS_EMBODIMENT]->(:Manifestation)
                -[:HAS_EXEMPLAR]->(expr_item:Item)
  WITH node_sources,
       chunk_sources,
       [entry IN collect(DISTINCT
          CASE WHEN expr IS NULL OR expr_item.inbox_filename IS NULL THEN NULL
               ELSE {file: expr_item.inbox_filename, chunk_id: null} END)
        WHERE entry IS NOT NULL] AS expression_sources
  RETURN node_sources + chunk_sources + expression_sources AS evidence_sources
}
WITH n,
     coalesce(rid.identifierValue, rid.label) AS identifier,
     rid.entityId AS identifier_id,
     rid_class.localName AS kind,
     rid.scheme AS scheme,
     coalesce(rid.lifecycle_status, 'active') AS status,
     evidence_sources
WITH identifier,
     n.entityId AS organization_id,
     kind,
     scheme,
     status,
     [id IN collect(DISTINCT identifier_id) WHERE id IS NOT NULL] AS identifier_ids,
     reduce(raw_sources = [], source_list IN collect(evidence_sources) |
       raw_sources + [entry IN source_list WHERE entry IS NOT NULL]
     ) AS raw_sources
WITH identifier,
     organization_id,
     head(identifier_ids) AS identifier_id,
     kind,
     scheme,
     status,
     reduce(sources = [], entry IN raw_sources |
       CASE
         WHEN any(existing IN sources
                  WHERE existing.file = entry.file
                    AND coalesce(existing.chunk_id, '') = coalesce(entry.chunk_id, ''))
         THEN sources
         ELSE sources + [entry]
       END
     ) AS sources
RETURN identifier,
       organization_id,
       identifier_id,
       kind,
       scheme,
       status,
       sources
ORDER BY status, kind, identifier
""".strip()

ORGANIZATION_OFFICES = r"""
MATCH (n:Entity:LegalEntity {entityId: $organization_id})
MATCH (n)-[attachment:HAS_REGISTERED_ADDRESS]->(addr:Entity)
WHERE addr:ConventionalStreetAddress OR addr:PhysicalAddress
CALL {
  WITH addr
  OPTIONAL MATCH (chunk:Chunk)-[:EVIDENCES|MENTIONS|RECORDS|DESIGNATES_SIGNATORY]->(addr)
  OPTIONAL MATCH (chunk)<-[:HAS_PART]-(chunk_expr:Expression)
                -[:HAS_EMBODIMENT]->(:Manifestation)
                -[:HAS_EXEMPLAR]->(chunk_item:Item)
  WITH addr,
       [entry IN collect(DISTINCT
          CASE WHEN chunk IS NULL OR chunk_item.inbox_filename IS NULL THEN NULL
               ELSE {file: chunk_item.inbox_filename, chunk_id: chunk.chunk_id} END)
        WHERE entry IS NOT NULL] AS chunk_sources
  OPTIONAL MATCH (expr:Expression)-[:EVIDENCES|MENTIONS|RECORDS|DESIGNATES_SIGNATORY]->(addr)
  OPTIONAL MATCH (expr)-[:HAS_EMBODIMENT]->(:Manifestation)
                -[:HAS_EXEMPLAR]->(expr_item:Item)
  WITH chunk_sources,
       [entry IN collect(DISTINCT
          CASE WHEN expr IS NULL OR expr_item.inbox_filename IS NULL THEN NULL
               ELSE {file: expr_item.inbox_filename, chunk_id: null} END)
        WHERE entry IS NOT NULL] AS expression_sources
  RETURN chunk_sources + expression_sources AS linked_sources
}
WITH n,
     attachment,
     addr,
     CASE
       WHEN attachment.source_doc IS NULL THEN []
       ELSE [{file: attachment.source_doc, chunk_id: attachment.source_chunk}]
     END
     + CASE
         WHEN addr.source_doc IS NULL THEN []
         ELSE [{file: addr.source_doc, chunk_id: addr.source_chunk}]
       END
     + linked_sources AS raw_sources
WITH n,
     attachment,
     addr,
     reduce(sources = [], entry IN raw_sources |
       CASE
         WHEN any(existing IN sources
                  WHERE existing.file = entry.file
                    AND coalesce(existing.chunk_id, '') = coalesce(entry.chunk_id, ''))
         THEN sources
         ELSE sources + [entry]
       END
     ) AS sources
RETURN coalesce(addr.addressText, addr.street_line, addr.label) AS address,
       n.entityId                                             AS organization_id,
       addr.entityId                                          AS address_id,
       addr.street_line                                         AS street,
       addr.city                                                AS city,
       coalesce(addr.iso_alpha2, addr.country_code)             AS country_iso2,
       coalesce(addr.country_name, addr.name_en, addr.name, addr.country_code) AS country,
       attachment.valid_from                                    AS valid_from,
       attachment.valid_to                                      AS valid_to,
       coalesce(addr.lifecycle_status, 'active')                AS status,
       sources                                                  AS sources
ORDER BY coalesce(attachment.valid_from, attachment.valid_to, '') DESC,
         coalesce(attachment.valid_to, '9999-12-31') DESC,
         address
""".strip()

CAPITAL_HOLDERS = r"""
WITH coalesce($subject_id, '')      AS subject_id,
     coalesce($organization_id, '') AS organization_id,
     CASE WHEN coalesce($as_of, '') = '' THEN NULL ELSE $as_of END AS as_of,
     CASE WHEN coalesce($since, '') = '' THEN NULL ELSE $since END AS since_,
     CASE WHEN coalesce($until, '') = '' THEN NULL ELSE $until END AS until_
OPTIONAL MATCH (subject:BusinessSubject)
WHERE subject_id <> '' AND subject.subjectId = subject_id
WITH subject, subject_id, organization_id, as_of, since_, until_
MATCH (phase:Entity)
WHERE (organization_id = '' OR phase.entityId = organization_id)
  AND (subject_id = '' OR EXISTS {
    MATCH (subject)-[:HAS_PHASE]->(phase)
  })
MATCH (holder_state:Entity:ShareholdingPhase)-[:HOLDS_SHARES_OF]->(phase)
MATCH (holder_state)-[:HELD_BY]->(holder:Entity)
WHERE coalesce(holder_state.projection_active, true) = true
  AND holder_state.valid_from =~ '\\d{4}-\\d{2}-\\d{2}$'
  AND holder_state.share_role = 'issued'
  AND (
    as_of IS NULL
    OR (
      holder_state.valid_from <= as_of
      AND (holder_state.valid_to IS NULL OR holder_state.valid_to >= as_of)
    )
  )
  AND (
    as_of IS NOT NULL
    OR $include_cancelled
    OR coalesce(holder_state.lifecycle_status, 'active') = 'active'
  )
  AND (since_ IS NULL OR holder_state.valid_from >= since_)
  AND (until_ IS NULL OR holder_state.valid_from <= until_)
RETURN subject.label                              AS subject,
       phase.label                                AS organization,
       phase.entityId                             AS organization_id,
       holder_state.entityId                      AS shareholding_phase_id,
       CASE WHEN as_of IS NOT NULL
            THEN as_of ELSE holder_state.valid_from END
                                                   AS effective_date,
       holder.label                               AS holder,
       holder_state.share_role                    AS share_role,
       holder_state.share_class                   AS share_class,
       holder_state.share_count                   AS share_count,
       holder_state.ownership_pct                 AS ownership_pct,
       holder_state.valid_from                    AS valid_from,
       holder_state.valid_to                      AS valid_to,
       coalesce(holder_state.lifecycle_status, 'active')
                                                   AS status,
       coalesce(holder_state.evidence_conflict, false)
                                                   AS evidence_conflict,
       [doc IN coalesce(holder_state.source_docs, [])
          WHERE doc IS NOT NULL | {file: doc, chunk_id: NULL}]
                                                   AS sources
ORDER BY effective_date DESC, organization, holder
LIMIT toInteger($limit)
""".strip()

PERSON_ROLE_COLUMNS = (
    'person',
    'person_id',
    'fact_id',
    'tenure_kind',
    'role',
    'organization',
    'valid_from',
    'valid_to',
    'lifecycle_status',
    'sources',
)

PERSON_AUTHORITY_COLUMNS = (
    'person',
    'person_id',
    'fact_id',
    'branch',
    'fact_type',
    'relates_to',
    'valid_from',
    'valid_to',
    'lifecycle_status',
    'doc_type',
    'sources',
)

CAPITAL_HOLDER_COLUMNS = (
    'subject',
    'organization',
    'organization_id',
    'shareholding_phase_id',
    'effective_date',
    'holder',
    'share_role',
    'share_class',
    'share_count',
    'ownership_pct',
    'valid_from',
    'valid_to',
    'status',
    'evidence_conflict',
    'sources',
)
