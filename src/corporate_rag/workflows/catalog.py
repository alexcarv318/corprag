from corporate_rag.workflows import repository
from corporate_rag.workflows.models import Parameter, Workflow

FIND_SUBJECT = Workflow(
    workflow_id='find.subject',
    title='Find a business subject',
    category='General',
    description=
                (
                    'Look up a business subject and see every legal incarnation it has lived '
                    'through. Pick a business subject from the dropdown and the result shows one '
                    'row for each legal entity the business subject has been — for example a '
                    'Cyprus Limited, a Curaçao N.V., or a Swiss SA — with the dates it was '
                    'active, registration number, registry, legal form, governing law, status, '
                    'the latest registered office known for that phase, and the primary registry '
                    "documents that anchor each phase's start and end dates. The same result also "
                    'includes detail tables for identifiers and event-sourced board history '
                    "across the subject's full history."
                ),
    cypher=repository.SUBJECT_OVERVIEW,
    parameters=(
        Parameter(
            name='subject_id',
            label='Business subject',
            description='Type to search and pick a business subject.',
            required=True,
            default=None,
            placeholder='Search for a business subject…',
        ),
    ),
    output_columns=
        (
            'subject_id',
            'subject',
            'phase_id',
            'phase_label',
            'phase_classes',
            'phase_valid_from',
            'phase_valid_to',
            'registration_number',
            'registration_scheme',
            'legal_form',
            'governing_law',
            'status',
            'registered_office',
            'sources',
        ),
    use_cases=
        (
            'What are all the legal forms this business subject has had?',
            'Show me the timeline of this business subject.',
        ),
)

FIND_ORGANIZATION = Workflow(
    workflow_id='find.organization',
    title='Find an organization',
    category='General',
    description=
                (
                    'Look up any legal entity — corporations, partnerships, limited companies, '
                    'and so on. Leave the search blank to browse everything (most-mentioned '
                    'first), or pick one to focus on a single company. Each row shows the entity '
                    'class, jurisdiction, registered office, registration numbers, when it was '
                    'incorporated, when it was dissolved (if it was), and the supporting '
                    'mentions. When you focus on a single organization, the result also breaks '
                    'out every identifier and every registered office it has carried into their '
                    'own tables — shown only when the organization actually has more than the '
                    'summary can hold.'
                ),
    cypher=repository.ORGANIZATION_OVERVIEW,
    parameters=(
        Parameter(
            name='organization_id',
            label='Organization',
            description=
                        (
                            'Leave blank to browse everything, or pick one organization to focus '
                            'on a single company.'
                        ),
            default=None,
            placeholder='Search for an organization (optional)…',
        ),
    ),
    output_columns=
        (
            'organization_id',
            'label',
            'fibo_classes',
            'jurisdictions',
            'registered_offices',
            'registration_numbers',
            'date_of_incorporation',
            'date_of_dissolution',
            'mentions',
            'mention_count',
            'edge_count',
        ),
    use_cases=
        (
            'Which organizations show up most often?',
            'What is the legal profile of this counterparty?',
            'Is this company still active, or when was it dissolved?',
        ),
)

FIND_PERSON = Workflow(
    workflow_id='find.person',
    title='Find a person',
    category='General',
    description=
                (
                    'Look up directors, signatories, officers, and other individuals. Leave the '
                    'search blank to browse everyone — the most-mentioned people come first — or '
                    "pick one person to focus on a single individual. Each row shows the person's "
                    'basic identity details. When you focus on a single person, the result also '
                    "breaks out that person's roles and affiliations and their authority and "
                    'documents into their own tables, each ordered by start date with the most '
                    'recent first and including inactive rows.'
                ),
    cypher=repository.PERSON_OVERVIEW,
    parameters=(
        Parameter(
            name='person_id',
            label='Person',
            description=
                        (
                            'Leave blank to browse everyone, or pick one person to focus on a '
                            'single individual.'
                        ),
            default=None,
            placeholder='Search for a person (optional)…',
        ),
    ),
    output_columns=
        (
            'person_id',
            'person',
            'date_of_birth',
            'nationality',
            'residence',
            'passport',
            'mention_count',
            'mentions',
        ),
    use_cases=
        (
            'Who is this person and what are their name variants?',
            'Find a director before searching for documents they signed.',
            "Confirm a person's identity before reviewing their authority.",
        ),
)

