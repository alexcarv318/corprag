# ruff: noqa: E501

from corporate_rag.graph.interfaces import BaseGraphReader
from corporate_rag.workflows.options import CAPITAL_EVENT_TYPES, IDENTIFIER_KIND_OPTIONS


def document_count(reader: BaseGraphReader) -> int:
    rows = reader.read(DOCUMENT_COUNT_CYPHER)
    raw_count = rows[0].get("document_count") if rows else 0
    return int(raw_count or 0)


def cypher_list(values: tuple[str, ...]) -> str:
    return "[" + ", ".join(repr(value) for value in values if value) + "]"


IDENTIFIER_KIND_LIST = cypher_list(IDENTIFIER_KIND_OPTIONS)
CAPITAL_EVENT_TYPE_LIST = cypher_list(CAPITAL_EVENT_TYPES)
DOCUMENT_COUNT_CYPHER = "MATCH (w:Work) RETURN count(DISTINCT w) AS document_count"

SUBJECT_OVERVIEW = """
MATCH (subject:BusinessSubject {subjectId: $subject_id})
OPTIONAL MATCH (subject)-[:HAS_PHASE]->(phase:Entity)
OPTIONAL MATCH (phase)-[:INSTANCE_OF]->(class:Class)
WITH subject, phase, [name IN collect(DISTINCT class.localName) WHERE name IS NOT NULL] AS classes
OPTIONAL MATCH (phase)-[address_rel:HAS_REGISTERED_ADDRESS]->(address)
WHERE address IS NULL OR coalesce(address.lifecycle_status, 'active') <> 'superseded'
WITH subject, phase, classes, address_rel, address
ORDER BY coalesce(address_rel.valid_from, address_rel.valid_to, '') DESC
WITH subject, phase, classes, head(collect(address)) AS registered_office
RETURN subject.subjectId AS subject_id,
       subject.label AS subject,
       phase.entityId AS phase_id,
       phase.label AS phase_label,
       classes AS phase_classes,
       phase.phase_valid_from AS phase_valid_from,
       phase.phase_valid_to AS phase_valid_to,
       phase.registration_number AS registration_number,
       phase.registration_scheme AS registration_scheme,
       phase.legal_form_suffix AS legal_form,
       phase.governing_law AS governing_law,
       coalesce(phase.status, phase.lifecycle_status, 'active') AS status,
       CASE WHEN registered_office IS NULL THEN NULL ELSE {
         address: coalesce(registered_office.addressText, registered_office.street_line, registered_office.label),
         city: registered_office.city,
         country: coalesce(registered_office.country_name, registered_office.name, registered_office.country_code)
       } END AS registered_office,
       CASE WHEN phase.source_doc IS NULL THEN [] ELSE [{file: phase.source_doc, chunk_id: phase.source_chunk}] END AS sources
ORDER BY coalesce(phase.phase_valid_from, '')
""".strip()

SUBJECT_IDENTIFIERS = f"""
MATCH (subject:BusinessSubject {{subjectId: $subject_id}})-[:HAS_PHASE]->(phase:Entity)
OPTIONAL MATCH (phase)-[:IS_IDENTIFIED_BY]->(identifier:Entity)-[:INSTANCE_OF]->(kind:Class)
WHERE kind.localName IN {IDENTIFIER_KIND_LIST}
RETURN subject.subjectId AS subject_id,
       subject.label AS subject,
       phase.entityId AS phase_id,
       phase.label AS phase_label,
       phase.phase_valid_from AS phase_valid_from,
       phase.phase_valid_to AS phase_valid_to,
       identifier.entityId AS identifier_id,
       coalesce(identifier.label, identifier.identifierValue, phase.registration_number) AS identifier,
       coalesce(kind.localName, 'RegistrationIdentifier') AS kind,
       coalesce(identifier.scheme, phase.registration_scheme) AS scheme,
       phase.governing_law AS governing_law,
       coalesce(identifier.lifecycle_status, phase.status, 'active') AS status,
       CASE WHEN identifier.source_doc IS NULL THEN [] ELSE [{{file: identifier.source_doc, chunk_id: identifier.source_chunk}}] END AS sources
ORDER BY coalesce(phase.phase_valid_from, '') DESC, kind, identifier
""".strip()

