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

  headings.forEach(function (heading, index) {
    if (!heading.id) {
      heading.id = "section-" + (index + 1);
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
