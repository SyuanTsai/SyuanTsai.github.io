---
layout: default
title: 關於
description: 關於 Syuan Tsai，以及這個用來整理開發實務、架構決策與學習紀錄的技術筆記網站。
permalink: /about/
---

<section class="about-page" aria-labelledby="about-title">
  <header class="page-intro">
    <p class="page-intro__eyebrow">About</p>
    <h1 id="about-title">關於這個網站</h1>
    <p>這裡整理我在開發、學習與問題排查過程中值得留下來的內容，讓處理過的問題能再次被找到、理解與使用。</p>
  </header>

  <section class="about-profile" aria-labelledby="about-profile-title">
    <div class="about-profile__identity">
      <p class="about-profile__name">Syuan Tsai</p>
      <p class="about-profile__role">C# Software Engineer</p>

      <dl class="about-profile__facts">
        <div>
          <dt>主要技術</dt>
          <dd>C# · .NET · SQL Server</dd>
        </div>
        <div>
          <dt>內容形式</dt>
          <dd>實作筆記 · 決策紀錄 · 問題排查</dd>
        </div>
      </dl>
    </div>

    <div class="about-profile__statement">
      <h2 id="about-profile-title">把解決過的問題，整理成下次能直接使用的答案。</h2>
      <p>我是 Syuan，一名以 C# 與 .NET 為主要技術棧的軟體工程師。這個網站不是完整的百科全書，而是持續整理的工作筆記：保留當時的情境、做法、限制與驗證結果。</p>
      <p>網站使用 Jekyll 與 GitHub Pages 建置，文章以 Markdown 維護，讓內容可以長期保存、版本化並持續更新。</p>
    </div>
  </section>

  <section class="about-section" aria-labelledby="about-topics-title">
    <div class="about-section__heading">
      <p>Topics</p>
      <h2 id="about-topics-title">這裡會記錄什麼</h2>
    </div>

    <div class="about-topic-grid">
      <article class="about-topic-card">
        <span class="about-topic-card__index" aria-hidden="true">01</span>
        <h3>開發實務</h3>
        <p>C#、.NET、SQL Server 與日常開發中可重複使用的實作方式。</p>
      </article>

      <article class="about-topic-card">
        <span class="about-topic-card__index" aria-hidden="true">02</span>
        <h3>架構與品質</h3>
        <p>設計取捨、程式碼審查、測試、效能與可維護性的思考紀錄。</p>
      </article>

      <article class="about-topic-card">
        <span class="about-topic-card__index" aria-hidden="true">03</span>
        <h3>問題排查</h3>
        <p>記錄問題現象、根本原因、修正方式與最後的驗證結果。</p>
      </article>

      <article class="about-topic-card">
        <span class="about-topic-card__index" aria-hidden="true">04</span>
        <h3>學習紀錄</h3>
        <p>課程、講座、文件閱讀，以及值得回頭查找的技術觀念。</p>
      </article>
    </div>
  </section>

  <section class="about-section about-principles" aria-labelledby="about-principles-title">
    <div class="about-principles__intro">
      <p class="about-section__eyebrow">Writing principles</p>
      <h2 id="about-principles-title">筆記整理原則</h2>
      <p>目標不是把內容寫得複雜，而是讓未來的自己與遇到相同問題的人能快速掌握關鍵。</p>
    </div>

    <ol class="about-principles__list">
      <li>
        <span aria-hidden="true">01</span>
        <div>
          <strong>先說明情境</strong>
          <p>交代環境、限制與問題邊界，避免把特定做法誤認為通用答案。</p>
        </div>
      </li>
      <li>
        <span aria-hidden="true">02</span>
        <div>
          <strong>步驟可以重現</strong>
          <p>保留必要指令、程式碼與驗證方式，讓結果可以被再次確認。</p>
        </div>
      </li>
      <li>
        <span aria-hidden="true">03</span>
        <div>
          <strong>記錄限制與更新</strong>
          <p>技術會改變；若條件或結論不同，會補充適用範圍與更新紀錄。</p>
        </div>
      </li>
    </ol>
  </section>

  <section class="about-links" aria-labelledby="about-links-title">
    <div>
      <p class="about-section__eyebrow">Explore</p>
      <h2 id="about-links-title">繼續閱讀</h2>
      <p>從文章列表查看目前公開的開發與學習筆記，也可以透過公開平台了解其他內容。</p>
    </div>

    <nav class="about-links__actions" aria-label="關於頁面連結">
      <a class="about-link about-link--primary" href="{{ '/articles/' | relative_url }}">瀏覽全部文章 <span aria-hidden="true">→</span></a>
      <a class="about-link" href="https://github.com/SyuanTsai" rel="me">GitHub</a>
      <a class="about-link" href="https://www.linkedin.com/in/tw-syuan" rel="me">LinkedIn</a>
    </nav>
  </section>
</section>