SUBJECT_BOARD_HISTORY = """
MATCH (subject:BusinessSubject {subjectId: $subject_id})-[:HAS_PHASE]->(phase:Entity)
MATCH (membership:Entity:BoardMembership)-[membership_edge:INVOLVES_CONTROLLED_THING]->(phase)
MATCH (membership)-[:HAS_PARTY_IN_CONTROL]->(person:Entity:Person)
WITH subject, phase, membership, membership_edge, person,
     [file IN [
       membership.appointment_source_doc,
       membership.valid_from_source_doc,
       membership.source_doc
     ] WHERE file IS NOT NULL] AS source_files
WHERE membership_edge.valid_to IS NULL
  AND NOT toLower(coalesce(membership.role_title, '')) IN [
  'chairman', 'chairperson', 'chairman of meeting', 'chairperson of meeting'
]
  AND EXISTS {
    MATCH (work:Work)-[:HAS_REALIZATION]->(:Expression)-[:HAS_EMBODIMENT]->(:Manifestation)-[:HAS_EXEMPLAR]->(item:Item)
    WHERE item.inbox_filename IN source_files
      AND work.doc_type IN [
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
      ]
  }
RETURN subject.label AS subject,
       phase.entityId AS phase_id,
       phase.label AS legal_entity,
       person.label AS person,
       person.entityId AS person_id,
       membership.entityId AS board_membership_id,
       membership.role_title AS role,
       membership.valid_from AS valid_from,
       membership.valid_to AS valid_to,
       coalesce(membership.lifecycle_status, 'active') AS status,
       [] AS events,
       [] AS event_types,
       CASE WHEN membership.source_doc IS NULL THEN 'missing_document' ELSE 'documented' END AS evidence_status,
       CASE WHEN membership.source_doc IS NULL THEN [] ELSE [{file: membership.source_doc, chunk_id: membership.source_chunk}] END AS sources,
       [] AS evidence_doc_types,
       [] AS evidence_titles
ORDER BY CASE status WHEN 'active' THEN 0 ELSE 1 END, coalesce(valid_from, '') DESC, legal_entity, person
""".strip()

PERSON_OVERVIEW = """
MATCH (person:Entity:Person)
WHERE coalesce($person_id, '') = '' OR person.entityId = $person_id
OPTIONAL MATCH (chunk:Chunk)-[:EVIDENCES|MENTIONS|RECORDS|DESIGNATES_SIGNATORY]->(person)
OPTIONAL MATCH (chunk)<-[:HAS_PART]-(:Expression)-[:HAS_EMBODIMENT]->(:Manifestation)-[:HAS_EXEMPLAR]->(item:Item)
WITH person, [source IN collect(DISTINCT {file: item.inbox_filename, chunk_id: chunk.chunk_id}) WHERE source.file IS NOT NULL] AS mentions
OPTIONAL MATCH (person)-[:IS_IDENTIFIED_BY]->(passport:PassportIdentifier)
RETURN person.entityId AS person_id,
       person.label AS person,
       person.date_of_birth AS date_of_birth,
       person.nationality AS nationality,
       person.residence AS residence,
       [value IN collect(DISTINCT coalesce(passport.label, head(passport.aliases))) WHERE value IS NOT NULL] AS passport,
       size(mentions) AS mention_count,
       mentions AS mentions
ORDER BY mention_count DESC, person.label
LIMIT 250
""".strip()

PERSON_ROLES = """
MATCH (person:Entity:Person {entityId: $person_id})
MATCH (role:Entity)-[:HAS_PARTY_IN_CONTROL|HAS_INCUMBENT|HAS_PARTY_ROLE]->(person)
WHERE NOT ('MeetingFunction' IN labels(role))
  AND coalesce(role.lifecycle_status, role.status, 'active') <> 'superseded'
OPTIONAL MATCH (role)-[:INVOLVES_CONTROLLED_THING|HAS_AUTHORIZING_PARTY|CONCERNS_ORGANIZATION]->(org:Entity)
RETURN DISTINCT person.entityId AS person_id,
       person.label AS person,
       role.entityId AS role_id,
       labels(role) AS role_labels,
       coalesce(role.role_title, role.label, head(labels(role))) AS role,
       org.entityId AS organization_id,
       org.label AS organization,
       role.valid_from AS valid_from,
       role.valid_to AS valid_to,
       coalesce(role.lifecycle_status, role.status, 'active') AS status,
       CASE WHEN role.source_doc IS NULL THEN [] ELSE [{file: role.source_doc, chunk_id: role.source_chunk}] END AS sources
ORDER BY coalesce(valid_from, '') DESC, organization, role
""".strip()

