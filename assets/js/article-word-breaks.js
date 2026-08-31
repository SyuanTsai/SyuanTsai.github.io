(function () {
  "use strict";

  var content = document.querySelector("[data-post-content]");

  if (!content) {
    return;
  }

  var supportsNativePhraseWrapping = typeof CSS === "object"
    && typeof CSS.supports === "function"
    && CSS.supports("word-break", "auto-phrase");

  if (typeof Intl !== "object" || typeof Intl.Segmenter !== "function") {
    if (supportsNativePhraseWrapping) {
      content.dataset.wordSegmentation = "native";
    } else {
      content.dataset.wordSegmentation = "unavailable";
    }
    return;
  }

  var segmenter = new Intl.Segmenter("zh-Hant", { granularity: "word" });
  var joinsFollowingWord = new Set([
    "不",
    "非",
    "未",
    "無",
    "可",
    "難",
    "易",
    "須",
    "需",
    "應",
    "會",
    "能",
    "將",
    "讓",
    "被",
    "把",
    "與",
    "及",
    "或",
    "並",
    "且",
    "但",
    "則",
    "而",
    "以",
    "於",
    "在",
    "由",
    "從",
    "向",
    "對",
    "為",
    "如",
    "若",
    "只能",
    "為非"
  ]);
  var joinsPreviousWord = new Set([
    "性",
    "者",
    "們"
  ]);
  var hanNumerals = new Set([
    "〇",
    "零",
    "一",
    "二",
    "兩",
    "三",
    "四",
    "五",
    "六",
    "七",
    "八",
    "九",
    "十",
    "百",
    "千",
    "萬",
    "億"
  ]);
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

  function isHanWord(part) {
    return part.isWordLike && hasHanCharacter.test(part.segment);
  }

  function shouldJoinWords(left, right) {
    return isHanWord(left)
      && isHanWord(right)
      && (
        joinsFollowingWord.has(left.segment)
        || joinsPreviousWord.has(right.segment)
        || hanNumerals.has(left.segment)
        || hanNumerals.has(right.segment)
      );
  }

  function appendProtectedWord(fragment, text) {
    if (Array.from(text).length < 2) {
      fragment.appendChild(document.createTextNode(text));
      return;
    }

    var word = document.createElement("span");
    word.dataset.wordSegment = "";
    word.textContent = text;
    fragment.appendChild(word);
  }

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
    var fragment = document.createDocumentFragment();
    var insertedProtectedWord = false;

    for (var index = 0; index < segments.length; index += 1) {
      var part = segments[index];

      if (!isHanWord(part)) {
        fragment.appendChild(document.createTextNode(part.segment));
        continue;
      }

      var groupedWord = part.segment;

      while (
        index + 1 < segments.length
        && shouldJoinWords(segments[index], segments[index + 1])
      ) {
        index += 1;
        groupedWord += segments[index].segment;
      }

      appendProtectedWord(fragment, groupedWord);
      insertedProtectedWord = insertedProtectedWord || Array.from(groupedWord).length > 1;
    }

    if (insertedProtectedWord) {
      textNode.parentNode.replaceChild(fragment, textNode);
    }
  });

  content.querySelectorAll("p code, li code, blockquote code").forEach(function (code) {
    if (code.closest("pre")) {
      return;
    }

    var spacing = code.previousSibling;

    if (
      spacing
      && spacing.nodeType === Node.TEXT_NODE
      && /[ \t\r\n]$/.test(spacing.nodeValue || "")
    ) {
      spacing.nodeValue = spacing.nodeValue.replace(/[ \t\r\n]+$/, "\u00a0");
    }
  });

  content.dataset.wordSegmentation = "enhanced";
}());