DOCUMENTS_SEARCH = Workflow(
    workflow_id='documents.search',
    title='Find documents',
    category='General',
    description=
                (
                    'Search across every document. Combine any of the filters — document type, '
                    'who signed it, which business subject it is about, a keyword in the title or '
                    'summary. Leave every filter blank to browse the full corpus up to the result '
                    'limit.'
                ),
    cypher=repository.DOCUMENTS_SEARCH,
    parameters=(
        Parameter(
            name='doc_type',
            label='Document type',
            kind='select',
            description='Pick a type such as share certificate or board resolution.',
            default='',
            options=
                (
                    '',
                    'incorporation_certificate',
                    'articles_of_association_or_bylaws',
                    'continuation_certificate',
                    'discontinuance_certificate',
                    'dissolution_certificate',
                    'registry_extract_certificate',
                    'registry_filing',
                    'administrative_certificate',
                    'good_standing_certificate',
                    'board_resolution',
                    'board_meeting_minutes',
                    'shareholder_resolution',
                    'shareholder_meeting_minutes',
                    'director_appointment',
                    'director_resignation',
                    'director_resolution',
                    'share_certificate',
                    'share_register',
                    'share_transfer_agreement',
                    'share_contribution_agreement',
                    'power_of_attorney',
                    'proxy',
                    'intercompany_or_other_agreement',
                    'banking_payment_or_credit_record',
                    'receivables_purchase_agreement',
                    'reorganization_resolution',
                    'reorganization_deed',
                    'redomiciliation_application',
                    'annual_accounts_financial_statements',
                    'tax_document',
                    'regulatory_filing',
                    'legal_declaration',
                    'legal_opinion',
                    'corporate_data_sheet',
                    'registry_extract',
                    'corporate_index_or_data_sheet',
                    'director_officer_appointment_or_resignation',
                    'engagement_letter',
                    'engagement_letter_or_legal_advice',
                    'kyc_document',
                    'management_representation_letter',
                    'correspondence',
                    'other',
                ),
            multiple=True,
        ),
        Parameter(
            name='signatory_person_id',
            label='Signed by',
            description='Show only documents signed by this person.',
            default=None,
            placeholder='Search for a person (optional)…',
        ),
        Parameter(
            name='subject_id',
            label='Business subject',
            description='Show only documents about this business subject.',
            default=None,
            placeholder='Search for a business subject (optional)…',
        ),
        Parameter(
            name='file',
            label='Filename',
            description=
                        (
                            'Pin to a single document — useful when you have the file in hand and '
                            'want its title, summary, doc type, and document date.'
                        ),
            default=None,
            placeholder='Search for a document (optional)…',
        ),
        Parameter(
            name='text_query',
            label='Keyword',
            description='Find documents whose title, summary, or type contains this text.',
            default='',
            placeholder='e.g. capital injection',
        ),
        Parameter(
            name='limit',
            label='Maximum results',
            kind='number',
            description='How many results to show at most.',
            default=100,
        ),
    ),
    output_columns=
        (
            'work_id',
            'expression_id',
            'item_id',
            'title',
            'doc_type',
            'effective_date',
            'work_lifecycle_status',
            'expression_lifecycle_status',
            'item_lifecycle_status',
            'summary',
            'sources',
        ),
    notes='With no filters set, the workflow returns every document up to the configured limit.',
    use_cases=
        (
            'Which documents were signed by a given person?',
            'Show every share certificate issued by this business subject.',
            'Find a specific share-purchase agreement by keyword.',
            'Which documents record a particular decision or event?',
        ),
)

