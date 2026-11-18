
(() => {
 const settings=document.createElement('div');settings.className='personal-settings';
 settings.innerHTML='<h3>자주 입는 10벌로 가볍게 시작</h3><p id="capsuleProgress"></p><label><input id="capsuleOnly" type="checkbox">자주 입는 옷만 추천받기</label><p class="note">옷 카드의 별을 눌러 선택하세요. 전체 옷을 등록하지 않아도 사용할 수 있어요.</p>';
 document.getElementById('closetGrid').before(settings);
 const feedback=document.createElement('div');feedback.id='personalFeedback';feedback.setAttribute('aria-live','polite');document.querySelector('.owned-outfit').append(feedback);
 window.dispatchEvent(new Event('wardrobe-personal-ready'));
})();