PERSON_AUTHORITY = """
MATCH (person:Entity:Person {entityId: $person_id})
OPTIONAL MATCH (poa:Entity:PowerOfAttorney)-[:IS_CONFERRED_ON]->(person)
OPTIONAL MATCH (document)-[document_relation:SIGNED_BY|DESIGNATES_SIGNATORY|AUTHORIZES|HAS_AUTHORIZED_PARTY]->(person)
WITH person, poa, document, document_relation
WHERE poa IS NOT NULL OR document IS NOT NULL
RETURN person.entityId AS person_id,
       person.label AS person,
       CASE WHEN poa IS NOT NULL THEN 'authority' ELSE 'document' END AS branch,
       coalesce(poa.entityId, document.entityId) AS fact_id,
       coalesce(poa.label, document.label) AS fact,
       coalesce(poa.scope, type(document_relation)) AS relation,
       coalesce(poa.valid_from, document.effectiveDate, document.effective_date) AS valid_from,
       poa.valid_to AS valid_to,
       coalesce(poa.lifecycle_status, document.lifecycle_status, 'active') AS status,
       CASE
         WHEN poa.source_doc IS NOT NULL THEN [{file: poa.source_doc, chunk_id: poa.source_chunk}]
         WHEN document.source_doc IS NOT NULL THEN [{file: document.source_doc, chunk_id: document.source_chunk}]
         ELSE []
       END AS sources
ORDER BY CASE branch WHEN 'authority' THEN 0 ELSE 1 END, coalesce(valid_from, '') DESC, fact
""".strip()

ORGANIZATION_OVERVIEW = """
MATCH (org:Entity:LegalEntity)
WHERE coalesce($organization_id, '') = '' OR org.entityId = $organization_id
OPTIONAL MATCH (org)-[:INSTANCE_OF]->(class:Class)
OPTIONAL MATCH (subject:BusinessSubject)-[:HAS_PHASE]->(org)
OPTIONAL MATCH (org)-[:HAS_LEGAL_FORM]->(form)
OPTIONAL MATCH (org)-[:HAS_LEGAL_NAME]->(name)
OPTIONAL MATCH (org)-[:IS_IDENTIFIED_BY]->(identifier:RegistrationIdentifier)
RETURN org.entityId AS organization_id,
       org.label AS organization,
       [value IN collect(DISTINCT class.localName) WHERE value IS NOT NULL] AS fibo_classes,
       head([value IN collect(DISTINCT form.label) WHERE value IS NOT NULL]) AS legal_form,
       [value IN collect(DISTINCT name.label) WHERE value IS NOT NULL] AS legal_names,
       org.governing_law AS governing_law,
       org.registration_number AS registration_number,
       [value IN collect(DISTINCT coalesce(identifier.label, identifier.identifierValue)) WHERE value IS NOT NULL] AS identifiers,
       subject.subjectId AS subject_id,
       subject.label AS subject_family,
       coalesce(org.status, org.lifecycle_status, 'active') AS status
ORDER BY organization
LIMIT 500
""".strip()

ORGANIZATION_IDENTIFIERS = f"""
MATCH (org:Entity {{entityId: $organization_id}})
OPTIONAL MATCH (org)-[:IS_IDENTIFIED_BY]->(identifier:Entity)-[:INSTANCE_OF]->(kind:Class)
WHERE kind.localName IN {IDENTIFIER_KIND_LIST}
RETURN org.entityId AS organization_id,
       org.label AS organization,
       identifier.entityId AS identifier_id,
       coalesce(identifier.label, identifier.identifierValue, org.registration_number) AS identifier,
       coalesce(kind.localName, 'RegistrationIdentifier') AS kind,
       coalesce(identifier.scheme, org.registration_scheme) AS scheme,
       coalesce(identifier.lifecycle_status, org.status, 'active') AS status,
       CASE WHEN identifier.source_doc IS NULL THEN [] ELSE [{{file: identifier.source_doc, chunk_id: identifier.source_chunk}}] END AS sources
ORDER BY kind, identifier
""".strip()

