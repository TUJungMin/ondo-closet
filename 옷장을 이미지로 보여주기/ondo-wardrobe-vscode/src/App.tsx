import { ChangeEvent, ReactNode, useRef, useState } from 'react'

type Tab = 'home' | 'closet' | 'add' | 'calendar'
type Category = 'outer' | 'top' | 'bottom' | 'shoes'

type ClothingItem = {
  id: number
  name: string
  category: Category
  image: string
  color: string
}

const categories: { id: Category; label: string; description: string }[] = [
  { id: 'outer', label: '겉옷', description: '재킷 · 코트 · 가디건' },
  { id: 'top', label: '상의', description: '티셔츠 · 셔츠 · 니트' },
  { id: 'bottom', label: '하의', description: '팬츠 · 스커트' },
  { id: 'shoes', label: '신발', description: '스니커즈 · 구두' },
]

const starterItems: ClothingItem[] = [
  { id: 1, name: '아이보리 니트', category: 'top', image: '/assets/e8c08.png', color: '아이보리' },
  { id: 2, name: '스트레이트 데님', category: 'bottom', image: '/assets/49620.png', color: '데님 블루' },
  { id: 3, name: '화이트 스니커즈', category: 'shoes', image: '/assets/d7101.png', color: '화이트' },
]

const wardrobeSymbols: Record<Category, string> = {
  outer: '/assets/outer-symbol-v2.png',
  top: '/assets/top-symbol-v2.png',
  bottom: '/assets/bottom-symbol-v2.png',
  shoes: '/assets/shoes-symbol-v2.png',
}

function Icon({ children, size = 20 }: { children: ReactNode; size?: number }) {
  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {children}
    </svg>
  )
}

function Header({ active, onChange }: { active: Tab; onChange: (tab: Tab) => void }) {
  const navItems: { id: Tab; label: string }[] = [
    { id: 'home', label: '오늘의 추천' },
    { id: 'closet', label: '내 옷장' },
    { id: 'add', label: '옷 등록·분석' },
    { id: 'calendar', label: '캘린더' },
  ]

  return (
    <header className="site-header">
      <button className="brand" onClick={() => onChange('home')} aria-label="온도옷장 홈">
        온도옷장
      </button>
      <nav aria-label="주요 메뉴">
        {navItems.map((item) => (
          <button
            key={item.id}
            className={`nav-link ${active === item.id ? 'active' : ''}`}
            onClick={() => onChange(item.id)}
          >
            {item.label}
          </button>
        ))}
      </nav>
      <button className="location-button">
        <Icon size={16}>
          <path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z" />
          <circle cx="12" cy="10" r="2.5" />
        </Icon>
        광주광역시
        <span>변경</span>
      </button>
    </header>
  )
}

function Footer() {
  return (
    <footer>
      <strong>온도옷장</strong>
      <span>날씨에 맞는, 나다운 옷차림</span>
      <span className="footer-weather">광주 18°C · 맑음 기준의 추천입니다.</span>
    </footer>
  )
}

function Home({ onOpenCloset }: { onOpenCloset: () => void }) {
  return (
    <>
      <section className="home-hero">
        <div className="hero-shade" />
        <div className="weather-card">
          <p>광주광역시</p>
          <strong>18°</strong>
          <span>맑음</span>
          <div className="forecast">
            <b>오후에도 맑은 하늘이에요.</b>
            <div>
              <span>지금<br /><b>18°</b></span>
              <span>12시<br /><b>20°</b></span>
              <span>14시<br /><b>21°</b></span>
              <span>16시<br /><b>19°</b></span>
            </div>
          </div>
          <small>일교차에 맞춰 겉옷을 챙겨요.</small>
        </div>
        <div className="hero-copy">
          <span>오늘의 날씨, 오늘의 옷차림</span>
          <h1>햇살 좋은 오늘,<br />가볍게 나가볼까요?</h1>
          <p>낮에는 가볍게, 아침저녁에는 얇은 겉옷을.<br />일교차에 맞춰 벗기 쉬운 옷을 추천해요.</p>
          <div className="weather-summary"><b>18°C · 맑음</b><span>가벼운 재킷 / 얇은 니트 / 스니커즈</span></div>
          <button className="primary-button" onClick={onOpenCloset}>내 옷장에서 코디 보기 <span>→</span></button>
        </div>
      </section>
      <main className="home-content">
        <div className="section-heading">
          <div><span className="eyebrow">TODAY'S CLOSET</span><h2>오늘 꺼내 입기 좋은 옷</h2></div>
          <p>보유 중인 옷을 바탕으로 골랐어요</p>
        </div>
        <div className="recommendation-grid">
          {starterItems.map((item, index) => (
            <article className="recommendation-card" key={item.id}>
              <div className="recommendation-image"><img src={item.image} alt={item.name} /></div>
              <div><span>0{index + 1} · {categories.find((c) => c.id === item.category)?.label}</span><h3>{item.name}</h3><p>{index === 0 ? '아침저녁 쌀쌀한 공기에 가볍게 겹쳐 입어요.' : index === 1 ? '어떤 상의에도 편안하게 어울리는 기본 아이템이에요.' : '오래 걸어도 편안한 오늘의 마무리예요.'}</p></div>
            </article>
          ))}
        </div>
      </main>
    </>
  )
}

