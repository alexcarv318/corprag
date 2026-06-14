export const dataModelGuideContent = {
  entities: [
    {
      title: "Business subject",
      description:
        "A business subject is the family-level identity that persists across changes in jurisdiction, legal form, or corporate phase. It is the historical thread that ties several legal entities into one business story.",
      notes: [
        "The main anchor for `find.subject`, `capital.shareholdings`, `governance.poa.register`, and subject-scoped timeline queries.",
        "Useful when the same business moved between entities such as a Cyprus company, a Curaçao company, and a Swiss company over time."
      ]
    },
    {
      title: "Legal entity",
      description:
        "A legal entity is a concrete company or legal body. It carries jurisdiction, legal form, registration numbers, governing law, and registered office. A legal entity can be one phase inside a broader business-subject history or a standalone organization in the corpus.",
      notes: [
        "Most often appears as an actor, undergoer, counterparty, authorizing party, or concerned organization.",
        "The most visible organization-facing workflow is `find.organization`."
      ]
    },
    {
      title: "Person",
      description:
        "A person is a natural person who appears in governance, signatures, appointments, elections, authority grants, or supporting documents. Person views combine identity, roles, and evidence rather than splitting those into separate paths.",
      notes: [
        "Can surface through board roles, employment affiliation, signing authority, document signatures, and event participation.",
        "Often linked to governance and authority facts that are then explained through source documents."
      ]
    },
    {
      title: "Event",
      description:
        "An event is a corporate act, decision, filing, or status change described by a canonical event type. Events are the center of the most reliable historical views because they connect action, participants, timing, amounts, and authority into one factual unit.",
      notes: [
        "Event-driven logic powers the timeline, capital workflow, and board-history projections.",
        "Events are grouped into domains such as corporate lifecycle, governance, authority, capital, finance, and tax."
      ]
    },
    {
      title: "Document",
      description:
        "A document is the textual or formal source that records, mentions, evidences, or supports a fact. Document types are controlled so the console can rank authority consistently and explain why one source counts as primary while another counts only as context.",
      notes: [
        "A single document can support multiple events, identifiers, signatures, and authority statements.",
        "Some documents record an act directly; others only mention it or attest to it after the fact."
      ]
    },
    {
      title: "Power of attorney",
      description:
        "A power of attorney is a formal grant of authority modeled as its own entity. It separates the grantor, the grantee, the represented or concerned organization, the effective period, and the signature mode.",
      notes: [
        "Supports grants to people and to organizations.",
        "Carries lifecycle states such as active, revoked, cancelled, and spent."
      ]
    },
    {
      title: "Board membership",
      description:
        "A board membership is a governance role held by a person in relation to a controlled party. It is not only a text mention of a title; it is the structured role record used to project board history and person affiliation history.",
      notes: [
        "Separates the role-holder from the organization being governed.",
        "Best interpreted together with appointment-grade event evidence."
      ]
    },
    {
      title: "Shareholding, identifier, and amount",
      description:
        "Shareholdings, identifiers, and monetary amounts are supporting fact types that let the graph express ownership, registration identity, and stated value. They rarely stand alone in the product; instead they enrich the capital, subject, organization, and event surfaces.",
      notes: [
        "Identifiers explain official numbers and schemes across jurisdictions.",
        "Amounts explain capital values, stated figures, and transaction-linked monetary facts."
      ]
    }
  ],
  relationships: [
    ["HAS_ACTOR", "Links an event to the party that performed or initiated the act. In practice this is often a company, shareholder, director, officer, or signatory acting in a formal capacity."],
    ["HAS_UNDERGOER", "Links an event to the party or thing that the act happened to. The undergoer is the affected side of the event: the company being appointed into, the entity receiving capital, or the party being changed."],
    ["HAS_COUNTERPARTY", "Links an event to the other side of the act. A counterparty is not the primary actor and not the main affected side, but the additional participant necessary to understand the transaction or authority structure."],
    ["HAS_EFFECTIVE_DATE", "Links an event or authority fact to the date on which it takes effect. This is what makes timeline ordering, phase filtering, and point-in-time questions coherent."],
    ["HAS_NOTIONAL_AMOUNT", "Links an event to a stated monetary amount. It is used when the act explicitly carries a value such as a contribution amount, transfer amount, or capital figure."],
    ["IS_CONFERRED_ON", "Links a power of attorney to the natural person who receives authority under it."],
    ["HAS_AUTHORIZING_PARTY", "Links a power of attorney to the legal entity that grants the authority."],
    ["HAS_CONFERRED_ON_ORGANIZATION", "Links a power of attorney to an organization that receives delegated authority rather than a single individual."],
    ["CONCERNS_ORGANIZATION", "Links a power of attorney to the organization whose affairs or representation the authority concerns."],
    ["HAS_PARTY_IN_CONTROL", "Links a board or control structure to the person who holds the governing role."],
    ["INVOLVES_CONTROLLED_THING", "Links a board or control structure to the organization or controlled party that the role applies to."]
  ],
  eventDomains: [
    ["corporate_lifecycle", "Events about formation, continuation, redomiciliation, conversion, dissolution, liquidation, and the legal life of the entity itself."],
    ["constitutional_governance", "Events about articles, meetings, resolutions, and formal governance acts that set or amend how the entity is governed."],
    ["officers_and_roles", "Events about appointments, resignations, and role changes for directors, officers, auditors, and similar office-holders."],
    ["capital_and_shares", "Events about share issuance, allotment, transfer, cancellation, capital increase, capital reduction, and contribution into capital."],
    ["distributions", "Events about dividends and other value distributions to owners or relevant parties."],
    ["authority_and_representation", "Events about powers of attorney, proxies, delegated representation, and similar authority-conferring acts."],
    ["finance_and_treasury", "Events about loans, repayments, forgiveness, and treasury-style financial flows."],
    ["reorganization_and_transactions", "Events about mergers, demergers, asset transfers, and transaction structures that reshape the corporate perimeter."],
    ["tax_and_regulatory", "Events about tax rulings, tax status, regulatory requests, and other compliance-facing determinations."],
    ["formalities", "Events about certification, notarisation, apostille, and similar procedural acts that formalise another underlying fact."],
    ["meta_quality", "Events about cancellation, recall, or other quality-control actions taken against earlier extracted or recorded facts."]
  ],
  eventTypeGroups: [
    ["Corporate lifecycle", [
      ["incorporation", "The formal creation of the entity as a legal body."],
      ["constitutional-adoption", "The adoption of foundational constitutional documents at formation or reconstitution."],
      ["continuation-in", "The inward continuation of an entity into the current jurisdiction or legal regime."],
      ["continuation-out", "The outward continuation of an entity into another jurisdiction or legal regime."],
      ["redomiciliation", "A change of legal home from one jurisdiction to another."],
      ["legal-form-conversion", "A conversion from one legal form to another without treating the business as a wholly new history."],
      ["dissolution", "The formal dissolution of the entity as a legal body."],
      ["liquidation-start", "The start of a liquidation process."],
      ["liquidation-end", "The completion or closure of a liquidation process."],
      ["striking-off", "Administrative removal of the entity from a register or official standing."]
    ]],
    ["Governance and constitutional acts", [
      ["articles-amendment", "An amendment to constitutional or articles-level governance text."],
      ["board-meeting", "A board meeting as a dated governance event."],
      ["board-resolution", "A decision formally taken by the board."],
      ["shareholder-meeting", "A shareholder meeting as a dated governance event."],
      ["shareholder-resolution", "A decision formally taken by shareholders."],
      ["annual-report-filing", "The filing of an annual report or equivalent reporting package."],
      ["annual-report-approval", "The approval of annual accounts or annual reporting materials."]
    ]],
    ["Officers and roles", [
      ["director-appointment", "The appointment of a director or equivalent board member."],
      ["director-resignation", "The resignation or removal of a director or equivalent board member."],
      ["officer-appointment", "The appointment of an officer or executive role-holder."],
      ["officer-resignation", "The resignation or removal of an officer or executive role-holder."],
      ["auditor-appointment", "The appointment of an auditor or similar control function."]
    ]],
    ["Capital and shares", [
      ["share-issuance", "The issue of shares into existence or into the holder structure."],
      ["share-allotment", "The allotment of shares to a particular holder or allocation structure."],
      ["share-transfer", "The transfer of shares from one holder to another."],
      ["share-cancellation", "The cancellation or extinguishing of shares."],
      ["capital-increase", "A formal increase in share capital or equivalent capital figure."],
      ["capital-reduction", "A formal reduction in share capital or equivalent capital figure."],
      ["capital-contribution-cash", "A capital contribution made in cash."],
      ["capital-contribution-in-kind", "A capital contribution made in kind rather than in cash."]
    ]],
    ["Distributions and authority", [
      ["dividend-declaration", "A formal declaration that a dividend will be distributed."],
      ["dividend-payment", "The payment or execution of a declared dividend."],
      ["power-of-attorney-grant", "The grant of authority under a power of attorney."],
      ["power-of-attorney-revocation", "The revocation or withdrawal of a power of attorney."],
      ["proxy-grant", "The grant of proxy authority for representation or voting."]
    ]],
    ["Finance and transactions", [
      ["loan-agreement", "The creation or documentation of a loan relationship."],
      ["loan-repayment", "The repayment of principal or another loan obligation."],
      ["loan-forgiveness", "The forgiveness, waiver, or write-off of loan obligations."],
      ["merger", "A merger of corporate bodies or business structures."],
      ["demerger", "A demerger or split of corporate structures."],
      ["asset-transfer", "A transfer of assets between parties or structures."],
      ["intercompany-agreement", "A formal agreement within a group or affiliated-party structure."]
    ]],
    ["Tax, formalities, and quality", [
      ["tax-ruling-request", "A request for a tax ruling or similar tax determination."],
      ["tax-ruling-grant", "The grant or issuance of a tax ruling."],
      ["tax-residence-attestation", "An attestation of tax residence or tax status."],
      ["notarial-certification", "A notarial act that certifies or formalises another fact."],
      ["apostille", "An apostille or equivalent cross-border formalisation step."],
      ["cancellation", "The cancellation of an earlier decision, fact, or status."],
      ["recall-of-decision", "A recall or withdrawal of a previously taken decision."],
      ["unclassified", "An event that is known to exist but is not yet assigned to a more specific canonical type."]
    ]]
  ],
  documentTypeGroups: [
    ["Constitutional and registry records", [
      ["incorporation_certificate", "A certificate evidencing incorporation or formation."],
      ["articles_of_association_or_bylaws", "The constitutional rules that govern the entity internally."],
      ["continuation_certificate", "A certificate evidencing continuation into a jurisdiction or regime."],
      ["discontinuance_certificate", "A certificate evidencing discontinuance from a jurisdiction or regime."],
      ["dissolution_certificate", "A certificate evidencing dissolution or formal termination."],
      ["registry_extract_certificate", "A certified extract issued from an official registry."],
      ["registry_filing", "A filing lodged with a corporate or official registry."],
      ["registry_extract", "A registry extract that states official register information without necessarily being the constitutive act."],
      ["redomiciliation_application", "An application seeking redomiciliation or continuation."],
      ["corporate_data_sheet", "A corporate profile or summary sheet that states basic company facts."],
      ["corporate_index_or_data_sheet", "An index-like corporate summary or register-style information sheet."]
    ]],
    ["Governance records", [
      ["administrative_certificate", "An administrative certificate that confirms a status or formal fact."],
      ["good_standing_certificate", "A certificate confirming good standing or equivalent official status."],
      ["board_resolution", "A written board resolution."],
      ["board_meeting_minutes", "Minutes of a board meeting."],
      ["shareholder_resolution", "A written shareholder resolution."],
      ["shareholder_meeting_minutes", "Minutes of a shareholder meeting."],
      ["director_appointment", "A document whose primary legal function is a director appointment."],
      ["director_resignation", "A document whose primary legal function is a director resignation."],
      ["director_resolution", "A resolution concerning a director-level governance act."],
      ["director_officer_appointment_or_resignation", "A mixed or legacy governance document covering appointment or resignation of directors or officers."]
    ]],
    ["Capital and transaction records", [
      ["share_certificate", "A certificate evidencing ownership of shares."],
      ["share_register", "A register of share ownership and holder changes."],
      ["share_transfer_agreement", "An agreement transferring shares from one holder to another."],
      ["share_contribution_agreement", "An agreement contributing shares or capital into a structure."],
      ["receivables_purchase_agreement", "An agreement purchasing receivables or similar claims."],
      ["reorganization_resolution", "A resolution approving a reorganisation act."],
      ["reorganization_deed", "A deed formalising a reorganisation or restructuring act."],
      ["intercompany_or_other_agreement", "A broader agreement between affiliated or otherwise related parties."],
      ["banking_payment_or_credit_record", "A banking or payment record that evidences transfer of funds or credit."]
    ]],
    ["Authority and support documents", [
      ["power_of_attorney", "A formal power of attorney document."],
      ["proxy", "A proxy document conferring representation or voting authority."],
      ["engagement_letter", "A letter formally engaging a professional adviser or service provider."],
      ["engagement_letter_or_legal_advice", "A mixed document that functions as both engagement letter and legal advice."],
      ["management_representation_letter", "A management letter formally representing facts, positions, or assurances."],
      ["correspondence", "General correspondence that may support context, timing, or attribution but is not usually the core constitutive act."]
    ]],
    ["Tax, compliance, and supporting legal material", [
      ["annual_accounts_financial_statements", "Annual accounts or financial statements."],
      ["tax_document", "A tax-facing document such as a filing, form, statement, or official tax record."],
      ["regulatory_filing", "A filing made to a regulator rather than to a company register."],
      ["legal_declaration", "A formal legal declaration or statement."],
      ["legal_opinion", "A legal opinion explaining legal status, structure, or effect."],
      ["kyc_document", "Know-your-customer material or identity/compliance support."],
      ["other", "A document that is relevant to the corpus but not yet mapped to a narrower canonical type."]
    ]]
  ],
  identifierTypes: [
    ["RegistrationIdentifier", "An official company or registration number assigned by a registry or comparable authority."],
    ["TaxIdentifier", "A number used for tax administration or tax-facing registration."],
    ["BankAccountIdentifier", "A bank-account style identifier such as an account number or similar banking reference."],
    ["CertificateIdentifier", "An identifier attached to a certificate, often in share or registry contexts."],
    ["RegulatoryFilingIdentifier", "A filing number or reference used by a regulator or filing process."],
    ["DocumentReferenceIdentifier", "A reference number that points to a document, protocol, or filing artifact."]
  ]
};