ORGANIZATION_OFFICES = """
MATCH (org:Entity {entityId: $organization_id})-[rel:HAS_REGISTERED_ADDRESS|HAS_OFFICE|IS_LOCATED_IN|HAS_HEADQUARTERS_ADDRESS]->(address)
WHERE address:ConventionalStreetAddress OR address:PhysicalAddress OR address:Jurisdiction
  AND coalesce(address.lifecycle_status, 'active') <> 'superseded'
WITH org, address, collect(rel) AS rels
WITH org, address, head(rels) AS rel
RETURN org.entityId AS organization_id,
       org.label AS organization,
       type(rel) AS relation,
       coalesce(address.addressText, address.street_line, address.label) AS address,
       address.city AS city,
       coalesce(address.country_name, address.name, address.country_code) AS country,
       rel.valid_from AS valid_from,
       rel.valid_to AS valid_to,
       coalesce(address.lifecycle_status, 'active') AS status,
       CASE WHEN address.source_doc IS NULL THEN [] ELSE [{file: address.source_doc, chunk_id: address.source_chunk}] END AS sources
ORDER BY coalesce(valid_from, '') DESC, address
""".strip()

DOCUMENTS_SEARCH = """
MATCH (work:Work)-[:HAS_REALIZATION]->(expression:Expression)-[:HAS_EMBODIMENT]->(:Manifestation)-[:HAS_EXEMPLAR]->(item:Item)
OPTIONAL MATCH (expression)-[:HAS_EFFECTIVE_DATE]->(date:Entity:Date)
WITH work, expression, item, coalesce(expression.effective_date, toString(date.iso_date), toString(work.loaded_at)) AS effective_date
WHERE ($doc_type IS NULL OR size($doc_type) = 0 OR work.doc_type IN $doc_type)
  AND ($file IS NULL OR $file = '' OR item.item_id = $file OR item.inbox_filename = $file)
  AND ($text_query IS NULL OR $text_query = ''
       OR toLower(coalesce(work.title, '')) CONTAINS toLower($text_query)
       OR toLower(coalesce(work.summary, '')) CONTAINS toLower($text_query)
       OR toLower(coalesce(work.doc_type, '')) CONTAINS toLower($text_query))
  AND ($signatory_person_id IS NULL OR $signatory_person_id = '' OR EXISTS {
    MATCH (expression)-[:DESIGNATES_SIGNATORY|SIGNED_BY]->(:Entity:Person {entityId: $signatory_person_id})
  })
  AND ($subject_id IS NULL OR $subject_id = '' OR EXISTS {
    MATCH (:BusinessSubject {subjectId: $subject_id})-[:HAS_PHASE]->(phase:Entity)
    MATCH (expression)-[:MENTIONS|RECORDS|EVIDENCES|DESIGNATES_SIGNATORY]->(phase)
  })
RETURN work.work_id AS work_id,
       expression.expression_id AS expression_id,
       item.item_id AS item_id,
       work.title AS title,
       work.doc_type AS doc_type,
       item.inbox_filename AS file,
       effective_date AS effective_date,
       coalesce(work.lifecycle_status, 'active') AS work_lifecycle_status,
       coalesce(expression.lifecycle_status, 'active') AS expression_lifecycle_status,
       coalesce(item.lifecycle_status, 'active') AS item_lifecycle_status,
       work.summary AS summary,
       CASE WHEN item.inbox_filename IS NULL THEN [] ELSE [{file: item.inbox_filename, chunk_id: null}] END AS sources
ORDER BY effective_date DESC, title
LIMIT toInteger($limit)
""".strip()