CAPITAL_SHAREHOLDINGS = Workflow(
    workflow_id='capital.shareholdings',
    title='Capital and shareholdings',
    category='General',
    description=
                (
                    'Shows the capital story as a sequence of corporate acts, not as a pile of '
                    'extracted amounts. Each row is something a document says happened: a share '
                    'transfer, share issue, allotment, capital increase, contribution, or similar '
                    'capital event. The table shows who acted, who was affected, the date, amount '
                    'where the document states one, and the source documents ranked by authority. '
                    'Use the date filters to read a chosen period.'
                ),
    cypher=repository.CAPITAL_EVENTS,
    parameters=(
        Parameter(
            name='subject_id',
            label='Business subject',
            description='Type to search and pick a business subject.',
            default=None,
            placeholder='Search for a business subject…',
        ),
        Parameter(
            name='organization_id',
            label='Organization',
            description=
                        (
                            'Pick one organization to narrow the capital view to a single '
                            'company. Leave blank to span every organization under the selected '
                            'business subject.'
                        ),
            default='',
            placeholder='Search for an organization (optional)…',
        ),
        Parameter(
            name='since',
            label='From date',
            kind='date',
            description='Show only entries on or after this date.',
            default=None,
        ),
        Parameter(
            name='until',
            label='To date',
            kind='date',
            description='Show only entries on or before this date.',
            default=None,
        ),
        Parameter(
            name='limit',
            label='Maximum results',
            kind='number',
            description='How many results to show at most.',
            default=50,
        ),
        Parameter(
            name='include_cancelled',
            label='Show inactive',
            kind='boolean',
            description=
                        (
                            'Also show items that are no longer in force — cancelled, revoked, '
                            'expired, or superseded. Off by default so only what is currently '
                            'true is shown.'
                        ),
            default=False,
        ),
    ),
    output_columns=
        (
            'subject',
            'effective_date',
            'event',
            'event_type',
            'acting_parties',
            'affected_parties',
            'counterparties',
            'amount',
            'currency',
            'monetary_amount_id',
            'primary_document_type',
            'authority_status',
            'source_documents',
            'sources',
            'event_id',
        ),
    notes=
          (
              'With no ``subject_id``, ``organization_id``, or date filters, returns capital '
              'events and shareholdings corpus-wide, newest first, up to ``limit``.'
          ),
    use_cases=
        (
            'Show the capital events for this business subject.',
            'Which documents support capital contributions or share transfers?',
            'What happened to shares and capital in a chosen period?',
        ),
)

GOVERNANCE_POA_REGISTER = Workflow(
    workflow_id='governance.poa.register',
    title='Powers of attorney',
    category='General',
    description=
                (
                    'All powers of attorney — who was given authority, by whom, for what, how '
                    'they had to sign, the dates the power was in force, and the supporting '
                    'documents. Every filter is optional: narrow by business subject, person, or '
                    'organization, or combine them.'
                ),
    cypher=repository.POA_REGISTER,
    parameters=(
        Parameter(
            name='subject_id',
            label='Business subject',
            description=
                        (
                            'Show only powers of attorney touching this business subject. Leave '
                            'blank to search across every business subject.'
                        ),
            default=None,
            placeholder='Search for a business subject (optional)…',
        ),
        Parameter(
            name='involves_organization_id',
            label='Organization',
            description=
                        (
                            'Show only powers of attorney that involve this organization — '
                            'whether as the party receiving the authority, granting it, or being '
                            'represented.'
                        ),
            default=None,
            placeholder='Search for an organization (optional)…',
        ),
        Parameter(
            name='involves_person_id',
            label='Person',
            description='Show only powers of attorney that give authority to this person.',
            default=None,
            placeholder='Search for a person (optional)…',
        ),
        Parameter(
            name='include_cancelled',
            label='Show inactive',
            kind='boolean',
            description=
                        (
                            'Also show items that are no longer in force — cancelled, revoked, '
                            'expired, or superseded. Off by default so only what is currently '
                            'true is shown.'
                        ),
            default=False,
        ),
    ),
    output_columns=
        (
            'subject',
            'phase_id',
            'phase',
            'phase_valid_from',
            'phase_valid_to',
            'poa_id',
            'poa_label',
            'scope',
            'signature_mode',
            'valid_from',
            'valid_to',
            'valid_to_event_id',
            'lifecycle_status',
            'revocation_terms',
            'grounding_quote',
            'grantee_persons',
            'firm_grantees',
            'authorizing_parties',
            'concerned_organizations',
            'supporting_titles',
            'sources',
        ),
    use_cases=
        (
            'Which powers of attorney are currently in force for this business subject?',
            'What signing authority did this business subject grant over its history?',
            'Show every POA touching a specific subsidiary.',
            'Show every POA granted to a specific advocate or officer.',
        ),
)

