(() => {
  "use strict";

  const SCHEMA_VERSION = 3;
  const TAGS = new Set([
    "a", "article", "aside", "br", "caption", "code", "dd", "details", "div",
    "dl", "dt", "em", "fieldset", "figcaption", "figure", "footer", "h1", "h2",
    "h3", "h4", "h5", "h6", "header", "hr", "img", "label", "legend", "li",
    "main", "nav", "ol", "p", "section", "small", "span", "strong", "summary",
    "time", "ul"
  ]);
  const ATTRS = new Set([
    "alt", "class", "datetime", "dir", "height", "href", "id", "lang",
    "decoding", "loading", "rel", "role", "src", "tabindex", "target", "title", "width"
  ]);

  function scriptNode() {
    return document.currentScript ||
      Array.from(document.scripts).find((node) =>
        node.src.includes("darktide-dialogue.js")
      );
  }

  function safeUrl(value) {
    if (typeof value !== "string" || !value) return null;
    const text = value.trim();
    if (/^(javascript|data|vbscript):/i.test(text)) return null;
    try {
      const url = new URL(text, document.baseURI);
      if (url.protocol === "https:") return text;
      if ((url.protocol === "http:" || url.protocol === "file:") &&
          url.origin === window.location.origin) return text;
      return null;
    } catch {
      return null;
    }
  }

  function setAttributes(element, attrs, anchors, seen, replacing) {
    if (!attrs || typeof attrs !== "object" || Array.isArray(attrs)) return;
    for (const [rawKey, rawValue] of Object.entries(attrs)) {
      const key = String(rawKey).toLowerCase();
      if (!/^[a-z][a-z0-9_.:-]*$/.test(key) || key.startsWith("on") || key === "style") continue;
      if (!(ATTRS.has(key) || key.startsWith("aria-") || key.startsWith("data-"))) continue;
      if (rawValue === null || typeof rawValue === "undefined") {
        if (key === "alt") element.setAttribute(key, "");
        continue;
      }
      let value = String(rawValue);
      if ((key === "href" || key === "src") && !value.startsWith("#")) {
        value = safeUrl(value);
        if (value === null) continue;
      }
      if (key === "id") {
        if (!/^[A-Za-z][A-Za-z0-9_.:-]*$/.test(value) || seen.has(value)) continue;
        const placeholder = anchors.get(value);
        const existing = document.getElementById(value);
        const isReplacing = Boolean(existing && replacing &&
          Array.from(replacing).some((section) =>
            section === existing || section.contains(existing),
          ));
        if (existing && existing !== placeholder && !isReplacing) continue;
        seen.add(value);
      }
      element.setAttribute(key, value);
    }
  }

  function makeNode(record, anchors, seen, data, replacing) {
    if (typeof record === "string" || isCompactString(record)) {
      return document.createTextNode(compactString(record, data));
    }
    if (!Array.isArray(record) || record.length !== 3 ||
        !Number.isInteger(record[0]) || !Array.isArray(record[1]) ||
        !Array.isArray(record[2])) {
      throw new Error("Dialogue transcript node is invalid");
    }
    const tag = transcriptTag(record, data).toLowerCase();
    const attrs = transcriptAttributes(record, data);
    const children = record[2];
    if (!TAGS.has(tag)) {
      const fragment = document.createDocumentFragment();
      for (const child of children) fragment.append(makeNode(child, anchors, seen, data, replacing));
      return fragment;
    }
    const element = document.createElement(tag);
    setAttributes(element, attrs, anchors, seen, replacing);
    for (const child of children) element.append(makeNode(child, anchors, seen, data, replacing));
    return element;
  }

  function makeSourceNode(record, anchors, seen, replacing) {
    if (!record || typeof record !== "object" || Array.isArray(record)) {
      throw new Error("Dialogue participant markup is invalid");
    }
    if (record.type === "text") {
      if (typeof record.value !== "string") {
        throw new Error("Dialogue participant text is invalid");
      }
      return document.createTextNode(record.value);
    }
    if (record.type !== "element" || typeof record.tag !== "string" ||
        !Array.isArray(record.children)) {
      throw new Error("Dialogue participant element is invalid");
    }
    const tag = record.tag.toLowerCase();
    const fragment = document.createDocumentFragment();
    if (!TAGS.has(tag)) {
      for (const child of record.children) {
        fragment.append(makeSourceNode(child, anchors, seen, replacing));
      }
      return fragment;
    }
    const element = document.createElement(tag);
    setAttributes(element, record.attrs, anchors, seen, replacing);
    for (const child of record.children) {
      element.append(makeSourceNode(child, anchors, seen, replacing));
    }
    return element;
  }

  function normalizePath(path) {
    const value = new URL(path, window.location.href).pathname;
    return value.endsWith("/index.html") ? value.slice(0, -"index.html".length) : value;
  }

  function localized(locale, english, chinese) {
    return locale === "zh-tw" ? chinese : english;
  }

  function decodeMetadata(data) {
    const wire = data && data.wire;
    if (!wire || wire.version !== 2 || !Array.isArray(wire.fields) ||
        !Array.isArray(wire.strings) || !Array.isArray(wire.tags) ||
        !Array.isArray(wire.attributes)) {
      throw new Error("Dialogue metadata wire format is invalid");
    }

    function decode(value) {
      if (!Array.isArray(value)) return value;
      if (value[0] === "s") {
        if (value.length !== 2 || !Number.isInteger(value[1]) ||
            typeof wire.strings[value[1]] !== "string") {
          throw new Error("Dialogue string reference is invalid");
        }
        return wire.strings[value[1]];
      }
      if (value[0] === "~") return value.slice(1).map(decode);
      if (value[0] === "#") {
        if ((value.length - 1) % 2 !== 0) {
          throw new Error("Dialogue record row is invalid");
        }
        const result = Object.create(null);
        for (let index = 1; index < value.length; index += 2) {
          const fieldIndex = value[index];
          const field = wire.fields[fieldIndex];
          if (!Number.isInteger(fieldIndex) || typeof field !== "string" ||
              Object.prototype.hasOwnProperty.call(result, field)) {
            throw new Error("Dialogue field reference is invalid");
          }
          result[field] = decode(value[index + 1]);
        }
        return result;
      }
      return value.map(decode);
    }

    const metadata = decode(wire.metadata);
    if (!metadata || typeof metadata !== "object" || Array.isArray(metadata)) {
      throw new Error("Dialogue metadata record is invalid");
    }
    for (const [key, value] of Object.entries(metadata)) {
      if (key === "schemaVersion" || key === "contentVersion" ||
          key === "wire" || key === "transcripts") {
        throw new Error("Dialogue metadata contains a reserved field");
      }
      data[key] = value;
    }
    return data;
  }

  function compactString(value, data) {
    if (!Array.isArray(value) || value.length !== 2 || value[0] !== "s") return value;
    const index = value[1];
    if (!Number.isInteger(index) || typeof data.wire.strings[index] !== "string") {
      throw new Error("Dialogue string reference is invalid");
    }
    return data.wire.strings[index];
  }

  function transcriptTag(record, data) {
    const index = record[0];
    const tag = data.wire.tags[index];
    if (!Number.isInteger(index) || typeof tag !== "string") {
      throw new Error("Dialogue transcript tag reference is invalid");
    }
    return tag;
  }

  function transcriptAttributes(record, data) {
    const packed = record[1];
    if (!Array.isArray(packed) || packed.length % 2 !== 0) {
      throw new Error("Dialogue transcript attributes are invalid");
    }
    const attrs = Object.create(null);
    for (let index = 0; index < packed.length; index += 2) {
      const keyIndex = packed[index];
      const key = data.wire.attributes[keyIndex];
      if (!Number.isInteger(keyIndex) || typeof key !== "string" ||
          Object.prototype.hasOwnProperty.call(attrs, key)) {
        throw new Error("Dialogue transcript attribute reference is invalid");
      }
      attrs[key] = compactString(packed[index + 1], data);
    }
    return attrs;
  }

  function isCompactString(value) {
    return Array.isArray(value) && value.length === 2 && value[0] === "s";
  }

  function validateVariants(data, speakerData, locale) {
    if (!speakerData || speakerData.schemaVersion !== SCHEMA_VERSION ||
        speakerData.locale !== locale || speakerData.contentVersion !== data.contentVersion ||
        !Array.isArray(speakerData.speakers) || !Array.isArray(speakerData.variants) ||
        !Array.isArray(data.events) || data.events.length !== data.transcripts.length ||
        !Array.isArray(data.eventIds) || data.eventIds.length !== data.transcripts.length) {
      throw new Error("Speaker data does not match the dialogue page");
    }
    const profileIds = new Set(speakerData.speakers.map((item) => String(item.speakerId || "")));
    const variants = new Map();
    for (const record of speakerData.variants) {
      if (!record || typeof record.variantId !== "string" || !record.variantId ||
          typeof record.speakerId !== "string" || !profileIds.has(record.speakerId) ||
          record.locale !== locale || typeof record.displayName !== "string" ||
          (record.displayNameParts !== undefined &&
            (!Array.isArray(record.displayNameParts) ||
              record.displayNameParts.some((part) => typeof part !== "string"))) ||
          variants.has(record.variantId)) {
        throw new Error("Speaker variant data is invalid");
      }
      variants.set(record.variantId, record);
    }
    for (const [index, transcript] of data.transcripts.entries()) {
      const visit = (node) => {
        if (typeof node === "string" || isCompactString(node)) return;
        if (!Array.isArray(node) || node.length !== 3 ||
            !Number.isInteger(node[0]) || !Array.isArray(node[1]) ||
            !Array.isArray(node[2])) {
          throw new Error("Dialogue transcript node is invalid");
        }
        transcriptTag(node, data);
        const attrs = transcriptAttributes(node, data);
        const variantId = attrs["data-speaker-variant-ref"];
        if (typeof variantId === "string" && !variants.has(variantId)) {
          throw new Error("Dialogue references an unknown speaker variant");
        }
        node[2].forEach(visit);
      };
      if (!Array.isArray(transcript)) throw new Error("Dialogue transcript is invalid");
      transcript.forEach(visit);

      const event = data.events[index];
      if (!event || event.eventId !== data.eventIds[index] ||
          (event.participants !== undefined && !Array.isArray(event.participants)) ||
          (event.participantBars !== undefined && !Array.isArray(event.participantBars)) ||
          (event.hasInlineParticipantBars !== undefined &&
            typeof event.hasInlineParticipantBars !== "boolean")) {
        throw new Error("Dialogue event data does not match the page");
      }
      for (const participant of event.participants || []) {
        if (!participant || typeof participant !== "object" || Array.isArray(participant)) {
          throw new Error("Dialogue participant data is invalid");
        }
        if (typeof participant.variantId === "string") {
          const variant = variants.get(participant.variantId);
          if (!variant || variant.speakerId !== participant.speakerId) {
            throw new Error("Dialogue participant references an unknown speaker variant");
          }
        }
      }
      for (const bar of event.participantBars || []) {
        if (!bar || !bar.tree || !Array.isArray(bar.participantIndexes)) {
          throw new Error("Dialogue participant bar data is invalid");
        }
        const visitSourceNode = (node, inheritedSpeakerId) => {
          if (!node || typeof node !== "object" || Array.isArray(node)) {
            throw new Error("Dialogue participant markup is invalid");
          }
          if (node.type === "text") {
            if (typeof node.value !== "string") {
              throw new Error("Dialogue participant text is invalid");
            }
            return;
          }
          if (node.type !== "element" || typeof node.tag !== "string" ||
              !node.attrs || typeof node.attrs !== "object" || Array.isArray(node.attrs) ||
              !Array.isArray(node.children)) {
            throw new Error("Dialogue participant element is invalid");
          }
          const speakerId = typeof node.attrs["data-speaker-id"] === "string"
            ? node.attrs["data-speaker-id"] : inheritedSpeakerId;
          const variantId = node.attrs["data-speaker-variant-ref"];
          if (typeof variantId === "string") {
            const variant = variants.get(variantId);
            if (!variant || (speakerId && variant.speakerId !== speakerId)) {
              throw new Error("Dialogue participant references an unknown speaker variant");
            }
          }
          node.children.forEach((child) => visitSourceNode(child, speakerId));
        };
        visitSourceNode(bar.tree, null);
        for (const participantIndex of bar.participantIndexes) {
          if (!Number.isInteger(participantIndex) || participantIndex < 0 ||
              participantIndex >= (event.participants || []).length) {
            throw new Error("Dialogue participant bar references an unknown role");
          }
        }
      }
    }
    return variants;
  }

  function hydrateSpeakers(root, variants) {
    for (const node of root.querySelectorAll("[data-speaker-variant-ref]")) {
      const record = variants.get(node.dataset.speakerVariantRef);
      if (!record) throw new Error("Dialogue references an unknown speaker variant");
      if (node.classList.contains("speaker") || node.classList.contains("participant-name")) {
        if (node.classList.contains("participant-name") &&
            Array.isArray(record.displayNameParts)) {
          const parts = Array.from(node.querySelectorAll("[data-reader-variant-part]"));
          for (const target of parts) {
            const partIndex = Number(target.dataset.readerVariantPart);
            if (!Number.isInteger(partIndex) || typeof record.displayNameParts[partIndex] !== "string") {
              throw new Error("Speaker variant name part is invalid");
            }
            target.textContent = record.displayNameParts[partIndex];
          }
        } else {
          const value = node.classList.contains("participant-name")
            ? node.querySelector('[data-reader-variant-text="true"]') : null;
          (value || node).textContent = record.displayName;
        }
      } else if (node.tagName === "IMG") {
        if (record.portrait) {
          if (!safeUrl(record.portrait)) throw new Error("Speaker portrait URL is invalid");
        }
        const attrs = record.portraitAttributes || {
          src: record.portrait, alt: record.portraitAlt,
        };
        setAttributes(node, attrs, new Map(), new Set());
      }
    }
  }

  function makeFallbackParticipantSection(container, event, index, data, variants, locale) {
    const panel = container.closest(".dialogue-panel") || container.parentElement;
    if (!panel) return null;

    const evidenceBySpeaker = data.speakerEvidence || {};
    const messageAnchors = new Set((event.messages || [])
      .map((message) => message && message.anchorId)
      .filter((anchor) => typeof anchor === "string" && anchor));
    const participants = (event.participants || []).filter((participant) => {
      if (!participant || typeof participant.speakerId !== "string" ||
          typeof participant.variantId !== "string") return false;
      const variant = variants.get(participant.variantId);
      const evidence = evidenceBySpeaker[participant.speakerId];
      const anchor = participant.firstAnchor ||
        (typeof participant.href === "string" && participant.href.startsWith("#")
          ? participant.href.slice(1) : "");
      return Boolean(
        variant && variant.speakerId === participant.speakerId &&
        evidence && evidence.relation === "explicit source speaker profile" &&
        /^[A-Za-z][A-Za-z0-9_.:-]*$/.test(anchor) && messageAnchors.has(anchor)
      );
    });
    if (participants.length === 0) return null;

    const section = document.createElement("section");
    section.className = "participants";
    section.dataset.readerGeneratedParticipants = "true";
    section.setAttribute("aria-labelledby", "reader-participants-heading-" + index);

    const heading = document.createElement("h2");
    heading.id = "reader-participants-heading-" + index;
    heading.textContent = localized(
      locale, "Participants · " + participants.length,
      "參與角色 · " + participants.length,
    );
    section.append(heading);

    const hint = document.createElement("p");
    hint.className = "participant-hint";
    hint.textContent = localized(
      locale, "Select a participant to jump to their first line.",
      "點選角色，跳至首次發言。",
    );
    section.append(hint);

    const list = document.createElement("ul");
    list.className = "participant-list";
    for (const participant of participants) {
      const variant = variants.get(participant.variantId);
      const anchor = participant.firstAnchor || participant.href.slice(1);
      const item = document.createElement("li");
      const link = document.createElement("a");
      link.className = "participant-link";
      link.href = "#" + anchor;
      link.dataset.speakerId = participant.speakerId;
      if (participant.side) link.dataset.side = participant.side;

      if (variant.portrait) {
        const portrait = safeUrl(variant.portrait);
        if (!portrait) throw new Error("Speaker portrait URL is invalid");
        const image = document.createElement("img");
        image.className = "participant-avatar";
        const attrs = {
          ...(variant.portraitAttributes || {
            src: portrait,
            alt: typeof variant.portraitAlt === "string" ? variant.portraitAlt : "",
            loading: "lazy",
            decoding: "async",
          }),
          class: "participant-avatar",
        };
        delete attrs.width;
        delete attrs.height;
        setAttributes(image, attrs, new Map(), new Set());
        link.append(image);
      }

      const details = document.createElement("span");
      details.className = "participant-details";
      const name = document.createElement("span");
      name.className = "participant-name";
      name.textContent = variant.displayName;
      details.append(name);

      if (participant.side === "left" || participant.side === "right") {
        const side = document.createElement("span");
        side.className = "participant-side";
        side.textContent = localized(
          locale,
          participant.side === "left" ? "Left" : "Right",
          participant.side === "left" ? "左側" : "右側",
        );
        details.append(side);
      }
      link.append(details);
      item.append(link);
      list.append(item);
    }
    section.append(list);
    return { panel, section };
  }

  function makeAuthoredParticipantSection(bar, anchors, replacing, seen, variants) {
    if (!bar || !bar.tree) return null;
    const section = makeSourceNode(bar.tree, anchors, seen, replacing);
    if (!section || section.nodeType !== Node.ELEMENT_NODE ||
        !section.classList.contains("participants")) {
      throw new Error("Dialogue participant section is invalid");
    }
    hydrateSpeakers(section, variants);
    section.dataset.readerGeneratedParticipants = "true";
    return section;
  }

  function makeParticipantSections(container, event, index, data, variants, locale,
    anchors, replacing, seen) {
    const panel = container.closest(".dialogue-panel") || container.parentElement;
    if (!panel) return [];

    if (Array.isArray(event.participantBars) && event.participantBars.length > 0) {
      return event.participantBars.map((bar) => {
        const section = makeAuthoredParticipantSection(
          bar, anchors, replacing, seen, variants,
        );
        if (!section) throw new Error("Dialogue participant section is missing");
        const idNodes = [section, ...section.querySelectorAll("[id]")];
        const placeholder = idNodes.map((node) => anchors.get(node.id))
          .find((node) => node && node.hasAttribute("data-reader-role-anchor"));
        return { panel, section, placeholder };
      });
    }
    if (event.hasInlineParticipantBars) return [];

    const fallback = makeFallbackParticipantSection(
      container, event, index, data, variants, locale,
    );
    if (!fallback) return [];
    fallback.section.dataset.readerGeneratedParticipants = "true";
    return [fallback];
  }

  function start() {
    const script = scriptNode();
    const containers = Array.from(document.querySelectorAll(".transcript"));
    if (!script || containers.length === 0 || script.dataset.readerInitialized === "true") return;
    script.dataset.readerInitialized = "true";

    const locale = script.dataset.locale || document.body.dataset.locale || "en";
    const expectedVersion = script.dataset.contentVersion || "";
    const expectedReaderVersion = script.dataset.readerVersion || "";
    const dataName = script.dataset.json || "data.json";
    const speakerName = script.dataset.speakers || "";
    const anchorPlaceholders = Array.from(
      document.querySelectorAll("[data-reader-anchor][id]"),
    );
    const placeholders = containers.map(() => new Map(
      anchorPlaceholders.map((node) => [node.id, node]),
    ));
    const statuses = containers.map((container) => container.querySelector(".reader-status"));
    let loading = false;

    function scrollToHash() {
      if (!window.location.hash) return;
      let id;
      try {
        id = decodeURIComponent(window.location.hash.slice(1));
      } catch {
        id = window.location.hash.slice(1);
      }
      const target = document.getElementById(id);
      if (target) target.scrollIntoView({ block: "start" });
    }

    function statusFor(index, message, isError) {
      const container = containers[index];
      const matches = Array.from(container.querySelectorAll(".reader-status"));
      let status = matches.shift() || document.createElement("div");
      matches.forEach((duplicate) => duplicate.remove());
      status.className = isError ? "reader-status reader-status-error" : "reader-status";
      status.setAttribute("role", "status");
      status.setAttribute("aria-live", "polite");
      status.replaceChildren(document.createTextNode(message));
      if (!status.isConnected) container.prepend(status);
      statuses[index] = status;
      return status;
    }

    function showLoading() {
      containers.forEach((_, index) => statusFor(
        index, localized(locale, "Loading dialogue…", "正在載入對話…"), false,
      ));
    }

    function showError(message) {
      loading = false;
      containers.forEach((_, index) => {
        const status = statusFor(index, message + " ", true);
        const retry = document.createElement("button");
        retry.type = "button";
        retry.className = "reader-retry";
        retry.textContent = localized(locale, "Retry", "重試");
        retry.addEventListener("click", load);
        status.append(retry);
      });
    }

    function validatePage(data, speakers, dataUrl, speakerUrl, scriptUrl) {
      if (!data || data.schemaVersion !== SCHEMA_VERSION || !data.page ||
          !data.provenance || typeof data.provenance.dialogueCommit !== "string" ||
          !Array.isArray(data.transcripts) || data.transcripts.length !== containers.length) {
        throw new Error("Dialogue data does not match the page");
      }
      if (data.page.locale !== locale || data.contentVersion !== expectedVersion ||
          !speakers || speakers.locale !== locale ||
          speakers.contentVersion !== expectedVersion) {
        throw new Error("Dialogue content version or locale mismatch");
      }
      if (scriptUrl.searchParams.get("v") !== expectedReaderVersion ||
          dataUrl.searchParams.get("v") !== expectedVersion ||
          speakerUrl.searchParams.get("v") !== expectedVersion) {
        throw new Error("Dialogue asset version mismatch");
      }
      const canonical = document.querySelector('link[rel="canonical"]');
      const canonicalPath = canonical ? new URL(canonical.href, window.location.href).pathname : window.location.pathname;
      const dataPath = normalizePath(data.page.url);
      if (dataPath !== normalizePath(canonicalPath) ||
          dataPath !== normalizePath(window.location.pathname)) {
        throw new Error("Dialogue page URL mismatch");
      }
      return validateVariants(data, speakers, locale);
    }

    function render(data, variants) {
      const fragments = [];
      const participantSections = [];
      const panels = new Set(containers.map((container) =>
        container.closest(".dialogue-panel") || container.parentElement,
      ).filter(Boolean));
      const oldParticipantSections = [];
      for (const panel of panels) {
        for (const section of panel.querySelectorAll(".participants")) {
          if (!containers.some((container) => container.contains(section))) {
            oldParticipantSections.push(section);
          }
        }
      }
      const replacing = new Set(oldParticipantSections);
      containers.forEach((_, index) => {
        const fragment = document.createDocumentFragment();
        const seen = new Set();
        for (const item of data.transcripts[index]) {
          fragment.append(makeNode(item, placeholders[index], seen, data, replacing));
        }
        hydrateSpeakers(fragment, variants);
        fragments.push(fragment);
        participantSections.push(makeParticipantSections(
          containers[index], data.events[index], index, data, variants, locale,
          placeholders[index], replacing, seen,
        ));
      });

      const previousChildren = containers.map((container) => Array.from(container.childNodes));
      const oldPositions = oldParticipantSections.map((section) => ({
        section, parent: section.parentNode, nextSibling: section.nextSibling,
      }));
      const transferPlaceholders = new Set();
      for (const sections of participantSections) {
        for (const participant of sections) {
          const ids = [participant.section, ...participant.section.querySelectorAll("[id]")];
          for (const node of ids) {
            const placeholder = placeholders[0].get(node.id);
            if (placeholder && placeholder.hasAttribute("data-reader-role-anchor")) {
              transferPlaceholders.add(placeholder);
            }
          }
        }
      }
      const placeholderPositions = new Map(Array.from(transferPlaceholders, (placeholder) => [
        placeholder, { parent: placeholder.parentNode, nextSibling: placeholder.nextSibling },
      ]));
      const insertedSections = [];
      const removedSections = [];
      const removedPlaceholders = [];
      try {
        containers.forEach((container, index) => {
          for (const participant of participantSections[index]) {
            if (!participant.section.isConnected) {
              const host = participant.placeholder && participant.placeholder.parentNode
                ? participant.placeholder.parentNode : container.parentNode;
              if (!host) throw new Error("Dialogue participant section has no insertion point");
              const before = participant.placeholder && participant.placeholder.parentNode === host
                ? participant.placeholder : container.parentNode === host ? container : null;
              host.insertBefore(participant.section, before);
              insertedSections.push(participant.section);
            }
          }
          container.replaceChildren(fragments[index]);
        });
        for (const section of oldParticipantSections) {
          if (section.parentNode) {
            section.parentNode.removeChild(section);
            removedSections.push(section);
          }
        }
        for (const placeholder of transferPlaceholders) {
          if (placeholder.parentNode) {
            placeholder.parentNode.removeChild(placeholder);
            removedPlaceholders.push(placeholder);
          }
        }
      } catch (error) {
        insertedSections.reverse().forEach((section) => section.remove());
        containers.forEach((container, index) => container.replaceChildren(...previousChildren[index]));
        for (const placeholder of removedPlaceholders.reverse()) {
          const position = placeholderPositions.get(placeholder);
          if (position && position.parent) {
            const before = position.nextSibling && position.nextSibling.parentNode === position.parent
              ? position.nextSibling : null;
            position.parent.insertBefore(placeholder, before);
          }
        }
        for (const section of removedSections.reverse()) {
          const position = oldPositions.find((item) => item.section === section);
          if (position && position.parent) {
            const before = position.nextSibling && position.nextSibling.parentNode === position.parent
              ? position.nextSibling : null;
            position.parent.insertBefore(section, before);
          }
        }
        throw error;
      }
      containers.forEach((_, index) => { statuses[index] = null; });
      document.dispatchEvent(new CustomEvent("darktide:dialogue-ready", {
        detail: { page: data.page, contentVersion: data.contentVersion },
      }));
      requestAnimationFrame(scrollToHash);
    }

    async function load() {
      if (loading) return;
      loading = true;
      showLoading();
      try {
        const scriptUrl = new URL(script.src, window.location.href);
        const dataUrl = new URL(dataName, window.location.href);
        const speakerUrl = new URL(speakerName, window.location.href);
        const [dataResponse, speakerResponse] = await Promise.all([
          fetch(dataUrl.href, { credentials: "same-origin" }),
          fetch(speakerUrl.href, { credentials: "same-origin" })
        ]);
        if (!dataResponse.ok) throw new Error("Dialogue data HTTP " + dataResponse.status);
        if (!speakerResponse.ok) throw new Error("Speaker data HTTP " + speakerResponse.status);
        const [data, speakers] = await Promise.all([dataResponse.json(), speakerResponse.json()]);
        decodeMetadata(data);
        const variants = validatePage(data, speakers, dataUrl, speakerUrl, scriptUrl);
        render(data, variants);
        loading = false;
      } catch (error) {
        showError(localized(locale, "Dialogue could not be loaded.", "目前無法載入對話。"));
        if (window.console && console.error) console.error("Dialogue reader failed", error);
      }
    }

    window.addEventListener("hashchange", scrollToHash);
    load();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
