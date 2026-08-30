---
layout: default
title: 搜尋文章
description: 搜尋公開文章的標題、摘要與標籤。
permalink: /search/
---

<section class="discovery-page search-page" aria-labelledby="search-title">
  <header class="page-intro">
    <p class="page-intro__eyebrow">Search</p>
    <h1 id="search-title">{{ page.title | escape }}</h1>
    <p>{{ page.description | escape }}</p>
  </header>

  <nav class="discovery-nav" aria-label="文章探索方式">
    <a href="{{ '/categories/' | relative_url }}">所有分類</a>
    <a href="{{ '/tags/' | relative_url }}">所有標籤</a>
    <a href="{{ '/archives/' | relative_url }}">月份封存</a>
    <a href="{{ '/search/' | relative_url }}" aria-current="page">搜尋文章</a>
  </nav>

  <form class="search-form" role="search" data-search-form data-index-url="{{ '/search.json' | relative_url }}">
    <label for="site-search">搜尋關鍵字</label>
    <div class="search-form__controls">
      <input id="site-search" name="q" type="search" autocomplete="off" placeholder="例如：Code Review、SQL Server、maintainability">
      <button type="submit">搜尋</button>
    </div>
  </form>

  <p class="search-status" data-search-status role="status" aria-live="polite">輸入關鍵字後，會比對文章標題、摘要與標籤。</p>
  <div class="post-list search-results" data-search-results></div>
</section>

<script src="{{ '/assets/js/search.js' | relative_url }}" defer></script>