CAPITAL_EVENTS = f"""
MATCH (event:Entity:Event)
WHERE event.eventType IN {CAPITAL_EVENT_TYPE_LIST}
OPTIONAL MATCH (event)-[:HAS_EFFECTIVE_DATE]->(date:Date)
WITH event, coalesce(event.effectiveDate, event.effective_date, toString(date.iso_date)) AS effective_date
WHERE ($since IS NULL OR effective_date >= $since)
  AND ($until IS NULL OR effective_date <= $until)
  AND ($event_type IS NULL OR $event_type = '' OR event.eventType = $event_type)
  AND ($subject_id IS NULL OR $subject_id = '' OR EXISTS {{
    MATCH (:BusinessSubject {{subjectId: $subject_id}})-[:HAS_PHASE]->(phase:Entity)
    MATCH (event)-[:HAS_ACTOR|HAS_UNDERGOER|HAS_COUNTERPARTY|INVOLVES_CONTROLLED_THING|RELATED_ENDEAVOUR]->(phase)
  }})
  AND ($organization_id IS NULL OR $organization_id = '' OR EXISTS {{
    MATCH (event)-[:HAS_ACTOR|HAS_UNDERGOER|HAS_COUNTERPARTY|INVOLVES_CONTROLLED_THING|RELATED_ENDEAVOUR]->(:Entity {{entityId: $organization_id}})
  }})
OPTIONAL MATCH (event)-[:HAS_ACTOR]->(actor:Entity)
OPTIONAL MATCH (event)-[:HAS_UNDERGOER]->(undergoer:Entity)
OPTIONAL MATCH (event)-[:HAS_COUNTERPARTY]->(counterparty:Entity)
OPTIONAL MATCH (event)-[:HAS_NOTIONAL_AMOUNT]->(amount:Entity:MonetaryAmount)
RETURN event.entityId AS event_id,
       event.label AS event,
       event.eventType AS event_type,
       effective_date AS effective_date,
       [value IN collect(DISTINCT actor.label) WHERE value IS NOT NULL] AS actors,
       [value IN collect(DISTINCT undergoer.label) WHERE value IS NOT NULL] AS affected_parties,
       [value IN collect(DISTINCT counterparty.label) WHERE value IS NOT NULL] AS counterparties,
       head([value IN collect(DISTINCT amount.amount) WHERE value IS NOT NULL]) AS amount,
       head([value IN collect(DISTINCT amount.currency) WHERE value IS NOT NULL]) AS currency,
       CASE WHEN event.source_doc IS NULL THEN [] ELSE [{{file: event.source_doc, chunk_id: event.source_chunk}}] END AS sources,
       coalesce(event.lifecycle_status, 'active') AS status
ORDER BY effective_date DESC, event
LIMIT toInteger($limit)
""".strip()

CAPITAL_HOLDERS = """
MATCH (holding:Entity:Shareholding)
OPTIONAL MATCH (holding)-[:IS_HELD_BY]->(holder:Entity)
OPTIONAL MATCH (holding)-[:INVOLVES_CONTROLLED_THING|IS_ISSUED_BY]->(org:Entity)
WITH holding, holder, org
WHERE ($organization_id IS NULL OR $organization_id = '' OR org.entityId = $organization_id)
  AND ($subject_id IS NULL OR $subject_id = '' OR EXISTS {
    MATCH (:BusinessSubject {subjectId: $subject_id})-[:HAS_PHASE]->(phase:Entity)
    WHERE phase = org OR phase = holder
  })
RETURN holding.entityId AS holding_id,
       org.entityId AS organization_id,
       org.label AS organization,
       holder.entityId AS holder_id,
       holder.label AS holder,
       holding.share_class AS share_class,
       holding.number_of_shares AS number_of_shares,
       holding.percentage AS percentage,
       coalesce(holding.valid_from, holding.as_of) AS valid_from,
       holding.valid_to AS valid_to,
       coalesce(holding.lifecycle_status, 'active') AS status,
       CASE WHEN holding.source_doc IS NULL THEN [] ELSE [{file: holding.source_doc, chunk_id: holding.source_chunk}] END AS sources
ORDER BY coalesce(valid_from, '') DESC, organization, holder
LIMIT 500
""".strip()

