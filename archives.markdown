---
layout: default
title: 月份封存
description: 依文章發布年月瀏覽本站的歷史內容。
permalink: /archives/
---

<section class="discovery-page" aria-labelledby="archives-title">
  <header class="page-intro">
    <p class="page-intro__eyebrow">Archives</p>
    <h1 id="archives-title">{{ page.title | escape }}</h1>
    <p>{{ page.description | escape }}</p>
  </header>

  <nav class="discovery-nav" aria-label="文章探索方式">
    <a href="{{ '/categories/' | relative_url }}">所有分類</a>
    <a href="{{ '/tags/' | relative_url }}">所有標籤</a>
    <a href="{{ '/archives/' | relative_url }}" aria-current="page">月份封存</a>
    <a href="{{ '/search/' | relative_url }}">搜尋文章</a>
  </nav>

  {%- assign years = site.posts | group_by_exp: "post", "post.date | date: '%Y'" -%}
  {%- if years != empty -%}
    <div class="archive-groups">
      {%- for year in years -%}
        <section class="archive-group" aria-labelledby="archive-year-{{ year.name }}">
          <h2 id="archive-year-{{ year.name }}">{{ year.name }} 年</h2>
          {%- assign months = year.items | group_by_exp: "post", "post.date | date: '%m'" -%}
          <div class="archive-months">
            {%- for month in months -%}
              <a href="{{ '/archives/' | append: year.name | append: '/' | append: month.name | append: '/' | relative_url }}">
                <span>{{ month.name }} 月</span>
                <small>{{ month.items | size }} 篇文章</small>
              </a>
            {%- endfor -%}
          </div>
        </section>
      {%- endfor -%}
    </div>
  {%- else -%}
    <div class="discovery-empty" role="status">
      <h2>目前沒有文章</h2>
      <p>文章發布後會依年月自動顯示在這裡。</p>
    </div>
  {%- endif -%}
</section>
