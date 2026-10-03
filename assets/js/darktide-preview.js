(() => {
  "use strict";

  const root = document.querySelector("[data-legacy-event-base]");

  if (!root) {
    return;
  }

  function openLegacyEvent() {
    const match = window.location.hash.match(
      /^#(debriefing_(?:0[1-9]|10))-(en|zh-tw)$/
    );

    if (!match) {
      return;
    }

    const eventUrl = `${root.dataset.legacyEventBase}${match[2]}/` +
      `mission-debrief/${match[1]}/`;
    window.location.replace(eventUrl);
  }

  window.addEventListener("hashchange", openLegacyEvent);
  openLegacyEvent();
})();
