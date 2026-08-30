(function () {
  "use strict";

  var form = document.querySelector("[data-search-form]");
  if (!form) {
    return;
  }

  var input = form.querySelector("input[name='q']");
  var status = document.querySelector("[data-search-status]");
  var results = document.querySelector("[data-search-results]");
  var indexUrl = form.getAttribute("data-index-url");
  var posts = [];

  function normalize(value) {
    return String(value || "").normalize("NFKC").toLocaleLowerCase("zh-TW");
  }

  function tokensFor(query) {
    return normalize(query).split(/\s+/).filter(Boolean);
  }

  function searchableText(post) {
    return normalize([
      post.title,
      post.description,
      (post.tags || []).join(" ")
    ].join(" "));
  }

  function score(post, tokens) {
    var title = normalize(post.title);
    var description = normalize(post.description);
    var tags = normalize((post.tags || []).join(" "));
    var total = 0;

    tokens.forEach(function (token) {
      if (title.indexOf(token) !== -1) {
        total += 6;
      }
      if (tags.indexOf(token) !== -1) {
        total += 3;
      }
      if (description.indexOf(token) !== -1) {
        total += 1;
      }
    });
    return total;
  }

  function createResult(post) {
    var article = document.createElement("article");
    article.className = "post-card";

    var meta = document.createElement("div");
    meta.className = "post-card__meta";
    var time = document.createElement("time");
    time.dateTime = post.date;
    time.textContent = post.date.replace(/-/g, ".");
    var category = document.createElement("span");
    category.className = "post-card__category";
    category.textContent = post.category;
    meta.appendChild(time);
    meta.appendChild(category);

    var body = document.createElement("div");
    body.className = "post-card__body";
    var heading = document.createElement("h2");
    heading.className = "post-card__title";
    var link = document.createElement("a");
    link.href = post.url;
    link.textContent = post.title;
    heading.appendChild(link);
    var description = document.createElement("p");
    description.textContent = post.description;
    body.appendChild(heading);
    body.appendChild(description);

    var arrow = document.createElement("span");
    arrow.className = "post-card__read";
    arrow.setAttribute("aria-hidden", "true");
    arrow.textContent = "→";

    article.appendChild(meta);
    article.appendChild(body);
    article.appendChild(arrow);
    return article;
  }

  function render(query) {
    var tokens = tokensFor(query);
    results.replaceChildren();

    if (!tokens.length) {
      status.textContent = "輸入關鍵字後，會比對文章標題、摘要與標籤。";
      return;
    }

    var matches = posts
      .filter(function (post) {
        var text = searchableText(post);
        return tokens.every(function (token) { return text.indexOf(token) !== -1; });
      })
      .map(function (post) { return { post: post, score: score(post, tokens) }; })
      .sort(function (left, right) {
        return right.score - left.score || right.post.date.localeCompare(left.post.date);
      });

    if (!matches.length) {
      status.textContent = "找不到符合「" + query.trim() + "」的文章。請縮短關鍵字或改用分類與標籤瀏覽。";
      return;
    }

    status.textContent = "找到 " + matches.length + " 篇符合「" + query.trim() + "」的文章。";
    matches.forEach(function (match) {
      results.appendChild(createResult(match.post));
    });
  }

  function updateUrl(query) {
    var url = new URL(window.location.href);
    if (query.trim()) {
      url.searchParams.set("q", query.trim());
    } else {
      url.searchParams.delete("q");
    }
    window.history.replaceState({}, "", url);
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    updateUrl(input.value);
    render(input.value);
  });

  input.addEventListener("input", function () {
    updateUrl(input.value);
    render(input.value);
  });

  fetch(indexUrl, { credentials: "same-origin" })
    .then(function (response) {
      if (!response.ok) {
        throw new Error("Search index request failed");
      }
      return response.json();
    })
    .then(function (data) {
      posts = Array.isArray(data) ? data : [];
      var initialQuery = new URL(window.location.href).searchParams.get("q") || "";
      input.value = initialQuery;
      render(initialQuery);
    })
    .catch(function () {
      status.textContent = "搜尋索引目前無法載入，請改用分類、標籤或月份封存瀏覽。";
    });
}());
