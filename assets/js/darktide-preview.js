(() => {
  "use strict";

  const root = document.querySelector("[data-darktide-preview]");

  if (!root) {
    return;
  }

  const content = root.querySelector("#dialogue-content");
  const title = root.querySelector("#active-event-title");
  const subtitle = root.querySelector("#active-event-subtitle");
  const source = root.querySelector("#dialogue-source");
  const status = root.querySelector("#dialogue-status");
  const eventSelect = root.querySelector("#event-select");
  const eventTypeSelect = root.querySelector("#event-type-select");
  const eventTypeTitle = root.querySelector("#active-event-type");
  const eventTypeGroups = [...root.querySelectorAll("details[data-event-type]")];
  const eventOptionGroups = [...eventSelect.querySelectorAll("optgroup[data-event-type]")];
  const eventButtons = [...root.querySelectorAll("[data-event-button]")];
  const languageButtons = [...root.querySelectorAll("[data-language-button]")];
  const templates = new Map(
    [...root.querySelectorAll("template[data-dialogue-template]")].map(
      (template) => [template.id, template]
    )
  );
  const sourceRoot =
    "https://github.com/Aussiemon/Darktide-Source-Code/blob/" +
    "7e662fcda16219d775b84af50322be2e9cd9d62e/" +
    "scripts/settings/cinematic_video/templates/";
  const defaultSelection = {
    event: "debriefing_01",
    language: "zh-tw"
  };
  let activeSelection = defaultSelection;

  function selectionFromHash() {
    const match = window.location.hash.match(
      /^#(debriefing_(?:0[1-9]|10))-(en|zh-tw)$/
    );

    if (!match || !templates.has(`${match[1]}-${match[2]}`)) {
      return defaultSelection;
    }

    return {
      event: match[1],
      language: match[2]
    };
  }

  function render(selection) {
    const template = templates.get(`${selection.event}-${selection.language}`);

    if (!template) {
      return;
    }

    const eventType = eventTypeGroups.find(
      (group) => group.dataset.eventType === template.dataset.eventType
    );

    if (!eventType) {
      return;
    }

    activeSelection = selection;
    eventType.open = true;
    eventTypeSelect.value = eventType.dataset.eventType;
    eventTypeTitle.textContent = selection.language === "en"
      ? eventType.dataset.typeTitleEn
      : eventType.dataset.typeTitleZh;
    eventTypeTitle.lang = selection.language === "en" ? "en" : "zh-Hant";
    root.dataset.activeEventType = eventType.dataset.eventType;
    eventOptionGroups.forEach((group) => {
      const selected = group.dataset.eventType === eventType.dataset.eventType;
      group.hidden = !selected;
      group.disabled = !selected;
    });
    content.replaceChildren(template.content.cloneNode(true));
    content.lang = selection.language === "en" ? "en" : "zh-Hant";
    title.textContent = template.dataset.title;
    title.lang = content.lang;
    subtitle.textContent = template.dataset.otherTitle;
    subtitle.lang = selection.language === "en" ? "zh-Hant" : "en";
    source.href = `${sourceRoot}${selection.event}.lua#L1`;
    source.textContent = selection.language === "en" ? "Dialogue source" : "對話來源";
    source.lang = content.lang;
    eventSelect.value = selection.event;
    root.dataset.activeEvent = selection.event;
    root.dataset.activeLanguage = selection.language;

    eventButtons.forEach((button) => {
      const selected = button.dataset.eventButton === selection.event;
      button.setAttribute("aria-pressed", String(selected));
      button.tabIndex = selected ? 0 : -1;
    });

    languageButtons.forEach((button) => {
      button.setAttribute(
        "aria-pressed",
        String(button.dataset.languageButton === selection.language)
      );
    });

    const count = content.querySelectorAll(".message").length;
    status.lang = content.lang;
    status.textContent = selection.language === "en"
      ? `${template.dataset.title}, English, ${count} subtitles.`
      : `${template.dataset.title}，繁體中文，${count} 句字幕。`;
  }

  function navigate(selection) {
    const hash = `#${selection.event}-${selection.language}`;

    if (window.location.hash !== hash) {
      window.history.pushState(null, "", hash);
    }

    render(selection);
  }

  eventButtons.forEach((button) => {
    button.addEventListener("click", () => {
      navigate({
        event: button.dataset.eventButton,
        language: activeSelection.language
      });
    });

    button.addEventListener("keydown", (event) => {
      const group = button.closest("details[data-event-type]");
      const groupButtons = eventButtons.filter(
        (candidate) => candidate.closest("details[data-event-type]") === group
      );
      const index = groupButtons.indexOf(button);
      let nextIndex;

      if (event.key === "ArrowDown" || event.key === "ArrowRight") {
        nextIndex = (index + 1) % groupButtons.length;
      } else if (event.key === "ArrowUp" || event.key === "ArrowLeft") {
        nextIndex = (index - 1 + groupButtons.length) % groupButtons.length;
      } else if (event.key === "Home") {
        nextIndex = 0;
      } else if (event.key === "End") {
        nextIndex = groupButtons.length - 1;
      } else {
        return;
      }

      event.preventDefault();
      groupButtons[nextIndex].click();
      groupButtons[nextIndex].focus();
    });
  });

  languageButtons.forEach((button) => {
    button.addEventListener("click", () => {
      navigate({
        event: activeSelection.event,
        language: button.dataset.languageButton
      });
    });
  });

  eventTypeSelect.addEventListener("change", () => {
    const group = eventOptionGroups.find(
      (candidate) => candidate.dataset.eventType === eventTypeSelect.value
    );
    const options = group ? [...group.querySelectorAll("option")] : [];
    const selected = options.find((option) => option.value === activeSelection.event)
      || options[0];

    if (selected) {
      navigate({
        event: selected.value,
        language: activeSelection.language
      });
    }
  });

  eventSelect.addEventListener("change", () => {
    navigate({
      event: eventSelect.value,
      language: activeSelection.language
    });
  });

  root.querySelector(".skip-link").addEventListener("click", (event) => {
    event.preventDefault();
    content.focus();
  });

  window.addEventListener("hashchange", () => render(selectionFromHash()));
  window.addEventListener("popstate", () => render(selectionFromHash()));

  const initialSelection = selectionFromHash();

  if (!/^#(debriefing_(?:0[1-9]|10))-(en|zh-tw)$/.test(window.location.hash)) {
    window.history.replaceState(
      null,
      "",
      `#${initialSelection.event}-${initialSelection.language}`
    );
  }

  render(initialSelection);
})();
