---
layout: default
title: 分類
description: 依文章主要領域瀏覽本站內容；每篇文章只屬於一個主分類。
permalink: /categories/
---

<section class="discovery-page" aria-labelledby="categories-title">
  <header class="page-intro">
    <p class="page-intro__eyebrow">Categories</p>
    <h1 id="categories-title">{{ page.title | escape }}</h1>
    <p>{{ page.description | escape }}</p>
  </header>

  <nav class="discovery-nav" aria-label="文章探索方式">
    <a href="{{ '/categories/' | relative_url }}" aria-current="page">所有分類</a>
    <a href="{{ '/tags/' | relative_url }}">所有標籤</a>
    <a href="{{ '/archives/' | relative_url }}">月份封存</a>
    <a href="{{ '/search/' | relative_url }}">搜尋文章</a>
  </nav>

  <div class="taxonomy-grid">
    {%- for category in site.data.taxonomy.categories -%}
      {%- assign category_posts = site.categories[category.slug] -%}
      {%- assign category_count = category_posts | size -%}
      <a class="taxonomy-card" href="{{ '/categories/' | append: category.slug | append: '/' | relative_url }}">
        <span class="taxonomy-card__count">{{ category_count }} 篇文章</span>
        <h2>{{ category.name | escape }}</h2>
        <p>{{ category.description | escape }}</p>
        <span class="taxonomy-card__action">查看分類 <span aria-hidden="true">→</span></span>
      </a>
    {%- endfor -%}
  </div>
</section>