function Closet({
  items,
  onAdd,
}: {
  items: ClothingItem[]
  onAdd: (category?: Category) => void
}) {
  const [filter, setFilter] = useState<Category | 'all'>('all')
  const total = items.length

  return (
    <main className="closet-page">
      <section className="closet-intro">
        <div>
          <span className="eyebrow">MY WARDROBE</span>
          <h1>내 옷장</h1>
          <p>내가 가진 옷을 한눈에 보고, 오늘 입을 옷을 꺼내보세요.</p>
        </div>
        <div className="closet-stats">
          <div><strong>{total}</strong><span>전체 아이템</span></div>
          <div><strong>{new Set(items.map((item) => item.category)).size}</strong><span>채워진 칸</span></div>
          <button className="primary-button" onClick={() => onAdd()}>+ 새 옷 등록</button>
        </div>
      </section>

      <section className="closet-toolbar">
        <div className="filter-tabs" aria-label="옷 종류 필터">
          <button className={filter === 'all' ? 'active' : ''} onClick={() => setFilter('all')}>전체</button>
          {categories.map((category) => (
            <button className={filter === category.id ? 'active' : ''} key={category.id} onClick={() => setFilter(category.id)}>
              {category.label}
            </button>
          ))}
        </div>
        <span>최근 등록순 <b>⌄</b></span>
      </section>

      <section className="wardrobe-shell" aria-label="카테고리별 내 옷장">
        <img
          className="wardrobe-image"
          src="/assets/wardrobe-shoe-grid-v2.png"
          alt="세 개의 옷걸이 칸과 봉 없이 2열 3행 선반으로 구성된 신발장이 있는 옷장"
        />
        <div className="wardrobe-top">
          <div className="wardrobe-brand">ONDO</div>
          <span>MY EVERYDAY WARDROBE</span>
        </div>
        <div className="wardrobe-interior">
          {categories
            .map((category) => {
              const categoryItems = items.filter((item) => item.category === category.id)
              const visibleSlotCount = category.id === 'shoes' ? 6 : 5
              const visibleItems = categoryItems.slice(-visibleSlotCount)
              const slots = Array.from({ length: visibleSlotCount }, (_, index) => visibleItems[index])
              return (
                <article
                  className={`closet-compartment ${category.id === 'shoes' ? 'shoe-compartment' : ''} ${filter !== 'all' && filter !== category.id ? 'filtered-out' : ''}`}
                  key={category.id}
                >
                  <div className="compartment-label">
                    <div><span>{category.label}</span><small>{category.description}</small></div>
                    <div className="category-total">
                      <b>{categoryItems.length}</b>
                      {categoryItems.length > visibleSlotCount && <small>최근 {visibleSlotCount}개 표시</small>}
                    </div>
                  </div>
                  {category.id === 'shoes' ? (
                    <div className="shoe-grid">
                      {slots.map((item, index) =>
                        item ? (
                          <button className="shoe-slot filled" key={item.id} title={item.name}>
                            <img src={wardrobeSymbols.shoes} alt="등록된 신발을 나타내는 흰색 신발 심볼" />
                            <small>{item.name}</small>
                          </button>
                        ) : (
                          <div className="shoe-slot empty" key={`shoes-${index}`} aria-hidden="true">
                            <span>{index + 1}</span>
                          </div>
                        ),
                      )}
                    </div>
                  ) : (
                    <>
                      <div className="closet-rail"><i /><i /><i /></div>
                      <div className="closet-items">
                        {slots.map((item, index) =>
                          item ? (
                            <button className="closet-item filled" key={item.id} title={item.name}>
                              <span className="hanger-hook" />
                              <span className="hanger-shoulders" />
                              <img
                                src={wardrobeSymbols[item.category]}
                                alt={`등록된 ${category.label}을 나타내는 흰색 의상 심볼`}
                              />
                              <small>{item.name}</small>
                            </button>
                          ) : (
                            <div
                              className="closet-item empty-hanger"
                              key={`${category.id}-${index}`}
                              aria-hidden="true"
                            >
                              <span className="hanger-hook" />
                              <span className="hanger-shoulders" />
                              <small>{index + 1}</small>
                            </div>
                          ),
                        )}
                      </div>
                    </>
                  )}
                  <button className="center-add-button" onClick={() => onAdd(category.id)} aria-label={`${category.label} 옷 추가`}>
                    <span>+</span>
                    <small>옷 걸기</small>
                  </button>
                </article>
              )
            })}
        </div>
      </section>
      <p className="closet-tip"><Icon size={18}><path d="M9 18h6M10 22h4M8.5 14.5a6 6 0 1 1 7 0c-1 .8-1.5 1.6-1.5 2.5h-4c0-.9-.5-1.7-1.5-2.5Z" /></Icon>옷을 등록하면 색상과 카테고리를 분석해 알맞은 칸에 정리해드려요.</p>
      <Footer />
    </main>
  )
}

