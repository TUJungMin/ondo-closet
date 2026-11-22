(() => {
  const panel = document.querySelector('.pinterest-panel');
  panel.hidden = true;
  panel.classList.add('outfit-reference');
  panel.innerHTML = '<h2>비슷한 코디 참고</h2><p class="muted">추천한 옷의 종류와 스타일을 기준으로 고른 Pinterest 예시예요.</p><div class="reference-result"></div>';

  const examples = [
    { gender: 'men', types: ['outer', 'bottom'], style: 'minimal', tags: /카디건|가디건|블랙 팬츠|cardigan/i, title: '브라운 카디건', pin: '422281209388500', image: '736x/f8/70/3f/f8703fdea69f342e13c999b097ef45f4.jpg' },
    { gender: 'men', types: ['outer'], style: 'formal', tags: /블레이저|울 재킷|blazer/i, title: '울 블레이저', pin: '927249010771235211', image: 'originals/ab/24/02/ab2402fc58249273697f6d9ec35704f2.jpg' },
    { gender: 'women', types: ['outer', 'skirt'], style: 'casual', tags: /카디건|가디건|스커트|cardigan/i, title: '데일리 카디건', pin: '21462535719575733', image: 'originals/dd/ed/26/dded26ef520a86e5e389023f9407997e.jpg' },
    { gender: 'women', types: ['outer', 'skirt'], style: 'minimal', tags: /베이지 니트|베이지 카디건|베이지 가디건/i, title: '베이지 니트 레이어드', pin: '409968372337296992', image: '564x/34/bd/87/34bd87918a4445254f8b814ed18c15df.jpg' },
    { gender: 'women', types: ['outer', 'bottom'], style: 'formal', tags: /체크 재킷|체크 자켓|블레이저|데님|blazer/i, title: '체크 재킷 레이어드', pin: '422281208644025', image: '736x/12/af/36/12af36081fb9cf6ea2da785640e5a990.jpg' }
  ];
  const age = get('ageGroup');
  try { age.value = window.wardrobeStorage.getItem('wardrobe.ageGroup') || ''; } catch {}
  age.addEventListener('change', () => {
    try { window.wardrobeStorage.setItem('wardrobe.ageGroup', age.value); } catch {}
  });

  const result = panel.querySelector('.reference-result');
  let picks = [];
  function renderReferences() {
    result.replaceChildren();
    panel.hidden = !picks.length;
    if (panel.hidden) return;

    const matches = examples.filter(example =>
      example.gender === get('gender').value &&
      picks.some(item => {
        const compatibleType = example.types.includes(item.type) ||
          (item.type === 'top' && example.tags.test(item.name));
        return compatibleType && (example.tags.test(item.name) || item.style === example.style);
      })
    );
    if (!matches.length) {
      result.textContent = '등록한 옷과 비슷한 참고 이미지를 찾지 못했어요.';
      return;
    }
    for (const example of matches) {
      const card = document.createElement('a');
      card.href = 'https://www.pinterest.com/pin/' + example.pin + '/';
      card.target = '_blank';
      card.rel = 'noopener noreferrer';
      const image = document.createElement('img');
      image.alt = example.title + ' 코디 예시';
      image.loading = 'lazy';
      image.onerror = () => { image.hidden = true; };
      image.src = 'https://i.pinimg.com/' + example.image;
      const caption = document.createElement('span');
      caption.textContent = example.title + ' · Pinterest';
      card.append(image, caption);
      result.append(card);
    }
  }
  window.addEventListener('wardrobe-outfit', event => {
    picks = event.detail;
    get('outfitStatus').after(panel);
    renderReferences();
  });
  get('gender').addEventListener('change', renderReferences);
})();
