(() => {
  const tabs = document.querySelector('.app-tabs');
  const outfitTab = get('outfitTab');
  const closetTab = get('closetTab');
  const overview = document.createElement('section');
  overview.id = 'shelfHome';
  overview.setAttribute('role', 'tabpanel');
  overview.setAttribute('aria-labelledby', 'overviewTab');
  overview.innerHTML = `
    <section class="editorial-hero" aria-labelledby="editorial-title">
      <div class="hero-graphic" aria-hidden="true"><i></i><i></i><i></i></div>
      <h1 id="editorial-title">오늘의 옷장</h1>
      <div class="hero-caption">
        <h2>오늘 입을 옷, 내 옷장에서.</h2>
        <p>날씨와 외출 장소에 맞춰 이미 가진 옷을 조합해 보세요.</p>
        <button type="button" class="overview-outfit editorial-link">오늘의 코디 열기</button>
      </div>
    </section>

    <section class="editorial-section" aria-labelledby="editorial-tools">
      <h2 id="editorial-tools" class="editorial-title">오늘 준비하기</h2>
      <div class="editorial-tools">
        <article>
          <div class="editorial-visual weather-visual">
            <span class="overview-temperature"></span>
            <span class="weather-indicator" aria-hidden="true"></span>
            <span class="overview-range"></span>
          </div>
          <h3>오늘의 날씨</h3>
          <p class="overview-source"></p>
          <button type="button" class="weather-settings editorial-link">날씨 설정</button>
        </article>
        <article>
          <div class="editorial-visual closet-visual">
            <span class="closet-graphic" aria-hidden="true"></span>
            <span class="overview-count" aria-live="polite"></span>
          </div>
          <h3>내 옷장</h3>
          <p>사진을 추가하고 종류와 스타일을 등록하세요.</p>
          <button type="button" class="overview-upload editorial-link">옷 사진 등록</button>
        </article>
        <article>
          <div class="editorial-visual outfit-visual" aria-hidden="true">
            <span></span><span>+</span><span></span>
          </div>
          <h3>오늘의 코디</h3>
          <p>날씨·장소·취향에 맞는 조합을 골라드려요.</p>
          <button type="button" class="overview-outfit editorial-link">코디 추천받기</button>
        </article>
      </div>
    </section>

    <section class="editorial-section editorial-help" aria-label="시작하기">
      <article>
        <h2>옷장을 채워요</h2>
        <p>자주 입는 상의와 하의부터 한 장씩 담아보세요.</p>
        <button type="button" class="overview-upload editorial-link">내 옷장 열기</button>
        <div class="editorial-note closet-note" aria-hidden="true">상의<span>+</span>하의</div>
      </article>
      <article>
        <h2>처음이라면</h2>
        <p>옷 등록부터 코디 추천까지 세 단계로 안내해요.</p>
        <button type="button" class="overview-guide editorial-link">사용법 보기</button>
        <div class="editorial-note guide-note" aria-hidden="true">등록<span>·</span>설정<span>·</span>추천</div>
      </article>
    </section>
  `;
  document.body.append(overview);
  document.body.append(tabs);
  document.body.classList.add('editorial-app');

  const overviewTab = document.createElement('button');
  overviewTab.id = 'overviewTab';
  overviewTab.textContent = '홈';
  overviewTab.setAttribute('role', 'tab');
  overviewTab.setAttribute('aria-controls', 'shelfHome');
  tabs.prepend(overviewTab);

  function showOverview() {
    hideGuide();
    overview.hidden = false;
    get('outfitPage').hidden = true;
    get('closetPage').hidden = true;
    overviewTab.setAttribute('aria-selected', 'true');
    outfitTab.setAttribute('aria-selected', 'false');
    closetTab.setAttribute('aria-selected', 'false');
    window.scrollTo(0, 0);
  }

  function hideOverview() {
    overview.hidden = true;
    overviewTab.setAttribute('aria-selected', 'false');
  }

  overviewTab.addEventListener('click', showOverview);
  outfitTab.addEventListener('click', hideOverview);
  closetTab.addEventListener('click', hideOverview);

  function openTab(tab, focusTarget) {
    tab.click();
    window.scrollTo(0, 0);
    focusTarget.focus({ preventScroll: true });
  }

  overview.querySelectorAll('.overview-upload').forEach(button => {
    button.onclick = () => openTab(closetTab, get('garmentPhoto'));
  });
  overview.querySelectorAll('.overview-outfit').forEach(button => {
    button.onclick = () => openTab(outfitTab, get('city'));
  });
  overview.querySelector('.weather-settings').onclick = () => openTab(outfitTab, get('city'));

  function updateWeatherSummary() {
    overview.querySelector('.overview-temperature').textContent = get('temperature').textContent;
    overview.querySelector('.weather-indicator').textContent = get('weatherIcon').textContent;
    overview.querySelector('.overview-range').textContent = '최저 · 최고 ' + get('range').textContent;
    overview.querySelector('.overview-source').textContent = get('weatherLabel').textContent;
  }

  const weatherCard = get('temperature').closest('.weather');
  new MutationObserver(updateWeatherSummary).observe(weatherCard, { childList: true, subtree: true });
  updateWeatherSummary();

  const closetGrid = get('closetGrid');
  const updateCount = () => {
    overview.querySelector('.overview-count').textContent = '등록 ' + closetGrid.children.length + '벌';
  };
  new MutationObserver(updateCount).observe(closetGrid, { childList: true });
  updateCount();

  const guideTab = document.createElement('button');
  guideTab.id = 'guideTab';
  guideTab.textContent = '사용법';
  guideTab.setAttribute('role', 'tab');
  guideTab.setAttribute('aria-controls', 'guidePage');
  tabs.append(guideTab);

  const guide = document.createElement('section');
  guide.id = 'guidePage';
  guide.setAttribute('role', 'tabpanel');
  guide.setAttribute('aria-labelledby', 'guideTab');
  guide.innerHTML = `
    <div class="guide-heading">
      <h1>온도옷장 사용법</h1>
      <p>옷 사진을 등록하고, 오늘 입을 조합을 찾아보세요.</p>
    </div>
    <ol class="guide-steps">
      <li><div><h2>내 옷장 채우기</h2><p>사진을 끌어다 놓고 이름, 종류, 보온성, 스타일을 입력해요. 상의와 하의를 함께 등록하면 조합을 만들기 쉬워요.</p></div><button type="button" data-guide-action="closet">옷 사진 등록</button></li>
      <li><div><h2>오늘의 조건 설정하기</h2><p>도시의 날씨를 불러오거나 직접 입력해요. 외출 장소와 선호 스타일도 선택할 수 있어요.</p></div><button type="button" data-guide-action="weather">날씨 설정</button></li>
      <li><div><h2>내 옷으로 코디 받기</h2><p>‘내 옷으로 코디 만들기’를 누르면 내가 등록한 옷이 표시돼요. 비슷한 참고 코디가 있으면 결과 아래에서 볼 수 있어요.</p></div><button type="button" data-guide-action="outfit">코디 화면 열기</button></li>
    </ol>
  `;
  overview.after(guide);

  function hideGuide() {
    guide.hidden = true;
    guideTab.setAttribute('aria-selected', 'false');
  }

  guideTab.onclick = () => {
    hideOverview();
    get('outfitPage').hidden = true;
    get('closetPage').hidden = true;
    outfitTab.setAttribute('aria-selected', 'false');
    closetTab.setAttribute('aria-selected', 'false');
    guide.hidden = false;
    guideTab.setAttribute('aria-selected', 'true');
    window.scrollTo(0, 0);
  };
  outfitTab.addEventListener('click', hideGuide);
  closetTab.addEventListener('click', hideGuide);
  overview.querySelector('.overview-guide').onclick = () => openTab(guideTab, guideTab);
  guide.querySelector('[data-guide-action="closet"]').onclick = () => openTab(closetTab, get('garmentPhoto'));
  guide.querySelector('[data-guide-action="weather"]').onclick = () => openTab(outfitTab, get('city'));
  guide.querySelector('[data-guide-action="outfit"]').onclick = () => openTab(outfitTab, get('buildOutfit'));

  for (const tab of [outfitTab, closetTab]) {
    tab.addEventListener('click', () => window.scrollTo(0, 0));
  }

  showOverview();
})();