POA_REGISTER = """
MATCH (poa:Entity:PowerOfAttorney)
WHERE ($include_cancelled OR coalesce(poa.lifecycle_status, 'active') = 'active')
  AND ($subject_id IS NULL OR $subject_id = '' OR EXISTS {
    MATCH (:BusinessSubject {subjectId: $subject_id})-[:HAS_PHASE]->(phase:Entity)
    WHERE (poa)-[:HAS_AUTHORIZING_PARTY|CONCERNS_ORGANIZATION]->(phase)
  })
  AND ($involves_person_id IS NULL OR $involves_person_id = '' OR EXISTS {
    MATCH (poa)-[:IS_CONFERRED_ON]->(:Entity:Person {entityId: $involves_person_id})
  })
  AND ($involves_organization_id IS NULL OR $involves_organization_id = '' OR EXISTS {
    MATCH (poa)-[:HAS_CONFERRED_ON_ORGANIZATION|HAS_AUTHORIZING_PARTY|CONCERNS_ORGANIZATION]->(:Entity {entityId: $involves_organization_id})
  })
OPTIONAL MATCH (subject:BusinessSubject)-[:HAS_PHASE]->(phase:Entity)<-[:HAS_AUTHORIZING_PARTY|CONCERNS_ORGANIZATION]-(poa)
OPTIONAL MATCH (poa)-[:IS_CONFERRED_ON]->(person:Entity:Person)
OPTIONAL MATCH (poa)-[:HAS_CONFERRED_ON_ORGANIZATION]->(firm:Entity)
OPTIONAL MATCH (poa)-[:HAS_AUTHORIZING_PARTY]->(authorizing:Entity)
OPTIONAL MATCH (poa)-[:CONCERNS_ORGANIZATION]->(concerned:Entity)
RETURN subject.label AS subject,
       phase.entityId AS phase_id,
       phase.label AS phase,
       phase.phase_valid_from AS phase_valid_from,
       phase.phase_valid_to AS phase_valid_to,
       poa.entityId AS poa_id,
       poa.label AS poa_label,
       poa.scope AS scope,
       poa.signature_mode AS signature_mode,
       poa.valid_from AS valid_from,
       poa.valid_to AS valid_to,
       poa.valid_to_event_id AS valid_to_event_id,
       coalesce(poa.lifecycle_status, 'active') AS lifecycle_status,
       poa.revocation_terms AS revocation_terms,
       poa.grounding_quote AS grounding_quote,
       [value IN collect(DISTINCT person.label) WHERE value IS NOT NULL] AS grantee_persons,
       [value IN collect(DISTINCT firm.label) WHERE value IS NOT NULL] AS firm_grantees,
       [value IN collect(DISTINCT authorizing.label) WHERE value IS NOT NULL] AS authorizing_parties,
       [value IN collect(DISTINCT concerned.label) WHERE value IS NOT NULL] AS concerned_organizations,
       [] AS supporting_titles,
       CASE WHEN poa.source_doc IS NULL THEN [] ELSE [{file: poa.source_doc, chunk_id: poa.source_chunk}] END AS sources
ORDER BY CASE lifecycle_status WHEN 'active' THEN 0 ELSE 1 END, coalesce(valid_from, '') DESC, poa_label
""".strip()

