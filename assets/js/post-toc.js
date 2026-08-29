(function () {
  var toc = document.querySelector("[data-post-toc]");
  var tocList = document.querySelector("[data-post-toc-list]");
  var content = document.querySelector("[data-post-content]");

  if (!toc || !tocList || !content) {
    return;
  }

  var headings = Array.prototype.slice.call(content.querySelectorAll("h2, h3"));

  if (headings.length === 0) {
    return;
  }

  function createHeadingId(text) {
    var baseId = text
      .trim()
      .toLowerCase()
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^\p{Letter}\p{Number}]+/gu, "-")
      .replace(/^-+|-+$/g, "") || "section";
    var candidateId = baseId;
    var suffix = 2;

    while (document.getElementById(candidateId)) {
      candidateId = baseId + "-" + suffix;
      suffix += 1;
    }

    return candidateId;
  }

  headings.forEach(function (heading) {
    if (!heading.id) {
      heading.id = createHeadingId(heading.textContent);
    }

    var item = document.createElement("li");
    var link = document.createElement("a");

    if (heading.tagName === "H3") {
      item.className = "post-toc__item--nested";
    }

    link.href = "#" + encodeURIComponent(heading.id);
    link.textContent = heading.textContent.trim();
    item.appendChild(link);
    tocList.appendChild(item);
  });

  toc.hidden = false;
}());
