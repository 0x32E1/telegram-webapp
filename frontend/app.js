(() => {
  const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.ready();
    tg.expand();
    if (tg.setHeaderColor) { try { tg.setHeaderColor('#241416'); } catch (e) {} }
  }
  const initData = tg && tg.initData ? tg.initData : '';

  const API = {
    async get(path) {
      const res = await fetch(path);
      if (!res.ok) throw await res.json().catch(() => ({ detail: res.statusText }));
      return res.json();
    },
    async post(path, body) {
      const res = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      if (!res.ok) throw await res.json().catch(() => ({ detail: res.statusText }));
      return res.json();
    },
  };

  const UI = {
    ru: {
      steps: ['Услуга', 'Мастер', 'Дата', 'Время', 'Подтверждение'],
      choose_service: 'Выберите услугу', choose_employee: 'Выберите мастера',
      choose_date: 'Выберите дату', choose_time: 'Выберите время',
      confirm_title: 'Проверьте запись', continue_: 'Продолжить', back: 'Назад',
      confirm: 'Подтвердить запись', my_bookings: 'Мои записи', bookings_title: 'Ваши записи',
      no_slots: 'На эту дату нет свободных окон', service_label: 'Услуга', master_label: 'Мастер',
      date_label: 'Дата', time_label: 'Время', total_label: 'Итого',
      success_title: 'Запись подтверждена!', success_sub: 'Ждём вас в салоне. Напомним за час до визита.',
      done: 'Готово', empty_bookings: 'У вас пока нет активных записей', cancel_booking: 'Отменить запись',
      cancelled: 'Запись отменена', min: 'мин', close: 'Закрыть', error: 'Что-то пошло не так, попробуйте ещё раз',
      slot_taken: 'Это время уже заняли — выберите другое',
      weekdays: ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'],
    },
    en: {
      steps: ['Service', 'Specialist', 'Date', 'Time', 'Confirm'],
      choose_service: 'Choose a service', choose_employee: 'Choose a specialist',
      choose_date: 'Choose a date', choose_time: 'Choose a time',
      confirm_title: 'Review your booking', continue_: 'Continue', back: 'Back',
      confirm: 'Confirm booking', my_bookings: 'My bookings', bookings_title: 'Your bookings',
      no_slots: 'No free slots on this date', service_label: 'Service', master_label: 'Specialist',
      date_label: 'Date', time_label: 'Time', total_label: 'Total',
      success_title: 'Booking confirmed!', success_sub: "We'll see you at the salon. Reminder sent 1 hour before.",
      done: 'Done', empty_bookings: "You don't have any active bookings", cancel_booking: 'Cancel booking',
      cancelled: 'Booking cancelled', min: 'min', close: 'Close', error: 'Something went wrong, try again',
      slot_taken: 'That time just got taken — pick another',
      weekdays: ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'],
    },
    uz: {
      steps: ['Xizmat', 'Usta', 'Sana', 'Vaqt', 'Tasdiqlash'],
      choose_service: 'Xizmatni tanlang', choose_employee: 'Ustani tanlang',
      choose_date: 'Sanani tanlang', choose_time: 'Vaqtni tanlang',
      confirm_title: 'Yozuvni tekshiring', continue_: 'Davom etish', back: 'Orqaga',
      confirm: 'Yozuvni tasdiqlash', my_bookings: 'Yozuvlarim', bookings_title: 'Sizning yozuvlaringiz',
      no_slots: 'Bu sanada bo\'sh vaqt yo\'q', service_label: 'Xizmat', master_label: 'Usta',
      date_label: 'Sana', time_label: 'Vaqt', total_label: 'Jami',
      success_title: 'Yozuv tasdiqlandi!', success_sub: 'Salonda kutamiz. Tashrifdan 1 soat oldin eslatamiz.',
      done: 'Tayyor', empty_bookings: "Sizda hozircha faol yozuvlar yo'q", cancel_booking: 'Yozuvni bekor qilish',
      cancelled: 'Yozuv bekor qilindi', min: 'daq', close: 'Yopish', error: 'Xatolik yuz berdi, qayta urinib ko\'ring',
      slot_taken: 'Bu vaqt band bo\'ldi — boshqasini tanlang',
      weekdays: ['Dush','Sesh','Chor','Pay','Jum','Shan','Yak'],
    },
  };

  const state = {
    lang: 'ru',
    step: 0, // 0..4, 4 = confirm, 5 = success
    services: [],
    employees: [],
    slots: [],
    selection: { service: null, employee: null, date: null, time: null },
    bootstrapped: false,
  };

  const el = (id) => document.getElementById(id);
  const ticketBody = el('ticketBody');
  const stepTitle = el('stepTitle');
  const stepNum = el('stepNum');
  const primaryBtn = el('primaryBtn');
  const backBtn = el('backBtn');
  const bookingsBtn = el('bookingsBtn');
  const toast = el('toast');

  function L() { return UI[state.lang]; }
  function fmtPrice(n) { return n.toLocaleString('ru-RU').replace(/,/g, ' ') + ' UZS'; }

  function showToast(msg) {
    toast.textContent = msg;
    toast.classList.remove('hidden');
    setTimeout(() => toast.classList.add('hidden'), 2600);
  }

  function setLangButtons() {
    document.querySelectorAll('.lang-switch button').forEach((b) => {
      b.classList.toggle('active', b.dataset.lang === state.lang);
    });
  }

  async function init() {
    setLangButtons();
    document.querySelectorAll('.lang-switch button').forEach((b) => {
      b.addEventListener('click', async () => {
        if (b.dataset.lang === state.lang) return;
        state.lang = b.dataset.lang;
        setLangButtons();
        try { await API.post('/api/lang', { init_data: initData, lang: state.lang }); } catch (e) {}
        render();
      });
    });
    backBtn.addEventListener('click', onBack);
    primaryBtn.addEventListener('click', onPrimary);
    bookingsBtn.addEventListener('click', openBookings);
    el('closeBookings').addEventListener('click', closeBookings);

    try {
      const boot = await API.get(`/api/bootstrap?init_data=${encodeURIComponent(initData)}`);
      state.lang = boot.lang;
      state.services = boot.services;
      state.bootstrapped = true;
      setLangButtons();
      render();
    } catch (e) {
      ticketBody.innerHTML = `<div class="empty-state">Auth error: ${(e && e.detail) || 'unknown'}</div>`;
    }
  }

  function render() {
    const t = L();
    stepTitle.textContent = [t.choose_service, t.choose_employee, t.choose_date, t.choose_time, t.confirm_title][state.step] || t.success_title;
    stepNum.textContent = String(Math.min(state.step + 1, 5)).padStart(2, '0');
    backBtn.style.visibility = state.step === 0 ? 'hidden' : 'visible';
    primaryBtn.textContent = state.step === 4 ? t.confirm : (state.step === 5 ? t.done : t.continue_);

    if (state.step === 0) renderServices();
    else if (state.step === 1) renderEmployees();
    else if (state.step === 2) renderDates();
    else if (state.step === 3) renderTimes();
    else if (state.step === 4) renderConfirm();
    else if (state.step === 5) renderSuccess();
  }

  function renderServices() {
    const t = L();
    ticketBody.innerHTML = '';
    state.services.forEach((s) => {
      const row = document.createElement('div');
      row.className = 'option-row' + (state.selection.service && state.selection.service.id === s.id ? ' selected' : '');
      row.innerHTML = `
        <div class="opt-main">
          <div class="opt-title">${s['name_' + state.lang]}</div>
          <div class="opt-sub">${s.duration_min} ${t.min}</div>
        </div>
        <div class="opt-price">${fmtPrice(s.price)}</div>`;
      row.addEventListener('click', () => {
        state.selection.service = s;
        state.selection.employee = null;
        renderServices();
        primaryBtn.disabled = false;
      });
      ticketBody.appendChild(row);
    });
    primaryBtn.disabled = !state.selection.service;
  }

  async function renderEmployees() {
    ticketBody.innerHTML = '<div class="loading-row">···</div>';
    primaryBtn.disabled = true;
    try {
      state.employees = await API.get(`/api/employees?service_id=${state.selection.service.id}&init_data=${encodeURIComponent(initData)}`);
    } catch (e) {
      ticketBody.innerHTML = `<div class="empty-state">${L().error}</div>`;
      return;
    }
    ticketBody.innerHTML = '';
    state.employees.forEach((emp) => {
      const row = document.createElement('div');
      row.className = 'option-row' + (state.selection.employee && state.selection.employee.id === emp.id ? ' selected' : '');
      row.innerHTML = `
        <div class="opt-main">
          <div class="opt-title">${emp.name}</div>
          <div class="opt-sub">${emp['specialty_' + state.lang]}</div>
        </div>`;
      row.addEventListener('click', () => {
        state.selection.employee = emp;
        renderEmployees();
      });
      ticketBody.appendChild(row);
    });
    primaryBtn.disabled = !state.selection.employee;
  }

  function renderDates() {
    const t = L();
    ticketBody.innerHTML = '';
    const grid = document.createElement('div');
    grid.className = 'date-grid';
    const today = new Date();
    for (let i = 0; i < 14; i++) {
      const d = new Date(today);
      d.setDate(d.getDate() + i);
      const iso = d.toISOString().slice(0, 10);
      const cell = document.createElement('div');
      cell.className = 'date-cell' + (state.selection.date === iso ? ' selected' : '');
      const dow = t.weekdays[(d.getDay() + 6) % 7];
      cell.innerHTML = `<span class="dow">${dow}</span><span class="dnum">${String(d.getDate()).padStart(2, '0')}.${String(d.getMonth() + 1).padStart(2, '0')}</span>`;
      cell.addEventListener('click', () => {
        state.selection.date = iso;
        state.selection.time = null;
        renderDates();
        primaryBtn.disabled = false;
      });
      grid.appendChild(cell);
    }
    ticketBody.appendChild(grid);
    primaryBtn.disabled = !state.selection.date;
  }

  async function renderTimes() {
    ticketBody.innerHTML = '<div class="loading-row">···</div>';
    primaryBtn.disabled = true;
    try {
      state.slots = await API.get(
        `/api/slots?employee_id=${state.selection.employee.id}&service_id=${state.selection.service.id}&date=${state.selection.date}&init_data=${encodeURIComponent(initData)}`
      );
    } catch (e) {
      ticketBody.innerHTML = `<div class="empty-state">${L().error}</div>`;
      return;
    }
    if (!state.slots.length) {
      ticketBody.innerHTML = `<div class="empty-state">${L().no_slots}</div>`;
      return;
    }
    const grid = document.createElement('div');
    grid.className = 'time-grid';
    state.slots.forEach((s) => {
      const cell = document.createElement('div');
      cell.className = 'time-cell' + (state.selection.time === s ? ' selected' : '');
      cell.textContent = s;
      cell.addEventListener('click', () => {
        state.selection.time = s;
        renderTimes();
        primaryBtn.disabled = false;
      });
      grid.appendChild(cell);
    });
    ticketBody.innerHTML = '';
    ticketBody.appendChild(grid);
    primaryBtn.disabled = !state.selection.time;
  }

  function renderConfirm() {
    const t = L();
    const s = state.selection.service;
    ticketBody.innerHTML = `
      <div class="summary-list">
        <div class="summary-item"><span class="label">${t.service_label}</span><span class="value">${s['name_' + state.lang]}</span></div>
        <div class="summary-item"><span class="label">${t.master_label}</span><span class="value">${state.selection.employee.name}</span></div>
        <div class="summary-item"><span class="label">${t.date_label}</span><span class="value">${state.selection.date}</span></div>
        <div class="summary-item"><span class="label">${t.time_label}</span><span class="value">${state.selection.time}</span></div>
        <div class="summary-total"><span class="label">${t.total_label}</span><span class="value">${fmtPrice(s.price)}</span></div>
      </div>`;
    primaryBtn.disabled = false;
  }

  function renderSuccess() {
    const t = L();
    backBtn.style.visibility = 'hidden';
    ticketBody.innerHTML = `
      <div class="success-wrap">
        <div class="success-icon">✓</div>
        <div class="step-title" style="font-size:19px">${t.success_title}</div>
        <p class="opt-sub" style="margin-top:8px">${t.success_sub}</p>
        <div class="success-code">#${state.selection.bookingId || '------'}</div>
      </div>`;
  }

  function onBack() {
    if (state.step === 0) return;
    state.step -= 1;
    render();
  }

  async function onPrimary() {
    if (state.step < 3) {
      state.step += 1;
      render();
      return;
    }
    if (state.step === 3) {
      state.step = 4;
      render();
      return;
    }
    if (state.step === 4) {
      primaryBtn.disabled = true;
      try {
        const booking = await API.post('/api/bookings', {
          init_data: initData,
          service_id: state.selection.service.id,
          employee_id: state.selection.employee.id,
          date: state.selection.date,
          time: state.selection.time,
        });
        state.selection.bookingId = booking.id;
        state.step = 5;
        render();
        if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
      } catch (e) {
        if (e && e.detail === 'slot no longer available') {
          showToast(L().slot_taken);
          state.step = 3;
          render();
        } else {
          showToast(L().error);
          primaryBtn.disabled = false;
        }
      }
      return;
    }
    if (state.step === 5) {
      // reset for a new booking
      state.step = 0;
      state.selection = { service: null, employee: null, date: null, time: null };
      render();
    }
  }

  async function openBookings() {
    const t = L();
    el('bookingsTitle').textContent = t.bookings_title;
    const list = el('bookingsList');
    list.innerHTML = '<div class="loading-row">···</div>';
    el('bookingsOverlay').classList.remove('hidden');
    try {
      const bookings = await API.get(`/api/my-bookings?init_data=${encodeURIComponent(initData)}`);
      if (!bookings.length) {
        list.innerHTML = `<div class="empty-state">${t.empty_bookings}</div>`;
        return;
      }
      list.innerHTML = '';
      bookings.forEach((b) => {
        const card = document.createElement('div');
        card.className = 'booking-card';
        card.innerHTML = `
          <div class="bk-top"><span>${b['name_' + state.lang]}</span><span>${fmtPrice(b.price)}</span></div>
          <div class="bk-meta">${b.employee_name} · ${b.date} · ${b.time}</div>
          <button class="bk-cancel">${t.cancel_booking}</button>`;
        card.querySelector('.bk-cancel').addEventListener('click', async () => {
          try {
            await API.post(`/api/bookings/${b.id}/cancel`, { init_data: initData });
            showToast(t.cancelled);
            openBookings();
          } catch (e) {
            showToast(t.error);
          }
        });
        list.appendChild(card);
      });
    } catch (e) {
      list.innerHTML = `<div class="empty-state">${t.error}</div>`;
    }
  }

  function closeBookings() {
    el('bookingsOverlay').classList.add('hidden');
  }

  init();
})();
