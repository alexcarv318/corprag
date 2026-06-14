import { useCallback, useEffect, useState } from "react";

import { dataModelGuideContent } from "./dataModelGuideContent.js";

function guideSlug(value) {
  return String(value).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function scrollToAnchor(targetId) {
  const target = document.getElementById(targetId);
  if (!target) return false;
  history.replaceState(null, "", `#${targetId}`);
  target.scrollIntoView({ block: "start", behavior: "smooth" });
  return true;
}

function tocItemsFor(section) {
  if (section.key === "entities") {
    return dataModelGuideContent.entities.map((entry) => [`entity-${guideSlug(entry.title)}`, entry.title]);
  }
  if (section.key === "eventTypeGroups") {
    return dataModelGuideContent.eventTypeGroups.map(([title]) => [`event-type-group-${guideSlug(title)}`, title]);
  }
  if (section.key === "documentTypeGroups") {
    return dataModelGuideContent.documentTypeGroups.map(([title]) => [`document-type-group-${guideSlug(title)}`, title]);
  }
  return dataModelGuideContent[section.key].map(([term]) => [`${section.itemPrefix}${guideSlug(term)}`, term]);
}

const tocSections = [
  { title: "Core entities", targetId: "entities", key: "entities", open: true },
  { title: "Core relationships", targetId: "relationships", key: "relationships", itemPrefix: "relationship-" },
  { title: "Event domains", targetId: "event-domains", key: "eventDomains", itemPrefix: "event-domain-" },
  { title: "Event types", targetId: "event-types", key: "eventTypeGroups" },
  { title: "Document types", targetId: "document-types", key: "documentTypeGroups" },
  { title: "Identifier types", targetId: "identifier-types", key: "identifierTypes", itemPrefix: "identifier-type-" }
];

function GuideTocGroup({ activeId, section, onNavigate }) {
  return (
    <details open={section.open ? true : undefined}>
      <summary>
        <a href={`#${section.targetId}`} onClick={(event) => onNavigate(event, section.targetId)}>
          {section.title}
        </a>
      </summary>
      <ul>
        {tocItemsFor(section).map(([itemId, label]) => (
          <li key={itemId}>
            <a
              className={activeId === itemId ? "guide-anchor-highlight" : ""}
              href={`#${itemId}`}
              onClick={(event) => onNavigate(event, itemId)}
            >
              {label}
            </a>
          </li>
        ))}
      </ul>
    </details>
  );
}

function GuideDefinitions({ activeId, idPrefix = "", items }) {
  return (
    <dl className="guide-definitions">
      {items.map(([term, description]) => {
        const id = idPrefix ? `${idPrefix}${guideSlug(term)}` : undefined;
        return (
          <div className={`guide-definition-row${activeId === id ? " guide-anchor-highlight" : ""}`} id={id} key={term}>
            <dt>{term}</dt>
            <dd>{description}</dd>
          </div>
        );
      })}
    </dl>
  );
}

function GuideSection({ activeId, children, id, title }) {
  return (
    <section className={activeId === id ? "guide-anchor-highlight" : ""} id={id}>
      <h2>{title}</h2>
      {children}
    </section>
  );
}

function EntityGroup({ activeId, entry }) {
  const id = `entity-${guideSlug(entry.title)}`;
  return (
    <article className={`guide-group${activeId === id ? " guide-anchor-highlight" : ""}`} id={id}>
      <h3>{entry.title}</h3>
      <p>{entry.description}</p>
      <ul>
        {entry.notes.map((note) => <li key={note}>{note}</li>)}
      </ul>
    </article>
  );
}

function GroupedDefinitions({ activeId, groups, idPrefix }) {
  return groups.map(([groupTitle, items]) => {
    const id = `${idPrefix}${guideSlug(groupTitle)}`;
    return (
      <article className={`guide-group${activeId === id ? " guide-anchor-highlight" : ""}`} id={id} key={groupTitle}>
        <h3>{groupTitle}</h3>
        <GuideDefinitions activeId={activeId} items={items} />
      </article>
    );
  });
}

export function DataModelGuide({ workflow }) {
  const [activeId, setActiveId] = useState("");
  const navigate = useCallback((event, targetId) => {
    event.preventDefault();
    event.stopPropagation();
    if (scrollToAnchor(targetId)) setActiveId(targetId);
  }, []);

  useEffect(() => {
    const hashTarget = decodeURIComponent(window.location.hash.replace(/^#/, ""));
    if (!hashTarget) return;
    const frame = window.requestAnimationFrame(() => {
      if (scrollToAnchor(hashTarget)) setActiveId(hashTarget);
    });
    return () => window.cancelAnimationFrame(frame);
  }, []);

  return (
    <section className="guide-layout">
      <div className="guide-stage">
        <nav className="guide-toc" aria-label="Data model contents">
          <h2>{workflow.title}</h2>
          <p>This page intentionally avoids raw schema inspection views.</p>
          <div className="guide-toc-sections">
            {tocSections.map((section) => (
              <GuideTocGroup activeId={activeId} key={section.targetId} section={section} onNavigate={navigate} />
            ))}
          </div>
        </nav>

        <main className="guide-document">
          <GuideSection activeId={activeId} id="entities" title="Core entities">
            {dataModelGuideContent.entities.map((entry) => (
              <EntityGroup activeId={activeId} entry={entry} key={entry.title} />
            ))}
          </GuideSection>

          <GuideSection activeId={activeId} id="relationships" title="Core relationships">
            <p className="guide-muted">
              These are the relation names most worth documenting directly because they shape the timeline, authority, governance, and capital views.
            </p>
            <GuideDefinitions activeId={activeId} idPrefix="relationship-" items={dataModelGuideContent.relationships} />
          </GuideSection>

          <GuideSection activeId={activeId} id="event-domains" title="Event domains">
            <p>
              Event domains are the first level of organisation for the event vocabulary. They help the user move from a broad business question to a narrower class of corporate acts.
            </p>
            <GuideDefinitions activeId={activeId} idPrefix="event-domain-" items={dataModelGuideContent.eventDomains} />
          </GuideSection>

          <GuideSection activeId={activeId} id="event-types" title="Event types">
            <p>
              Each canonical event type names a recurring kind of corporate act. The definitions below are written as index entries rather than as raw schema slugs.
            </p>
            <GroupedDefinitions activeId={activeId} groups={dataModelGuideContent.eventTypeGroups} idPrefix="event-type-group-" />
          </GuideSection>

          <GuideSection activeId={activeId} id="document-types" title="Document types">
            <p>
              Document types describe what sort of source a file is, not merely where it was found. These distinctions are central to evidence ranking and to the user's sense of what counts as constitutive, supportive, or contextual authority.
            </p>
            <GroupedDefinitions activeId={activeId} groups={dataModelGuideContent.documentTypeGroups} idPrefix="document-type-group-" />
          </GuideSection>

          <GuideSection activeId={activeId} id="identifier-types" title="Identifier types">
            <p>
              Identifier kinds are narrower than document types and event types. They explain which official number or reference a row is carrying.
            </p>
            <GuideDefinitions activeId={activeId} idPrefix="identifier-type-" items={dataModelGuideContent.identifierTypes} />
          </GuideSection>
        </main>
      </div>
    </section>
  );
}
