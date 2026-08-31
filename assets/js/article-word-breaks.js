(function () {
  "use strict";

  var content = document.querySelector("[data-post-content]");

  if (!content) {
    return;
  }

  var supportsNativePhraseWrapping = typeof CSS === "object"
    && typeof CSS.supports === "function"
    && CSS.supports("word-break", "auto-phrase");

  if (supportsNativePhraseWrapping) {
    content.dataset.wordSegmentation = "native";
    return;
  }

  if (typeof Intl !== "object" || typeof Intl.Segmenter !== "function") {
    content.dataset.wordSegmentation = "unavailable";
    return;
  }

  var segmenter = new Intl.Segmenter("zh-Hant", { granularity: "word" });
  var protectedSelector = [
    "code",
    "kbd",
    "pre",
    "samp",
    "script",
    "style",
    "svg",
    "textarea",
    ".footnotes",
    "[data-word-segment]"
  ].join(",");
  var hasHanCharacter = /[\u3400-\u9fff\uf900-\ufaff]/;
  var textNodes = [];
  var walker = document.createTreeWalker(
    content,
    NodeFilter.SHOW_TEXT,
    {
      acceptNode: function (node) {
        if (!hasHanCharacter.test(node.nodeValue || "")) {
          return NodeFilter.FILTER_REJECT;
        }

        if (node.parentElement && node.parentElement.closest(protectedSelector)) {
          return NodeFilter.FILTER_REJECT;
        }

        return NodeFilter.FILTER_ACCEPT;
      }
    }
  );
  var currentNode;

  while ((currentNode = walker.nextNode())) {
    textNodes.push(currentNode);
  }

  textNodes.forEach(function (textNode) {
    var segments = Array.from(segmenter.segment(textNode.nodeValue));
    var containsProtectedWord = segments.some(function (part) {
      return part.isWordLike && hasHanCharacter.test(part.segment) && part.segment.length > 1;
    });

    if (!containsProtectedWord) {
      return;
    }

    var fragment = document.createDocumentFragment();

    segments.forEach(function (part) {
      if (part.isWordLike && hasHanCharacter.test(part.segment) && part.segment.length > 1) {
        var word = document.createElement("span");
        word.dataset.wordSegment = "";
        word.textContent = part.segment;
        fragment.appendChild(word);
      } else {
        fragment.appendChild(document.createTextNode(part.segment));
      }
    });

    textNode.parentNode.replaceChild(fragment, textNode);
  });

  content.dataset.wordSegmentation = "fallback";
}());
