---
layout: default
title: 標籤
description: 依技術、工具與議題跨分類尋找相關文章。
permalink: /tags/
---

<section class="discovery-page" aria-labelledby="tags-title">
  <header class="page-intro">
    <p class="page-intro__eyebrow">Tags</p>
    <h1 id="tags-title">{{ page.title | escape }}</h1>
    <p>{{ page.description | escape }}</p>
  </header>

  <nav class="discovery-nav" aria-label="文章探索方式">
    <a href="{{ '/categories/' | relative_url }}">所有分類</a>
    <a href="{{ '/tags/' | relative_url }}" aria-current="page">所有標籤</a>
    <a href="{{ '/archives/' | relative_url }}">月份封存</a>
    <a href="{{ '/search/' | relative_url }}">搜尋文章</a>
  </nav>

  <div class="tag-cloud" role="list">
    {%- for tag in site.data.taxonomy.tags -%}
      {%- assign tag_posts = site.tags[tag.slug] -%}
      {%- assign tag_count = tag_posts | size -%}
      <a class="tag-cloud__item" href="{{ '/tags/' | append: tag.slug | append: '/' | relative_url }}" role="listitem">
        <span>{{ tag.name | escape }}</span>
        <small>{{ tag_count }}</small>
      </a>
    {%- endfor -%}
  </div>
</section>