EVENTS_TIMELINE = """
MATCH (event:Entity:Event)
OPTIONAL MATCH (event)-[:HAS_EFFECTIVE_DATE]->(date:Entity:Date)
WITH event, coalesce(event.effectiveDate, event.effective_date, toString(date.iso_date)) AS effective_date
WHERE ($since IS NULL OR effective_date >= $since)
  AND ($until IS NULL OR effective_date <= $until)
  AND ($event_type IS NULL OR $event_type = '' OR event.eventType = $event_type)
  AND ($q IS NULL OR $q = '' OR toLower(coalesce(event.label, '')) CONTAINS toLower($q) OR toLower(coalesce(event.eventType, '')) CONTAINS toLower($q))
  AND ($subject_id IS NULL OR $subject_id = '' OR EXISTS {
    MATCH (:BusinessSubject {subjectId: $subject_id})-[:HAS_PHASE]->(phase:Entity)
    MATCH (event)-[:HAS_ACTOR|HAS_UNDERGOER|HAS_COUNTERPARTY|INVOLVES_CONTROLLED_THING|RELATED_ENDEAVOUR]->(phase)
  })
  AND ($participant_id IS NULL OR $participant_id = '' OR EXISTS {
    MATCH (event)-[:HAS_ACTOR|HAS_UNDERGOER|HAS_COUNTERPARTY]->(:Entity {entityId: $participant_id})
  })
OPTIONAL MATCH (event)-[:HAS_ACTOR]->(actor:Entity)
OPTIONAL MATCH (event)-[:HAS_UNDERGOER]->(undergoer:Entity)
OPTIONAL MATCH (event)-[:HAS_COUNTERPARTY]->(counterparty:Entity)
OPTIONAL MATCH (event)-[:HAS_NOTIONAL_AMOUNT]->(amount:Entity:MonetaryAmount)
RETURN event.entityId AS event_id,
       event.label AS event,
       event.eventType AS event_type,
       effective_date AS effective_date,
       [value IN collect(DISTINCT actor.label) WHERE value IS NOT NULL] AS actors,
       [value IN collect(DISTINCT undergoer.label) WHERE value IS NOT NULL] AS affected_parties,
       [value IN collect(DISTINCT counterparty.label) WHERE value IS NOT NULL] AS counterparties,
       head([value IN collect(DISTINCT amount.amount) WHERE value IS NOT NULL]) AS amount,
       head([value IN collect(DISTINCT amount.currency) WHERE value IS NOT NULL]) AS currency,
       CASE WHEN event.source_doc IS NULL THEN [] ELSE [{file: event.source_doc, chunk_id: event.source_chunk}] END AS sources,
       coalesce(event.lifecycle_status, 'active') AS status
ORDER BY effective_date DESC, event
LIMIT toInteger($limit)
""".strip()

DATA_MODEL_GUIDE = """
RETURN 'guide' AS section,
       'Corporate graph workflow model' AS title,
       'BusinessSubject, Entity, Event, Work, Expression, Manifestation, Item, Chunk, Class' AS summary
""".strip()

DATA_MODEL_CLASSES = """
MATCH (class:Class)
WHERE $query IS NULL OR $query = ''
   OR toLower(class.localName) CONTAINS toLower($query)
   OR toLower(coalesce(class.label, '')) CONTAINS toLower($query)
   OR toLower(coalesce(class.definition, '')) CONTAINS toLower($query)
RETURN class.localName AS local_name,
       coalesce(class.label, class.localName) AS label,
       class.module AS module,
       class.definition AS definition
ORDER BY local_name
LIMIT toInteger($limit)
""".strip()


SUBJECT_IDENTIFIER_COLUMNS = (
    "subject_id",
    "subject",
    "phase_id",
    "phase_label",
    "phase_valid_from",
    "phase_valid_to",
    "identifier_id",
    "identifier",
    "kind",
    "scheme",
    "governing_law",
    "status",
    "sources",
)

SUBJECT_BOARD_HISTORY_COLUMNS = (
    "subject",
    "phase_id",
    "legal_entity",
    "person",
    "person_id",
    "board_membership_id",
    "role",
    "valid_from",
    "valid_to",
    "status",
    "events",
    "event_types",
    "evidence_status",
    "sources",
    "evidence_doc_types",
    "evidence_titles",
)

PERSON_ROLE_COLUMNS = (
    "person_id",
    "person",
    "role_id",
    "role_labels",
    "role",
    "organization_id",
    "organization",
    "valid_from",
    "valid_to",
    "status",
    "sources",
)

PERSON_AUTHORITY_COLUMNS = (
    "person_id",
    "person",
    "branch",
    "fact_id",
    "fact",
    "relation",
    "valid_from",
    "valid_to",
    "status",
    "sources",
)

ORGANIZATION_IDENTIFIER_COLUMNS = (
    "organization_id",
    "organization",
    "identifier_id",
    "identifier",
    "kind",
    "scheme",
    "status",
    "sources",
)

ORGANIZATION_OFFICE_COLUMNS = (
    "organization_id",
    "organization",
    "relation",
    "address",
    "city",
    "country",
    "valid_from",
    "valid_to",
    "status",
    "sources",
)

CAPITAL_HOLDER_COLUMNS = (
    "holding_id",
    "organization_id",
    "organization",
    "holder_id",
    "holder",
    "share_class",
    "number_of_shares",
    "percentage",
    "valid_from",
    "valid_to",
    "status",
    "sources",
)