function AddClothing({
  initialCategory,
  categoryCounts,
  onSave,
  onCancel,
}: {
  initialCategory: Category
  categoryCounts: Record<Category, number>
  onSave: (item: Omit<ClothingItem, 'id'>) => void
  onCancel: () => void
}) {
  const [category, setCategory] = useState<Category>(initialCategory)
  const [name, setName] = useState('')
  const [color, setColor] = useState('')
  const [preview, setPreview] = useState<string>('')
  const fileRef = useRef<HTMLInputElement>(null)

  const handleFile = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) setPreview(URL.createObjectURL(file))
  }

  const save = () => {
    if (!preview) return
    onSave({
      name: name.trim() || `새 ${categories.find((item) => item.id === category)?.label}`,
      color: color.trim() || '색상 미지정',
      category,
      image: preview,
    })
  }

  return (
    <main className="add-page">
      <section className="add-heading">
        <button onClick={onCancel} className="back-button">← 내 옷장</button>
        <span className="eyebrow">ADD TO MY CLOSET</span>
        <h1>새 옷 등록하기</h1>
        <p>옷 사진을 올리면 내 옷장의 알맞은 칸에 정리해드려요.</p>
      </section>
      <section className="add-workspace">
        <div className="upload-panel">
          <div
            className={`upload-dropzone ${preview ? 'has-image' : ''}`}
            onClick={() => fileRef.current?.click()}
            onKeyDown={(event) => event.key === 'Enter' && fileRef.current?.click()}
            role="button"
            tabIndex={0}
          >
            {preview ? (
              <>
                <img src={preview} alt="등록할 옷 미리보기" />
                <button onClick={(event) => { event.stopPropagation(); setPreview('') }}>사진 바꾸기</button>
              </>
            ) : (
              <div>
                <span className="upload-icon"><Icon size={28}><path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3M12 4v11M8 8l4-4 4 4" /></Icon></span>
                <h2>옷 사진을 올려주세요</h2>
                <p>배경이 단순하고 옷 전체가 보이는 사진이 좋아요.</p>
                <b>사진 선택</b>
                <small>JPG, PNG · 최대 10MB</small>
              </div>
            )}
            <input ref={fileRef} type="file" accept="image/png,image/jpeg" onChange={handleFile} hidden />
          </div>
          <div className="photo-tips">
            <span><b>01</b> 옷 전체가 보이게</span>
            <span><b>02</b> 밝은 곳에서 선명하게</span>
            <span><b>03</b> 한 장에 한 벌만</span>
          </div>
        </div>
        <div className="item-form">
          <div className="form-progress"><span>1. 사진 등록</span><span className={preview ? 'active' : ''}>2. 정보 확인</span><span>3. 옷장에 저장</span></div>
          <label>
            <span>어떤 종류의 옷인가요?</span>
            <div className="category-options">
              {categories.map((item) => (
                <button
                  key={item.id}
                  className={category === item.id ? 'active' : ''}
                  onClick={() => setCategory(item.id)}
                >
                  <Icon size={21}>
                    {item.id === 'shoes' ? <path d="M4 15c4 0 6-3 7-7l3 1c0 4 2 6 6 7v3H4Z" /> : <path d="M8 5 4 7l-2 5 3 2 2-3v9h10v-9l2 3 3-2-2-5-4-2c-1 2-7 2-8 0Z" />}
                  </Icon>
                  {item.label} <small>{categoryCounts[item.id]}개</small>
                </button>
              ))}
            </div>
          </label>
          <label><span>옷 이름</span><input value={name} onChange={(event) => setName(event.target.value)} placeholder="예: 아이보리 케이블 니트" /></label>
          <label><span>대표 색상</span><input value={color} onChange={(event) => setColor(event.target.value)} placeholder="예: 아이보리" /></label>
          <div className="analysis-note"><Icon><path d="m9 18-6-6 6-6M15 6l6 6-6 6" /></Icon><div><b>사진 분석 준비 완료</b><p>사진을 등록하면 카테고리와 색상을 자동으로 추천할 예정이에요.</p></div></div>
          <div className="form-actions"><button onClick={onCancel}>취소</button><button className="primary-button" disabled={!preview} onClick={save}>내 옷장에 넣기 <span>→</span></button></div>
        </div>
      </section>
    </main>
  )
}

