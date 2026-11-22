(() => {
  const api = window.ondoApi;
  const types = {top:'상의', pants:'바지', skirt:'스커트', outer:'겉옷', shoes:'신발'};
  const styles = {casual:'캐주얼', formal:'포멀', sporty:'스포티', street:'스트릿', feminine:'페미닌'};
  const warmth = {light:'얇음', medium:'보통', warm:'따뜻함'};
  const mimeTypes = ['image/jpeg','image/png','image/webp'];
  // Order follows the 4 × 3 sample photo sheet, not the server's garment IDs.
  const sampleGarments = [
    ['크림 니트','top','#f3ecd9'], ['화이트 옥스퍼드 셔츠','top','#ffffff'],
    ['그레이 맨투맨','top','#808080'], ['블랙 반팔 티셔츠','top','#151515'],
    ['브라운 슬랙스','pants','#6b4423'], ['연청 데님 팬츠','pants','#a6c8e6'],
    ['블랙 조거 팬츠','pants','#151515'], ['카멜 울 코트','outer','#c19a6b'],
    ['네이비 바람막이','outer','#1f2a44'], ['브라운 더비 슈즈','shoes','#6b4423'],
    ['화이트 스니커즈','shoes','#ffffff'], ['블랙 방수 부츠','shoes','#151515']
  ];
  const pinterestSweatshirtPins = {
    men: {id:'181269954511628020', image:'45/da/9f/45da9ff1b4d2943478a66a3b292635ab.jpg'},
    women: {id:'138133913563107220', image:'7f/e3/5a/7fe35a134773b3de57a62278cfca2cfb.jpg'}
  };
  let user = null;
  let sessionVersion = 0;
  let recommendationRequest;
  let analysisRequest;
  let analysisPreviewUrl;
  let closetCount = null;
  const auth = $('accountDialog');
  const garmentDialog = $('garmentDialog');

  function node(tag, value, className) {
    const element = document.createElement(tag);
    if (value != null) element.textContent = String(value);
    if (className) element.className = className;
    return element;
  }

  function button(label, action) {
    const element = node('button', label);
    element.type = 'button';
    element.onclick = action;
    return element;
  }

  function sessionMessage(message = '') {
    $('sessionStatus').textContent = message;
    $('sessionStatus').hidden = !message;
  }

  function setUser(next) {
    user = next;
    sessionVersion++;
    closetCount = null;
    recommendationRequest?.abort();
    analysisRequest?.abort();
    clearAnalysis();
    if (garmentDialog.open) garmentDialog.close();
    $('clothes').replaceChildren();
    $('empty').hidden = true;
    $('uploadStatus').textContent = '';
    $('analysisStatus').textContent = '';
    $('recommendationArea').replaceChildren();
    $('accountButton').textContent = user ? (user.guest ? '게스트 체험 중' : user.nickname + ' 님') : '로그인';
    updateRecommendationButton();
    updateClosetHint();
  }

  function updateClosetHint() {
    $('closetDummyCount').textContent = !user
      ? '로그인하거나 게스트로 시작하면 코디를 추천받을 수 있어요.'
      : closetCount == null ? '내 옷으로 코디를 추천해요.' : '옷장에 저장된 옷 ' + closetCount + '벌';
  }

  function updateRecommendationButton() {
    $('generateOutfitBtn').disabled = !forecast || !!recommendationRequest;
  }

  function authFields(signup) {
    return '<label>아이디<input name="loginId" autocomplete="username" required' +
      (signup ? ' pattern="[a-zA-Z0-9_]{4,20}" title="영문·숫자·밑줄 4~20자"' : '') +
      ' maxlength="20"></label><label>비밀번호<input name="password" type="password" required maxlength="64"' +
      (signup ? ' minlength="8" autocomplete="new-password"' : ' autocomplete="current-password"') + '></label>' +
      (signup ? '<label>닉네임<input name="nickname" maxlength="20" required></label>' : '');
  }

  function displayError(error, status, form) {
    status.textContent = error.message;
    if (!form) return;
    form.querySelectorAll('.field-error').forEach(element => element.remove());
    for (const [key, message] of Object.entries(error.fieldErrors || {})) {
      form.elements.namedItem(key)?.closest('label')?.append(node('small', message, 'field-error'));
    }
  }

  function openAccount(signup = false) {
    const content = $('authBody');
    const status = $('authStatus');
    status.textContent = '';
    content.replaceChildren();
    if (user) {
      $('authTitle').textContent = user.guest ? '게스트 체험 중' : user.nickname + ' 님';
      content.append(button('로그아웃', () => {
        api.setToken(null);
        setUser(null);
        auth.close();
        tab(false);
      }));
    } else {
      $('authTitle').textContent = signup ? '회원가입' : '온도옷장 시작하기';
      const form = node('form', null, 'server-fields');
      form.innerHTML = authFields(signup);
      const submit = node('button', signup ? '가입하고 시작하기' : '로그인');
      form.append(submit);
      form.onsubmit = event => {
        event.preventDefault();
        const body = Object.fromEntries(new FormData(form));
        body.loginId = body.loginId.trim();
        if (signup) body.nickname = body.nickname.trim();
        authenticate(signup ? 'signup' : 'login', body, form);
      };
      content.append(form, button(signup ? '로그인으로 돌아가기' : '회원가입', () => openAccount(!signup)),
        button('게스트로 시작', showGuestPreferences));
    }
    if (!auth.open) auth.showModal();
  }

  function showGuestPreferences() {
    const guest = {gender: 'men', height: '', styles: [], tops: [], bottoms: [], outerwear: [], colors: []};
    const pages = [
      ['gender', '어떤 코디를 보고 싶나요?', {men:'남성 코디', women:'여성 코디'}],
      ['styles', '좋아하는 스타일을 골라주세요', styles],
      ['tops', '자주 입는 상의', ['티셔츠','셔츠','니트','맨투맨','후드티']],
      ['bottoms', '자주 입는 하의', ['데님','슬랙스','면바지','조거 팬츠','스커트']],
      ['outerwear', '즐겨 입는 겉옷', ['카디건','블레이저','바람막이','코트','패딩']],
      ['colors', '좋아하는 색감', {sage:'세이지 · 크림', slate:'슬레이트 · 미스트', rose:'테라코타 · 로즈', warm:'브라운 · 베이지', mono:'차콜 · 그레이'}],
      ['summary', '선택한 취향을 확인해 주세요']
    ];
    let index = 0;

    function draw() {
      const [key, title, options] = pages[index];
      $('authTitle').textContent = title;
      $('authStatus').textContent = '';
      const form = node('form', null, 'server-fields guest-entry');
      form.append(node('p', (index + 1) + ' / ' + pages.length + ' · 게스트 취향 설정'));
      if (options) {
        const group = node('fieldset', null, 'guest-styles');
        group.append(node('legend', index === 0 ? '코디 기준' : '여러 개 선택할 수 있어요'));
        const entries = Array.isArray(options) ? options.map(value => [value, value]) : Object.entries(options);
        for (const [value, label] of entries) {
          const choice = node('label', label);
          const input = node('input');
          Object.assign(input, {type:index === 0 ? 'radio' : 'checkbox', name:key, value,
            checked:index === 0 ? guest.gender === value : guest[key].includes(value)});
          input.onchange = () => {
            const selected = new FormData(form).getAll(key);
            guest[key] = index === 0 ? selected[0] : selected;
          };
          choice.prepend(input);
          group.append(choice);
        }
        form.append(group);
        if (index === 0) {
          const input = node('input');
          Object.assign(input, {type:'number', min:'100', max:'230', value:guest.height});
          input.oninput = () => guest.height = input.value;
          field(form, '키 (cm, 선택)', input);
        }
      } else {
        const selected = Object.entries(styles).filter(([value]) => guest.styles.includes(value)).map(([,label]) => label);
        form.append(node('p', '코디 기준 · ' + (guest.gender === 'women' ? '여성' : '남성') + ' 코디'));
        if (guest.height) form.append(node('p', '키 · ' + guest.height + 'cm'));
        form.append(node('p', '선호 스타일 · ' + (selected.join(', ') || '선택 없음')));
        const usual = [...guest.tops, ...guest.bottoms, ...guest.outerwear];
        if (usual.length) form.append(node('p', '자주 입는 옷 · ' + usual.join(', ')));
        if (guest.colors.length) form.append(node('p', '색상 · ' + guest.colors.map(value => pages[5][2][value]).join(', ')));
        form.append(node('p', '첫 번째 색상과 선택한 스타일을 코디 추천에 반영해요. 샘플 옷장으로 시작합니다.'));
      }
      form.append(node('button', options ? '다음' : '체험 시작'), button('이전', () => {
        if (index === 0) openAccount();
        else { index--; draw(); }
      }));
      form.onsubmit = event => {
        event.preventDefault();
        if (options) { index++; draw(); }
        else authenticate('guest', undefined, form, guest);
      };
      $('authBody').replaceChildren(form);
      form.querySelector('input,button').focus();
    }
    draw();
  }

  async function authenticate(mode, body, form, guest = null) {
    const content = $('authBody');
    const controls = [...content.querySelectorAll('button')];
    controls.push($('closeAccount'));
    controls.forEach(control => control.disabled = true);
    $('authStatus').textContent = '연결 중이에요…';
    try {
      const response = await api.request('/api/auth/' + mode, {method:'POST', body, authenticated:false});
      api.setToken(response.accessToken);
      localStorage.setItem('ondo.guestStyles', JSON.stringify(guest?.styles || []));
      if (guest) {
        $('gender').value = guest.gender;
        if (guest.colors.length) {
          $('colorTone').value = guest.colors[0];
          syncPalette();
        }
      }
      setUser(response.user);
      sessionMessage();
      auth.close();
      await refreshCloset();
    } catch (error) {
      displayError(error, $('authStatus'), form);
    } finally {
      controls.forEach(control => control.disabled = false);
    }
  }

  $('accountButton').onclick = () => openAccount();
  $('closeAccount').onclick = () => auth.close();
  auth.addEventListener('cancel', event => {
    if ($('closeAccount').disabled) event.preventDefault();
  });
  window.addEventListener('ondo-session-expired', () => {
    setUser(null);
    openAccount();
    $('authStatus').textContent = '로그인 시간이 만료됐어요. 다시 로그인해 주세요.';
  });

  function requireUser() {
    if (user) return true;
    openAccount();
    return false;
  }

  function safePhoto(url) {
    if (!url) return null;
    try {
      const parsed = new URL(url);
      return ['http:', 'https:'].includes(parsed.protocol) ? parsed.href : null;
    } catch { return null; }
  }

  function garmentPhoto(item) {
    const photo = node('div', null, 'outfit-garment-photo');
    const url = safePhoto(item.photo);
    const fallback = () => {
      const sampleIndex = user?.guest && !item.photo ? sampleGarments.findIndex(([name, type, color]) =>
        item.name === name && item.type === type && item.color?.toLowerCase() === color) : -1;
      if (sampleIndex < 0) {
        photo.replaceChildren(node('span', '사진 없음'));
        return;
      }
      const thumbnail = node('span', null, 'sample-garment-photo');
      thumbnail.setAttribute('role', 'img');
      thumbnail.setAttribute('aria-label', item.name + ' 예시 사진');
      thumbnail.style.backgroundPosition = `${sampleIndex % 4 * 100 / 3}% ${Math.floor(sampleIndex / 4) * 50}%`;
      photo.replaceChildren(thumbnail);
    };
    if (!url) fallback();
    else {
      const image = node('img');
      image.alt = item.name || types[item.type] || '옷 사진';
      image.addEventListener('error', fallback, {once:true});
      image.src = url;
      photo.append(image);
    }
    return photo;
  }

  async function refreshCloset() {
    if (!user) return;
    const version = sessionVersion;
    try {
      const items = await api.request('/api/clothes');
      if (version !== sessionVersion) return;
      closetCount = items.length;
      $('empty').hidden = !!items.length;
      $('clothes').replaceChildren(...items.map(item => {
        const card = node('article', null, 'server-garment');
        card.append(garmentPhoto(item), node('strong', item.name), node('p', types[item.type]),
          button('수정', () => editGarment(item)),
          button('삭제', async event => {
            if (!confirm(item.name + '을 옷장에서 삭제할까요?')) return;
            event.currentTarget.disabled = true;
            try {
              await api.request('/api/clothes/' + item.id, {method:'DELETE'});
              if (version !== sessionVersion) return;
              $('recommendationArea').replaceChildren();
              await refreshCloset();
            } catch (error) {
              if (version === sessionVersion) $('uploadStatus').textContent = error.message;
              card.querySelector('button:last-child').disabled = false;
            }
          }));
        return card;
      }));
      updateClosetHint();
    } catch (error) {
      if (version === sessionVersion) $('uploadStatus').textContent = error.message;
    }
  }

  function validateFile(file) {
    if (!file?.size || !mimeTypes.includes(file.type) || file.size > 15 * 1024 * 1024) {
      throw new Error('15MB 이하의 JPG, PNG, WebP 사진을 선택해 주세요.');
    }
  }

  async function jpegData(blob, rotation = 0) {
    const url = URL.createObjectURL(blob);
    try {
      const image = new Image();
      image.src = url;
      await image.decode();
      const scale = Math.min(1, 700 / Math.max(image.naturalWidth, image.naturalHeight));
      const w = Math.max(1, Math.round(image.naturalWidth * scale));
      const h = Math.max(1, Math.round(image.naturalHeight * scale));
      const canvas = document.createElement('canvas');
      const turned = rotation % 180 !== 0;
      canvas.width = turned ? h : w;
      canvas.height = turned ? w : h;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.translate(canvas.width / 2, canvas.height / 2);
      ctx.rotate(rotation * Math.PI / 180);
      ctx.drawImage(image, -w / 2, -h / 2, w, h);
      return canvas.toDataURL('image/jpeg', .86);
    } finally { URL.revokeObjectURL(url); }
  }

  function field(form, label, input) {
    const wrap = node('label', label);
    wrap.append(input);
    form.append(wrap);
    return input;
  }

  function select(name, values, value) {
    const element = node('select');
    element.name = name;
    element.required = true;
    element.add(new Option('선택해 주세요', ''));
    for (const [key, label] of Object.entries(values)) element.add(new Option(label, key));
    element.value = value ?? '';
    return element;
  }

  function garmentForm(item, save, {replace = false, draft = false} = {}) {
    const form = node('form', null, 'server-fields');
    const preview = node('img', null, 'server-preview');
    preview.alt = '등록할 옷 미리보기';
    const initialPhoto = item.photo?.startsWith('data:image/jpeg;base64,') ? item.photo : safePhoto(item.photo);
    preview.hidden = !initialPhoto;
    if (initialPhoto) preview.src = initialPhoto;
    form.append(preview);
    const name = node('input');
    Object.assign(name, {name:'name', value:item.name || '', required:true, maxLength:60});
    field(form, '이름', name);
    field(form, '종류', select('type', types, item.type));
    const color = node('input');
    Object.assign(color, {type:'color', name:'color', value:item.color || '#808080'});
    const colorField = field(form, '색상', color);
    if (draft && !item.color) {
      colorField.parentElement.append(node('small', '기본 회색으로 표시돼요. 저장 전에 색상을 확인해 주세요.', 'field-error'));
    }
    field(form, '보온성', select('warm', warmth, item.warm));
    field(form, '스타일', select('style', styles, item.style));
    for (const [key, label] of [['water','방수'],['grip','미끄럼 방지']]) {
      const input = node('input');
      Object.assign(input, {type:'checkbox', name:key, checked:!!item[key]});
      field(form, label, input);
    }

    const status = node('p', '', 'server-form-status');
    status.setAttribute('role', 'status');
    let photo = item.photo;
    let changedPhoto = false;
    let imageBusy = false;
    let file;
    let rotation = 0;
    async function transform(rotate = false) {
      if (imageBusy) return;
      imageBusy = true;
      form.querySelectorAll('button, input[type=file]').forEach(element => element.disabled = true);
      status.textContent = '사진을 처리하고 있어요…';
      try {
        const nextRotation = rotate ? (rotation + 90) % 360 : 0;
        let blob = file;
        if (!blob) {
          const response = await fetch(initialPhoto);
          if (!response.ok) throw new Error('사진을 불러오지 못했어요.');
          blob = await response.blob();
        }
        const transformedPhoto = await jpegData(blob, nextRotation);
        photo = transformedPhoto;
        rotation = nextRotation;
        changedPhoto = true;
        preview.src = photo;
        preview.hidden = false;
        status.textContent = '';
      } catch {
        status.textContent = '사진을 처리하지 못했어요. 다른 사진으로 다시 시도해 주세요.';
      } finally {
        form.querySelectorAll('button, input[type=file]').forEach(element => element.disabled = false);
        imageBusy = false;
      }
    }
    if (replace) {
      const input = node('input');
      Object.assign(input, {type:'file', accept:mimeTypes.join(',')});
      input.onchange = () => {
        try {
          validateFile(input.files[0]);
          file = input.files[0];
          transform();
        } catch (error) { status.textContent = error.message; }
      };
      field(form, '사진 교체', input);
      if (initialPhoto) form.append(button('90° 회전', () => transform(true)));
    }

    const submit = node('button', draft || !item.id ? '옷장에 저장' : '수정 저장');
    form.append(status, submit);
    let saving = false;
    const version = sessionVersion;
    async function submitGarment(event) {
      event?.preventDefault();
      if (saving || imageBusy || version !== sessionVersion || !form.reportValidity()) return false;
      const values = new FormData(form);
      const payload = {
        name:String(values.get('name')).trim(), type:values.get('type'), color:values.get('color'),
        warm:values.get('warm'), style:values.get('style'), water:values.has('water'), grip:values.has('grip')
      };
      if (!payload.name) {
        status.textContent = '옷 이름을 입력해 주세요.';
        return false;
      }
      if (changedPhoto || !item.id) {
        if (photo) payload.photo = photo;
      }
      if (draft) {
        payload.aiTagged = item.aiTagged === true;
        if (payload.warm === item.warm && Number.isInteger(item.warmScore)) payload.warmScore = item.warmScore;
      }
      saving = true;
      submit.disabled = true;
      status.textContent = '저장 중이에요…';
      try {
        await save(payload);
        if (version === sessionVersion) status.textContent = '저장했어요.';
        return true;
      } catch (error) {
        if (version === sessionVersion) displayError(error, status, form);
        return false;
      } finally {
        saving = false;
        submit.disabled = false;
      }
    }
    form.onsubmit = submitGarment;
    return {form, submit:submitGarment};
  }

  function editGarment(item) {
    const version = sessionVersion;
    const {form} = garmentForm(item, async payload => {
      await api.request('/api/clothes' + (item.id ? '/' + item.id : ''), {
        method:item.id ? 'PATCH' : 'POST', body:payload
      });
      if (version !== sessionVersion) return;
      garmentDialog.close();
      $('recommendationArea').replaceChildren();
      await refreshCloset();
    }, {replace:true});
    $('garmentTitle').textContent = item.id ? '옷 정보 수정' : '새 옷 등록';
    $('garmentEditor').replaceChildren(form);
    if (!garmentDialog.open) garmentDialog.showModal();
  }

  async function prepareUpload(file) {
    if (!requireUser()) return;
    const version = sessionVersion;
    try {
      validateFile(file);
      $('uploadStatus').textContent = '사진을 준비하고 있어요…';
      const photo = await jpegData(file);
      if (version !== sessionVersion) return;
      $('uploadStatus').textContent = '';
      editGarment({photo});
    } catch (error) {
      if (version === sessionVersion) $('uploadStatus').textContent = error.message;
    }
  }

  $('closeGarment').onclick = () => garmentDialog.close();
  $('refreshCloset').onclick = () => { if (requireUser()) refreshCloset(); };
  for (const id of ['closetNav','start','add']) {
    $(id).onclick = () => { tab(true); if (requireUser()) { refreshCloset(); checkAi(); } };
  }
  const drop = $('drop');
  const upload = drop.querySelector('input');
  upload.onchange = () => {
    const file = upload.files[0];
    upload.value = '';
    if (file) prepareUpload(file);
  };
  drop.ondragover = event => { event.preventDefault(); drop.classList.add('drag'); };
  drop.ondragleave = () => drop.classList.remove('drag');
  drop.ondrop = event => {
    event.preventDefault();
    drop.classList.remove('drag');
    if (event.dataTransfer.files[0]) prepareUpload(event.dataTransfer.files[0]);
  };
  const analysisForm = $('analysisForm');
  const analysisButton = analysisForm.querySelector('button[type=submit]');
  let drafts = [];

  function clearAnalysis() {
    if (analysisPreviewUrl) URL.revokeObjectURL(analysisPreviewUrl);
    analysisPreviewUrl = null;
    $('analysisPreview').hidden = true;
    $('analysisPreview').replaceChildren();
    $('analysisItems').replaceChildren();
    $('saveAllDrafts').hidden = true;
    drafts = [];
  }

  async function checkAi() {
    if (analysisRequest) return;
    const version = sessionVersion;
    try {
      const result = await api.request('/api/ai/health', {authenticated:false});
      if (version !== sessionVersion || analysisRequest) return;
      $('analysisStatus').textContent = result.ai === 'ok' ? 'AI 분석을 사용할 수 있어요.' : 'AI가 준비 중이에요. 옷 정보를 직접 등록할 수 있어요.';
    } catch (error) {
      if (version === sessionVersion && !analysisRequest) $('analysisStatus').textContent = error.message;
    }
  }

  analysisForm.onsubmit = async event => {
    event.preventDefault();
    if (!requireUser() || analysisRequest || drafts.some(draft => draft.saving)) return;
    const file = analysisForm.elements.file.files[0];
    try { validateFile(file); }
    catch (error) { $('analysisStatus').textContent = error.message; return; }
    clearAnalysis();
    const preview = $('analysisPreview');
    analysisPreviewUrl = URL.createObjectURL(file);
    const image = node('img');
    image.src = analysisPreviewUrl;
    image.alt = '분석할 원본 사진';
    preview.append(image);
    preview.hidden = false;
    const request = new AbortController();
    analysisRequest = request;
    const version = sessionVersion;
    const form = new FormData();
    form.append('file', file);
    analysisButton.disabled = true;
    $('analysisStatus').textContent = '사진을 분석하고 있어요. 첫 분석은 시간이 걸릴 수 있어요.';
    try {
      const mode = analysisForm.elements.mode.value;
      const result = await api.request('/api/clothes/analyze?mode=' + mode, {method:'POST', form, signal:request.signal});
      if (version !== sessionVersion) return;
      const warnings = [...(result.warnings || [])];
      if (result.skipped?.length) warnings.push('옷장 분류에서 제외한 항목 · ' + result.skipped.join(', '));
      if (!result.items?.length) warnings.push('등록할 옷을 찾지 못했어요.');
      let originalPhoto;
      if (mode === 'single' && result.items?.length === 1 && !result.items[0].draft.photo) {
        try {
          originalPhoto = await jpegData(file);
          warnings.push('배경을 제거하지 못해 원본 사진으로 저장할 수 있어요.');
        } catch {
          warnings.push('사진을 처리하지 못했어요. 옷장에 직접 등록해 주세요.');
        }
        if (version !== sessionVersion) return;
      }
      $('analysisStatus').textContent = warnings.join(' / ') || '분석한 옷을 확인하고 저장해 주세요.';
      for (const item of result.items || []) {
        if (item.box?.length === 4 && item.box.every(Number.isFinite)) {
          const [l,t,r,b] = item.box;
          const box = node('span', item.index, 'detected-garment');
          Object.assign(box.style, {left:l*100+'%', top:t*100+'%', width:(r-l)*100+'%', height:(b-t)*100+'%'});
          preview.append(box);
        }
        const card = node('article', null, 'server-panel');
        card.append(node('h4', '감지한 옷 ' + item.index + (item.ai?.type ? ' · ' + item.ai.type : '')));
        if (item.ai?.needsReview) card.append(node('p', '저장 전에 종류, 색상, 보온성과 스타일을 확인해 주세요.'));
        for (const warning of item.ai?.warnings || []) card.append(node('p', warning));
        const draft = {saving:false};
        const details = {...item.draft, photo:item.draft.photo || originalPhoto};
        const {form:editor, submit} = garmentForm(details, async payload => {
          draft.saving = true;
          try {
            if (item.draft.material) payload.material = item.draft.material;
            await api.request('/api/clothes', {method:'POST', body:payload});
            if (version !== sessionVersion) return;
            drafts = drafts.filter(entry => entry !== draft);
            card.replaceChildren(node('p', payload.name + ' · 저장 완료'));
            $('saveAllDrafts').hidden = !drafts.length;
            $('recommendationArea').replaceChildren();
            await refreshCloset();
          } finally { draft.saving = false; }
        }, {draft:true});
        draft.submit = submit;
        drafts.push(draft);
        card.append(editor);
        $('analysisItems').append(card);
      }
      $('saveAllDrafts').hidden = !drafts.length;
    } catch (error) {
      if (version === sessionVersion && error.name !== 'AbortError') {
        $('analysisStatus').textContent = error.code === 'AI_UNAVAILABLE'
          ? 'AI 서버에 연결할 수 없어요. 위의 옷 사진 추가에서 정보를 직접 입력할 수 있어요.' : error.message;
      }
    } finally {
      if (analysisRequest === request) {
        analysisRequest = null;
        analysisButton.disabled = false;
      }
    }
  };
  $('saveAllDrafts').onclick = async () => {
    const saveAll = $('saveAllDrafts');
    saveAll.disabled = true;
    analysisButton.disabled = true;
    try {
      for (const draft of [...drafts]) await draft.submit();
    } finally {
      saveAll.disabled = false;
      analysisButton.disabled = !!analysisRequest;
    }
  };

  function paletteMatch(items, colors) {
    function rgb(hex) {
      return hex.match(/[a-fA-F0-9]{2}/g).map(part => parseInt(part, 16));
    }
    const palette = colors.map(rgb);
    const values = items.filter(item => /^#[0-9a-f]{6}$/i.test(item.color));
    if (!values.length) return 0;
    return values.reduce((total, item) => {
      const channels = rgb(item.color);
      const distance = Math.min(...palette.map(target =>
        channels.reduce((sum, channel, i) => sum + (channel - target[i]) ** 2, 0)));
      return total + (1 - Math.sqrt(distance) / Math.sqrt(3 * 255 ** 2));
    }, 0) / values.length;
  }

  function appendPinterestPreview(preview, items, gender) {
    const top = items.find(item => item.type === 'top' && /그레이|회색|gray|grey/i.test(item.name) && /맨투맨|스웨트셔츠|sweatshirt/i.test(item.name));
    const jeans = items.find(item => item.type === 'pants' && /연청|light[ -]?(blue|wash)/i.test(item.name) && /데님|청바지|jeans|denim/i.test(item.name));
    const pin = top && jeans ? pinterestSweatshirtPins[gender] : null;
    const link = node('a', null, 'pinterest-preview');
    const query = [gender === 'women' ? '여자' : '남자', ...items.map(item => item.name), '코디'].join(' ');
    const search = new URL('https://www.pinterest.com/search/pins/');
    search.searchParams.set('q', query);
    Object.assign(link, {href:search.href, target:'_blank', rel:'noopener noreferrer'});
    const caption = node('span', '이 조합으로 Pinterest에서 보기 ↗', 'pinterest-caption');
    if (pin) {
      const image = node('img');
      Object.assign(image, {
        src:'https://i.pinimg.com/736x/' + pin.image,
        alt:'그레이 맨투맨과 연청 데님을 입은 착장 예시',
        referrerPolicy:'no-referrer'
      });
      link.href = 'https://www.pinterest.com/pin/' + pin.id + '/';
      caption.textContent = '그레이 맨투맨 · 연청 데님 착장 참고 · Pinterest ↗';
      const note = node('small', '상의와 바지 조합을 참고할 수 있어요.', 'pinterest-caption');
      link.append(image, caption, note);
      image.addEventListener('error', () => {
        image.remove();
        note.remove();
        link.href = search.href;
        caption.textContent = '이 조합으로 Pinterest에서 보기 ↗';
      }, {once:true});
    } else {
      link.append(caption);
    }
    preview.append(link);
  }

  function renderOutfits(result, palette, snapshot, gender) {
    const output = $('recommendationArea');
    output.replaceChildren();
    for (const warning of result.warnings || []) output.append(node('p', warning, 'server-warning'));
    const ordered = [...(result.recommendations || [])].map(item => ({
      item, score:item.score + 15 * paletteMatch(item.items || [], palette.colors)
    })).sort((a, b) => b.score - a.score).slice(0, 3);
    if (!ordered.length) {
      output.append(node('p', '이 조건에 맞는 조합을 찾지 못했어요. 옷을 추가하거나 장소·스타일을 바꿔 보세요.', 'recommend-placeholder'));
      return;
    }
    ordered.forEach(({item: outfit}, index) => {
      const card = node('article', null, 'result-grid result-no-reference server-result');
      const info = node('div', null, 'wardrobe-match-box');
      info.append(node('h3', '추천 코디 ' + (index + 1)),
        node('p', palette.paletteName + ' · 체감 ' + Math.round(snapshot.feel) + '°C'),
        node('p', outfit.reason));
      const dots = node('div', null, 'palette-dots result-palette');
      dots.setAttribute('aria-label', palette.paletteName);
      for (const color of palette.colors) {
        const swatch = node('span');
        swatch.style.background = color;
        dots.append(swatch);
      }
      info.append(dots);
      const stack = node('div', null, 'garment-stack');
      for (const item of outfit.items || []) {
        const row = node('div', null, 'garment-item');
        const text = node('div', null, 'garment-info');
        text.append(node('strong', item.name));
        row.append(garmentPhoto(item), text, node('span', types[item.type] || item.slot, 'garment-tag'));
        stack.append(row);
      }
      info.append(stack);
      const details = node('div', null, 'outfit-guidance');
      const layer = node('section');
      layer.append(node('h4', '겉옷 · 레이어드'), node('p', snapshot.layer));
      const shoes = node('section');
      shoes.append(node('h4', '오늘의 신발'), node('p', footwear[snapshot.condition]));
      details.append(layer, shoes);
      info.append(details);
      if (outfit.basis?.length) {
        const basis = node('details', null, 'outfit-basis');
        basis.append(node('summary', '추천 근거'));
        for (const entry of outfit.basis) basis.append(node('p', entry.kind + ' · ' + entry.text));
        info.append(basis);
      }
      card.append(info);
      if (index === 0 && outfit.items?.length) {
        card.classList.remove('result-no-reference');
        const reference = node('aside', null, 'result-reference outfit-preview');
        reference.append(node('h3', '추천 조합 미리보기'));
        appendPinterestPreview(reference, outfit.items, gender);
        const gallery = node('div', null, 'outfit-preview-grid');
        for (const item of outfit.items) {
          const figure = node('figure');
          figure.append(garmentPhoto(item), node('figcaption', item.name));
          gallery.append(figure);
        }
        reference.append(gallery);
        card.append(reference);
      }
      output.append(card);
    });
  }

  function invalidateRecommendation() {
    recommendationRequest?.abort();
    recommendationRequest = null;
    $('recommendationArea').replaceChildren();
    updateRecommendationButton();
  }
  window.addEventListener('ondo-weather-change', invalidateRecommendation);
  for (const id of ['colorTone','gender','purpose','styleMood','sensitivity','shuffleCapsule']) {
    $(id).addEventListener(id === 'shuffleCapsule' ? 'click' : 'change', invalidateRecommendation);
  }

  $('generateOutfitBtn').onclick = async () => {
    if (!requireUser() || !forecast || recommendationRequest) return;
    if (forecast.condition === 'unknown') {
      $('recommendationArea').replaceChildren(node('p', '강수 정보를 확인할 수 없어요. 날씨를 다시 불러와 주세요.', 'recommend-placeholder'));
      return;
    }
    const request = new AbortController();
    recommendationRequest = request;
    updateRecommendationButton();
    const version = sessionVersion;
    const tone = activeTone();
    const palette = capsules[capsuleTones.indexOf(tone)];
    const gender = $('gender').value;
    const sensitivity = Number($('sensitivity').value);
    let guestStyles = [];
    if (user.guest) {
      try { guestStyles = JSON.parse(localStorage.getItem('ondo.guestStyles')) || []; } catch {}
    }
    const preferredStyles = [...new Set([$('styleMood').value, ...guestStyles])].filter(value => Object.hasOwn(styles, value));
    const current = {...forecast, layer:clothingPlan(forecast, sensitivity).text};
    const sky = ['rain','snow'].includes(current.condition)
      ? current.condition : current.cloud >= 60 ? 'cloudy' : 'clear';
    $('recommendationArea').replaceChildren(node('p', '코디를 고르고 있어요…', 'recommend-placeholder'));
    try {
      const result = await api.request('/api/outfits/recommend', {method:'POST', signal:request.signal, body:{
        place:$('purpose').value, topK:5, preferredStyles,
        weather:{tempC:current.temp, feelsLikeC:current.feel+sensitivity, tempMinC:current.low, tempMaxC:current.high, sky,
          precipProb:current.probability == null ? undefined : current.probability / 100,
          windMs:Number.isFinite(current.wind) ? current.wind : undefined}
      }});
      if (version === sessionVersion && request === recommendationRequest) renderOutfits(result, palette, current, gender);
    } catch (error) {
      if (version === sessionVersion && request === recommendationRequest && error.name !== 'AbortError') {
        const message = error.code === 'EMPTY_CLOSET' ? '내 옷장에 옷을 먼저 등록해 주세요.'
          : error.code === 'AI_UNAVAILABLE' ? '추천 서버에 연결할 수 없어요. 잠시 후 다시 시도해 주세요.' : error.message;
        $('recommendationArea').replaceChildren(node('p', message, 'recommend-placeholder'));
      }
    } finally {
      if (recommendationRequest === request) {
        recommendationRequest = null;
        updateRecommendationButton();
      }
    }
  };

  async function restoreSession() {
    updateClosetHint();
    if (!api.token()) { openAccount(); return; }
    const version = sessionVersion;
    try {
      const account = await api.request('/api/me');
      if (version !== sessionVersion) return;
      setUser(account);
      await refreshCloset();
    } catch (error) {
      if (version === sessionVersion) sessionMessage(error.message);
    }
  }
  restoreSession();
})();
