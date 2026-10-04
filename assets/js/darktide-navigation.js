(function () {
  "use strict";

  const SCHEMA_VERSION = 1;
  const DIRECTORY_SELECTOR = "details.dt-directory[data-navigation-root]";

  function text(locale, zh, en) {
    return locale === "en" ? en : zh;
  }

  function labelFor(node, locale) {
    return locale === "en" ? (node.titleEn || node.title || "") : (node.title || node.titleEn || "");
  }

  function safeLocalHref(value) {
    const url = new URL(value, window.location.origin);
    if (url.origin !== window.location.origin || !url.pathname.startsWith("/darktide/")) {
      throw new Error("Navigation URL is outside the local Darktide route.");
    }
    return url.pathname + url.search + url.hash;
  }

  async function readJson(url) {
    const parsed = new URL(url, window.location.origin);
    if (parsed.origin !== window.location.origin) {
      throw new Error("Navigation JSON must be served from this site.");
    }
    const response = await fetch(parsed.href, {
      credentials: "same-origin",
      cache: "default"
    });
    if (!response.ok) {
      throw new Error("Navigation JSON request failed with " + response.status + ".");
    }
    return response.json();
  }

  function makeDetails(summaryText, open) {
    const details = document.createElement("details");
    if (open) details.open = true;
    const summary = document.createElement("summary");
    summary.textContent = summaryText;
    details.append(summary);
    return details;
  }

  function makeLevel() {
    const level = document.createElement("div");
    level.className = "dt-level";
    return level;
  }

  function isCurrent(node, currentUrl) {
    const nodeUrl = new URL(node.url, window.location.origin);
    const pageUrl = new URL(currentUrl, window.location.origin);
    return nodeUrl.pathname === pageUrl.pathname && nodeUrl.hash === pageUrl.hash;
  }

  function makeLink(node, locale, currentUrl, englishSmall) {
    const anchor = document.createElement("a");
    anchor.href = safeLocalHref(node.url);
    anchor.append(document.createTextNode(labelFor(node, locale)));
    if (englishSmall && locale !== "en" && node.titleEn) {
      const small = document.createElement("small");
      small.lang = "en";
      small.textContent = node.titleEn;
      anchor.append(small);
    }
    if (isCurrent(node, currentUrl)) anchor.setAttribute("aria-current", "page");
    return anchor;
  }

  function appendLink(level, node, locale, currentUrl, englishSmall) {
    level.append(makeLink(node, locale, currentUrl, englishSmall));
  }

  function nearby(items, currentUrl) {
    if (!items || items.length === 0) return [];
    const current = new URL(currentUrl, window.location.origin);
    const index = items.findIndex(function (item) {
      const url = new URL(item.url, window.location.origin);
      return url.pathname === current.pathname && url.hash === current.hash;
    });
    if (index < 0) return items.slice(0, 5);
    return items.slice(Math.max(0, index - 2), Math.min(items.length, index + 3));
  }

  function renderSkillCategory(level, category, branch, locale, currentUrl) {
    const active = Boolean(
      branch &&
      branch.scope === "skill-category" &&
      branch.currentCategory &&
      branch.currentCategory.id === category.id
    );
    const details = makeDetails(labelFor(category, locale), active);
    if (active) details.dataset.navigationCurrentCategory = "true";
    const contents = makeLevel();
    appendLink(contents, category, locale, currentUrl, false);
    if (active) {
      nearby(branch.items || [], currentUrl).forEach(function (item) {
        appendLink(contents, item, locale, currentUrl, true);
      });
      appendLink(
        contents,
        {title: text(locale, "完整分類目錄 →", "Complete category list →"), url: category.url},
        locale,
        currentUrl,
        false
      );
    }
    details.append(contents);
    level.append(details);
  }

  function renderActiveClass(level, classNode, branch, locale, currentUrl) {
    const details = makeDetails(labelFor(classNode, locale), true);
    details.dataset.navigationCurrentClass = "true";
    const contents = makeLevel();
    appendLink(contents, classNode, locale, currentUrl, true);
    (branch.categories || []).forEach(function (category) {
      renderSkillCategory(contents, category, branch, locale, currentUrl);
    });
    details.append(contents);
    level.append(details);
  }

  function renderSkills(root, branch, page, locale) {
    const skills = root.skills;
    const active = page.kind.startsWith("skill-");
    const group = makeDetails(labelFor(skills, locale), active);
    group.dataset.navigationSkillsGroup = "true";
    const level = makeLevel();
    appendLink(level, skills, locale, page.url, false);
    const activeClassUrl = branch && branch.class ? branch.class.url : "";
    (skills.classes || []).forEach(function (classNode) {
      if (classNode.url === activeClassUrl && branch) {
        renderActiveClass(level, classNode, branch, locale, page.url);
      } else {
        appendLink(level, classNode, locale, page.url, true);
      }
    });
    group.append(level);
    return group;
  }

  function renderDialogueBranch(level, root, branch, page, locale) {
    const active = (root.categories || []).find(function (item) {
      return item.url === (page.category || "");
    });
    appendLink(level, root.home, locale, page.url, false);
    if (!active) {
      (root.categories || []).forEach(function (category) {
        appendLink(level, category, locale, page.url, false);
      });
      return;
    }

    const currentCategory = makeDetails(labelFor(active, locale), true);
    currentCategory.dataset.navigationCurrentCategory = "true";
    const currentLevel = makeLevel();
    appendLink(currentLevel, active, locale, page.url, false);
    if (
      branch &&
      branch.scope === "dialogue-catalog" &&
      branch.category &&
      branch.category.url === active.url
    ) {
      nearby(branch.items || [], page.url).forEach(function (item) {
        appendLink(currentLevel, item, locale, page.url, false);
      });
      if (branch.catalog && branch.catalog.url !== page.url) {
        appendLink(
          currentLevel,
          {title: text(locale, "完整目錄 →", "Complete directory →"), url: branch.catalog.url},
          locale,
          page.url,
          false
        );
      }
    }
    currentCategory.append(currentLevel);
    level.append(currentCategory);

    const others = makeDetails(text(locale, "其他分類", "Other categories"), false);
    const otherLevel = makeLevel();
    (root.categories || []).forEach(function (category) {
      if (category.url !== active.url) appendLink(otherLevel, category, locale, page.url, false);
    });
    others.append(otherLevel);
    level.append(others);
  }

  function sameNavigationPage(first, second) {
    const firstUrl = new URL(first, window.location.origin);
    const secondUrl = new URL(second, window.location.origin);
    return firstUrl.pathname === secondUrl.pathname && firstUrl.hash === secondUrl.hash;
  }

  function ensureCurrentLink(content, page, locale) {
    const links = Array.from(content.querySelectorAll("a"));
    const existing = links.find(function (anchor) {
      return sameNavigationPage(anchor.href, page.url);
    });
    if (existing) {
      existing.setAttribute("aria-current", "page");
      return;
    }

    const current = {
      title: page.title || page.url,
      url: page.url
    };
    let target = null;
    if (page.kind.startsWith("skill-")) {
      target = content.querySelector("[data-navigation-current-category] .dt-level") ||
        content.querySelector("[data-navigation-current-class] .dt-level") ||
        content.querySelector("[data-navigation-skills-group] .dt-level");
    } else {
      target = content.querySelector("[data-navigation-current-category] .dt-level") ||
        content.querySelector("[data-navigation-dialogue-group] .dt-level");
    }
    (target || content).append(makeLink(current, locale, page.url, false));
  }

  function renderNavigation(root, branch, page, locale) {
    const fragment = document.createDocumentFragment();
    fragment.append(renderSkills(root, branch, page, locale));
    const dialogue = makeDetails(
      text(locale, "對話與字幕", "Dialogue and subtitles"),
      !page.kind.startsWith("skill-")
    );
    dialogue.dataset.navigationDialogueGroup = "true";
    const level = makeLevel();
    renderDialogueBranch(level, root, branch, page, locale);
    dialogue.append(level);
    fragment.append(dialogue);
    return fragment;
  }

  function validate(root, branch, directory) {
    const locale = directory.dataset.navigationLocale;
    const version = directory.dataset.navigationVersion;
    const pageUrl = directory.dataset.navigationPage;
    if (
      root.schemaVersion !== SCHEMA_VERSION ||
      root.locale !== locale ||
      root.contentVersion !== version ||
      !root.home ||
      !root.skills ||
      !Array.isArray(root.categories)
    ) {
      throw new Error("The navigation root has an unsupported schema or version.");
    }
    if (branch && (
      branch.schemaVersion !== SCHEMA_VERSION ||
      branch.locale !== locale ||
      branch.contentVersion !== version ||
      branch.key !== directory.dataset.navigationBranchKey
    )) {
      throw new Error("The navigation branch does not match this page.");
    }
    if (!pageUrl || !pageUrl.startsWith("/darktide/")) {
      throw new Error("The page navigation URL is missing.");
    }
  }

  async function enhance(directory) {
    const locale = directory.dataset.navigationLocale || "zh-tw";
    const status = directory.querySelector(".dt-directory-status");
    const statusText = directory.querySelector("[data-navigation-status-text]");
    const content = directory.querySelector("[data-navigation-content]");
    if (!content) return;

    try {
      const root = await readJson(directory.dataset.navigationRoot);
      const branchUrl = directory.dataset.navigationBranch;
      const branch = branchUrl ? await readJson(branchUrl) : null;
      validate(root, branch, directory);
      const currentPage = {
        url: directory.dataset.navigationPage,
        title: directory.dataset.navigationCurrentTitle || "",
        kind: directory.dataset.navigationKind || "",
        category: directory.dataset.navigationCategory || ""
      };
      content.replaceChildren(renderNavigation(root, branch, currentPage, locale));
      ensureCurrentLink(content, currentPage, locale);
      if (status) status.hidden = true;
    } catch (error) {
      if (statusText) {
        statusText.textContent = text(
          locale,
          "完整目錄載入失敗。請使用上方基本連結，或重新載入重試。",
          "The complete directory failed to load. Use the basic links above or reload to retry."
        );
      }
      if (status) status.hidden = false;
      window.console.warn("Darktide navigation is unavailable.", error);
    }
  }

  document.querySelectorAll(DIRECTORY_SELECTOR).forEach(function (directory) {
    void enhance(directory);
  });
})();