function CalendarPage() {
  const today = new Date()
  const [viewDate, setViewDate] = useState(new Date(today.getFullYear(), today.getMonth(), 1))
  const year = viewDate.getFullYear()
  const month = viewDate.getMonth()
  const [selectedDay, setSelectedDay] = useState(today.getDate())
  const firstDay = new Date(year, month, 1).getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const previousMonthDays = new Date(year, month, 0).getDate()
  const calendarCells = Array.from({ length: 42 }, (_, index) => {
    const dayOffset = index - firstDay + 1
    if (dayOffset < 1) return { day: previousMonthDays + dayOffset, current: false }
    if (dayOffset > daysInMonth) return { day: dayOffset - daysInMonth, current: false }
    return { day: dayOffset, current: true }
  })
  const weekdays = ['일', '월', '화', '수', '목', '금', '토']
  const changeMonth = (offset: number) => {
    setViewDate(new Date(year, month + offset, 1))
    setSelectedDay(1)
  }

  return (
    <main className="calendar-page">
      <section className="calendar-heading">
        <div>
          <span className="eyebrow">OUTFIT CALENDAR</span>
          <h1>옷차림 캘린더</h1>
          <p>날짜를 선택하고 그날 입은 옷을 확인해보세요.</p>
        </div>
        <div className="selected-date">
          <span>선택한 날짜</span>
          <strong>{year}. {String(month + 1).padStart(2, '0')}. {String(selectedDay).padStart(2, '0')}</strong>
        </div>
      </section>

      <section className="calendar-card">
        <div className="calendar-month">
          <button aria-label="이전 달" onClick={() => changeMonth(-1)}>←</button>
          <h2>{year}년 {month + 1}월</h2>
          <button aria-label="다음 달" onClick={() => changeMonth(1)}>→</button>
        </div>
        <div className="calendar-weekdays">
          {weekdays.map((weekday) => <span key={weekday}>{weekday}</span>)}
        </div>
        <div className="calendar-grid">
          {calendarCells.map((cell, index) => {
            const isToday = cell.current && cell.day === today.getDate() && month === today.getMonth() && year === today.getFullYear()
            const isSelected = cell.current && cell.day === selectedDay
            return (
              <button
                key={`${cell.current ? 'current' : 'near'}-${cell.day}-${index}`}
                className={`${cell.current ? '' : 'outside'} ${isSelected ? 'selected' : ''}`}
                disabled={!cell.current}
                onClick={() => setSelectedDay(cell.day)}
              >
                <span>{cell.day}</span>
                {isToday && <small>오늘</small>}
              </button>
            )
          })}
        </div>
        <div className="calendar-action">
          <button className="primary-button">
            {month + 1}월 {selectedDay}일에 입은 옷 확인하기 <span>→</span>
          </button>
        </div>
      </section>
      <Footer />
    </main>
  )
}

export default function App() {
  const [tab, setTab] = useState<Tab>('home')
  const [items, setItems] = useState<ClothingItem[]>([])
  const [addCategory, setAddCategory] = useState<Category>('top')
  const categoryCounts = categories.reduce(
    (counts, category) => {
      counts[category.id] = items.filter((item) => item.category === category.id).length
      return counts
    },
    { outer: 0, top: 0, bottom: 0, shoes: 0 } as Record<Category, number>,
  )

  const openAdd = (category: Category = 'top') => {
    setAddCategory(category)
    setTab('add')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const saveItem = (item: Omit<ClothingItem, 'id'>) => {
    setItems((current) => [...current, { ...item, id: Date.now() }])
    setTab('closet')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <div className="app">
      <Header active={tab} onChange={(next) => next === 'add' ? openAdd() : setTab(next)} />
      {tab === 'home' && <Home onOpenCloset={() => setTab('closet')} />}
      {tab === 'closet' && <Closet items={items} onAdd={openAdd} />}
      {tab === 'add' && <AddClothing key={addCategory} initialCategory={addCategory} categoryCounts={categoryCounts} onSave={saveItem} onCancel={() => setTab('closet')} />}
      {tab === 'calendar' && <CalendarPage />}
    </div>
  )
}
