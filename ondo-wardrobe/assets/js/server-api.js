(() => {
  const base = window.ONDO_API_BASE || 'http://localhost:8080';
  const key = 'ondo.token';
  let token = localStorage.getItem(key);
  window.ondoApi = {
    token: () => token,
    setToken(value) {
      token = value || null;
      if (token) localStorage.setItem(key, token);
      else localStorage.removeItem(key);
    },
    async request(path, {method = 'GET', body, form, authenticated = true, signal} = {}) {
      const requestToken = authenticated ? token : null;
      const headers = {};
      if (requestToken) headers.Authorization = 'Bearer ' + requestToken;
      let payload = form;
      if (body !== undefined) {
        headers['Content-Type'] = 'application/json';
        payload = JSON.stringify(body);
      }
      let response;
      try {
        response = await fetch(base + path, {method, headers, body: payload, signal});
      } catch (error) {
        if (error.name === 'AbortError') throw error;
        throw new Error('서버에 연결할 수 없어요. 서버와 실행 주소를 확인한 뒤 다시 시도해 주세요.');
      }
      const data = response.status === 204 ? null : await response.json().catch(() => null);
      if (!response.ok) {
        if (response.status === 401 && requestToken && token === requestToken) {
          this.setToken(null);
          window.dispatchEvent(new Event('ondo-session-expired'));
        }
        throw Object.assign(new Error(data?.message || '서버 요청에 실패했어요.'), {
          code: data?.code, status: response.status, fieldErrors: data?.fieldErrors || {}
        });
      }
      return data;
    }
  };
})();