EVENTS_TIMELINE = Workflow(
    workflow_id='events.timeline',
    title='Event timeline',
    category='General',
    description=
                (
                    'Chronology of corporate events. Every filter is optional — with nothing set, '
                    'you get every event (capped by the maximum). Narrow by business subject, by '
                    'who participated, by a specific event type, by a keyword in the event name, '
                    'or by a date range. Each row shows who acted, who was affected, the '
                    'counterparties, any amount, and the supporting documents.'
                ),
    cypher=repository.EVENTS_TIMELINE,
    parameters=(
        Parameter(
            name='event_type',
            label='Event type',
            kind='select',
            description='Narrow to a single type of event.',
            default='',
            options=
                (
                    '',
                    'incorporation',
                    'constitutional-adoption',
                    'articles-amendment',
                    'continuation-in',
                    'continuation-out',
                    'redomiciliation',
                    'legal-form-conversion',
                    'dissolution',
                    'liquidation-start',
                    'liquidation-end',
                    'striking-off',
                    'board-meeting',
                    'board-resolution',
                    'shareholder-meeting',
                    'shareholder-resolution',
                    'director-appointment',
                    'director-resignation',
                    'officer-appointment',
                    'officer-resignation',
                    'auditor-appointment',
                    'share-issuance',
                    'share-allotment',
                    'share-transfer',
                    'share-cancellation',
                    'capital-increase',
                    'capital-reduction',
                    'capital-contribution-cash',
                    'capital-contribution-in-kind',
                    'dividend-declaration',
                    'dividend-payment',
                    'power-of-attorney-grant',
                    'power-of-attorney-revocation',
                    'proxy-grant',
                    'loan-agreement',
                    'loan-repayment',
                    'loan-forgiveness',
                    'merger',
                    'demerger',
                    'asset-transfer',
                    'intercompany-agreement',
                    'tax-ruling-request',
                    'tax-ruling-grant',
                    'tax-residence-attestation',
                    'annual-report-filing',
                    'annual-report-approval',
                    'notarial-certification',
                    'apostille',
                    'cancellation',
                    'recall-of-decision',
                    'unclassified',
                ),
            multiple=True,
        ),
        Parameter(
            name='event_domain',
            label='Event domain',
            kind='select',
            description=
                        (
                            'Optional event domain group. Selecting a domain returns events whose '
                            'canonical eventType belongs to that group.'
                        ),
            default='',
            options=
                (
                    '',
                    'corporate_lifecycle',
                    'constitutional_governance',
                    'officers_and_roles',
                    'capital_and_shares',
                    'distributions',
                    'authority_and_representation',
                    'finance_and_treasury',
                    'reorganization_and_transactions',
                    'tax_and_regulatory',
                    'formalities',
                    'meta_quality',
                ),
            multiple=True,
        ),
        Parameter(
            name='subject_id',
            label='Business subject',
            description=
                        (
                            'Show only events touching this business subject. Leave blank to '
                            'search across every business subject.'
                        ),
            default=None,
            placeholder='Search for a business subject (optional)…',
        ),
        Parameter(
            name='participant_id',
            label='Who participated',
            description=
                        (
                            'Show only events where this legal entity appears either as the actor '
                            'or as the affected party.'
                        ),
            default=None,
            placeholder='Search for an organization (optional)…',
        ),
        Parameter(
            name='file',
            label='In document',
            description=
                        (
                            'Show only events that are mentioned, recorded, or evidenced in this '
                            'document.'
                        ),
            default=None,
            placeholder='Search for a document (optional)…',
        ),
        Parameter(
            name='q',
            label='Keyword',
            description='Find events whose name or type contains this text.',
            default='',
            placeholder='e.g. dividend, appointment',
        ),
        Parameter(
            name='since',
            label='From date',
            kind='date',
            description='Show only entries on or after this date.',
            default=None,
        ),
        Parameter(
            name='until',
            label='To date',
            kind='date',
            description='Show only entries on or before this date.',
            default=None,
        ),
        Parameter(
            name='limit',
            label='Maximum results',
            kind='number',
            description='How many results to show at most.',
            default=200,
        ),
        Parameter(
            name='include_cancelled',
            label='Show inactive',
            kind='boolean',
            description=
                        (
                            'Also show items that are no longer in force — cancelled, revoked, '
                            'expired, or superseded. Off by default so only what is currently '
                            'true is shown.'
                        ),
            default=False,
        ),
    ),
    output_columns=
        (
            'actors',
            'undergoers',
            'event',
            'event_type',
            'event_domain',
            'effective_date',
            'primary_document_type',
            'authority_status',
            'counterparties',
            'amount',
            'currency',
            'sources',
            'supporting_titles',
            'subject',
            'event_id',
        ),
    use_cases=
        (
            'What corporate actions happened in a given period?',
            "Show every event of a specific type in this business subject's history.",
            'List all events involving a specific subsidiary or counterparty.',
            'Find every event where a given organization participated.',
        ),
)

DATA_MODEL_GUIDE = Workflow(
    workflow_id='data_model.guide',
    title='Data model',
    category='Data model',
    description=
                (
                    'Documentation-style guide to the main entities, relationships, event types, '
                    'document types, and identifier types used across the console.'
                ),
    cypher=repository.DATA_MODEL_GUIDE,
    output_columns=
        (
            'section',
        ),
    use_cases=
        (
            'Understand the main entities and relationships in the graph.',
            'See which document and event types exist in the corpus model.',
            'Read a plain-language guide instead of raw schema tables.',
        ),
)

DATA_MODEL_DEV_WORKFLOWS = Workflow(
    workflow_id='data_model.dev_workflows',
    title='Dev workflows',
    category='Data model',
    description=
                (
                    'Admin-only graph mutation workflows for deleting relationships, deleting '
                    'isolated nodes, and merging one node into another.'
                ),
    cypher=repository.DATA_MODEL_CLASSES,
    output_columns=
        (
            'section',
        ),
    use_cases=
        (
            'Delete one relationship by edge id.',
            'Delete one isolated node by entity id.',
            'Merge one node into another and move its relationships.',
        ),
    dev_only=True,
)

CATALOG: tuple[Workflow, ...] = (
    FIND_SUBJECT,
    FIND_ORGANIZATION,
    FIND_PERSON,
    DOCUMENTS_SEARCH,
    CAPITAL_SHAREHOLDINGS,
    GOVERNANCE_POA_REGISTER,
    EVENTS_TIMELINE,
    DATA_MODEL_GUIDE,
    DATA_MODEL_DEV_WORKFLOWS,
)

_INDEX: dict[str, Workflow] = {workflow.workflow_id: workflow for workflow in CATALOG}


def by_id(workflow_id: str) -> Workflow:
    if workflow_id not in _INDEX:
        raise KeyError(f"Unknown workflow_id: {workflow_id!r}")
    return _INDEX[workflow_id]


def categories() -> list[str]:
    result: list[str] = []
    for workflow in CATALOG:
        if workflow.category not in result:
            result.append(workflow.category)
    return result
