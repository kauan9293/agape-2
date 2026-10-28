import { FormEvent, useEffect, useState } from 'react'
import { Link, NavLink, Route, Routes, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { ArrowDownRight, ArrowLeft, ArrowRight, Check, ChevronDown, Instagram, LockKeyhole, Minus, Plus, Search, ShoppingBag, Sparkles, Trash2, Upload, X } from 'lucide-react'
import { api, dateTime, money } from './api'
import type { CartLine, Category, Order, Product } from './types'

const instagramUrl = 'https://www.instagram.com/confeitaria_agape_artesanal_/'
const fallbackPhotos = [
  'https://images.unsplash.com/photo-1578985545062-69928b1d9587?auto=format&fit=crop&w=1000&q=85',
  'https://images.unsplash.com/photo-1551024506-0bccd828d307?auto=format&fit=crop&w=1000&q=85',
  'https://images.unsplash.com/photo-1488477181946-6428a0291777?auto=format&fit=crop&w=1000&q=85',
]

function photo(product?: Product, index = 0) {
  return product?.images[0]?.url ?? fallbackPhotos[index % fallbackPhotos.length]
}

function App() {
  const [cart, setCart] = useState<CartLine[]>(() => {
    try { return JSON.parse(localStorage.getItem('agape-cart') ?? '[]') as CartLine[] } catch { return [] }
  })
  useEffect(() => localStorage.setItem('agape-cart', JSON.stringify(cart)), [cart])

  function addToCart(product: Product, quantity = 1, variantId?: number) {
    setCart((current) => {
      const found = current.find((line) => line.product.id === product.id && line.variantId === variantId)
      if (found) return current.map((line) => line === found ? { ...line, quantity: line.quantity + quantity } : line)
      return [...current, { product, quantity, variantId }]
    })
  }
  function updateQuantity(productId: number, variantId: number | undefined, quantity: number) {
    setCart((current) => quantity < 1 ? current.filter((line) => !(line.product.id === productId && line.variantId === variantId)) : current.map((line) => line.product.id === productId && line.variantId === variantId ? { ...line, quantity } : line))
  }

  return <Routes>
    <Route path="/" element={<><SiteHeader count={cart.reduce((sum, line) => sum + line.quantity, 0)} /><HomePage /><SiteFooter /></>} />
    <Route path="/produtos" element={<><SiteHeader count={cart.reduce((sum, line) => sum + line.quantity, 0)} /><CatalogPage /><SiteFooter /></>} />
    <Route path="/produto/:slug" element={<><SiteHeader count={cart.reduce((sum, line) => sum + line.quantity, 0)} /><ProductPage addToCart={addToCart} /><SiteFooter /></>} />
    <Route path="/carrinho" element={<><SiteHeader count={cart.reduce((sum, line) => sum + line.quantity, 0)} /><CartPage cart={cart} updateQuantity={updateQuantity} clearCart={() => setCart([])} /><SiteFooter /></>} />
    <Route path="/admin/*" element={<AdminArea />} />
    <Route path="*" element={<><SiteHeader count={cart.length} /><main className="not-found"><p className="eyebrow">404 · Página não encontrada</p><h1>Essa página não está no nosso cardápio.</h1><Link className="button button-dark" to="/produtos">Ver produtos <ArrowRight size={16} /></Link></main><SiteFooter /></>} />
  </Routes>
}

function SiteHeader({ count }: { count: number }) {
  return <header className="site-header">
    <Link className="brand" to="/" aria-label="Confeitaria Ágape Artesanal, início"><span className="brand-mark">á</span><span className="brand-copy"><strong>Ágape</strong><small>CONFEITARIA ARTESANAL</small></span></Link>
    <nav className="main-nav" aria-label="Navegação principal"><NavLink to="/produtos">Cardápio</NavLink><a href="/#sobre">Nossa história</a><a href={instagramUrl} target="_blank" rel="noreferrer">Instagram</a></nav>
    <Link className="cart-link" to="/carrinho" aria-label={`Sacola, ${count} itens`}><ShoppingBag size={19} /><span>Sacola</span><span className="cart-count">{count}</span></Link>
  </header>
}

function SiteFooter() {
  const [contacts, setContacts] = useState<{ business_whatsapp: string; business_email: string; instagram_url: string } | null>(null)
  useEffect(() => { api<typeof contacts>('/api/storefront-config').then(setContacts).catch(() => setContacts(null)) }, [])
  const whatsapp = contacts?.business_whatsapp.replace(/\D/g, '')
  const formattedPhone = whatsapp?.startsWith('55') && whatsapp.length === 13
    ? `+55 ${whatsapp.slice(2, 4)} ${whatsapp.slice(4, 9)}-${whatsapp.slice(9)}`
    : whatsapp ? `+${whatsapp}` : ''
  return <footer className="site-footer"><div className="footer-main"><div><Link className="brand brand-light" to="/"><span className="brand-mark">á</span><span className="brand-copy"><strong>Ágape</strong><small>CONFEITARIA ARTESANAL</small></span></Link><p>Feito com cuidado, para celebrar o que importa.</p></div><div className="footer-links"><span className="eyebrow">Explore</span><Link to="/produtos">Cardápio</Link><a href="/#sobre">Nossa história</a><Link to="/carrinho">Sacola</Link></div><div className="footer-links"><span className="eyebrow">Fale com a gente</span>{formattedPhone && <><a href={`tel:+${whatsapp}`}>{formattedPhone}</a><a href={`https://wa.me/${whatsapp}`} target="_blank" rel="noreferrer">WhatsApp para encomendas</a></>}<a href={`mailto:${contacts?.business_email ?? 'agapeconfeitaria06@gmail.com'}`}>{contacts?.business_email ?? 'agapeconfeitaria06@gmail.com'}</a><a href={contacts?.instagram_url ?? instagramUrl} target="_blank" rel="noreferrer"><Instagram size={16} /> Instagram oficial</a></div></div><div className="footer-bottom"><span>© {new Date().getFullYear()} Confeitaria Ágape Artesanal</span><span>Produção artesanal sob encomenda</span></div></footer>
}

function ProductCard({ product, index = 0 }: { product: Product; index?: number }) {
  const available = product.is_available && (product.stock === null || product.stock > 0) && (!product.variants.length || product.variants.some((variant) => variant.is_available && (variant.stock === null || variant.stock > 0)))
  return <article className="product-card"><Link className="product-image" to={`/produto/${product.slug}`}><img src={photo(product, index)} alt={product.images[0]?.alt_text || product.name} loading="lazy" />{!available && <span className="image-badge">Indisponível</span>}{product.is_demo && <span className="image-badge demo-badge">Demonstração</span>}<span className="image-arrow"><ArrowDownRight size={19} /></span></Link><div className="product-info"><div><p className="product-category">{product.category.name}</p><Link to={`/produto/${product.slug}`} className="product-name">{product.name}</Link></div><span className="product-price">{money(product.price)}</span></div></article>
}

function HomePage() {
  const [products, setProducts] = useState<Product[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [error, setError] = useState('')
  useEffect(() => { Promise.all([api<Product[]>('/api/products?featured=true'), api<Category[]>('/api/categories')]).then(([items, groups]) => { setProducts(items); setCategories(groups) }).catch(() => setError('Não foi possível carregar o cardápio agora.')) }, [])
  return <main>
    <section className="hero"><div className="hero-copy"><p className="eyebrow"><Sparkles size={14} /> Feito à mão, com afeto</p><h1>Um doce momento<br /><em>feito para você.</em></h1><p className="hero-intro">Receitas artesanais, ingredientes escolhidos e um carinho que cabe em cada pedaço.</p><div className="hero-actions"><Link className="button button-dark" to="/produtos">Descobrir o cardápio <ArrowRight size={16} /></Link><a className="text-link" href="#sobre">Conheça a Ágape <ArrowDownRight size={15} /></a></div><div className="hero-note"><span className="note-line" /><span>Pequenos lotes. Grandes celebrações.</span></div></div><div className="hero-visual"><img src={fallbackPhotos[0]} alt="Bolo artesanal decorado com frutas" /><div className="hero-stamp"><span>feito</span><strong>com<br />amor</strong><span>artesanal</span></div><span className="hero-image-caption">Confeitaria Ágape · artesanal</span></div><div className="hero-index">01 <span /> 03</div></section>
    <section className="featured section-wrap"><div className="section-heading"><div><p className="eyebrow">Da nossa cozinha</p><h2>Escolhas da casa<span>.</span></h2></div><Link className="text-link" to="/produtos">Ver todo o cardápio <ArrowRight size={16} /></Link></div>{error ? <p className="notice error">{error}</p> : products.length ? <div className="product-grid">{products.slice(0, 3).map((product, index) => <ProductCard key={product.id} product={product} index={index} />)}</div> : <div className="empty-featured"><p>Estamos preparando novidades para o cardápio.</p><Link to="/produtos">Explorar produtos <ArrowRight size={15} /></Link></div>}</section>
    <section className="category-band"><div className="section-wrap"><div className="section-heading"><div><p className="eyebrow">Feito para cada ocasião</p><h2>Um sabor para <em>cada história.</em></h2></div><span className="category-aside">Descubra algo especial para<br />o seu próximo momento.</span></div><div className="category-list">{categories.map((category, index) => <Link key={category.id} to={`/produtos?categoria=${category.slug}`}><span className="category-num">0{index + 1}</span><span>{category.name}</span><ArrowDownRight size={18} /></Link>)}{!categories.length && <Link to="/produtos"><span className="category-num">01</span><span>Conheça o cardápio</span><ArrowDownRight size={18} /></Link>}</div></div></section>
    <section id="sobre" className="story section-wrap"><div className="story-image"><img src={fallbackPhotos[2]} alt="Doce artesanal preparado com cuidado" loading="lazy" /><span>feito à mão<br />em cada detalhe</span></div><div className="story-copy"><p className="eyebrow">Nossa história</p><h2>Mais do que doce,<br /><em>um jeito de cuidar.</em></h2><p>A Confeitaria Ágape Artesanal nasceu do desejo de transformar ingredientes simples em momentos para guardar. Cada criação é preparada com atenção aos detalhes e respeito ao tempo de fazer bem feito.</p><p>Um convite para celebrar os dias comuns e os momentos que merecem ser lembrados.</p><a href={instagramUrl} target="_blank" rel="noreferrer" className="text-link">Acompanhe nossa cozinha <ArrowRight size={16} /></a></div></section>
    <section className="closing-band"><div className="section-wrap"><p className="eyebrow">O próximo momento especial começa aqui</p><h2>Tem lugar para<br /><em>mais um docinho.</em></h2><Link to="/produtos" className="button button-cream">Escolher meus favoritos <ArrowRight size={16} /></Link></div></section>
  </main>
}

function CatalogPage() {
  const [params, setParams] = useSearchParams()
  const [categories, setCategories] = useState<Category[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const search = params.get('q') ?? ''
  const category = params.get('categoria') ?? ''
  useEffect(() => { api<Category[]>('/api/categories').then(setCategories).catch(() => setError('Não foi possível carregar as categorias.')) }, [])
  useEffect(() => {
    setLoading(true)
    const query = new URLSearchParams()
    if (search) query.set('q', search)
    if (category) query.set('category', category)
    api<Product[]>(`/api/products?${query}`).then(setProducts).catch(() => setError('Não foi possível carregar os produtos.')).finally(() => setLoading(false))
  }, [search, category])
  function updateParam(key: string, value: string) { const next = new URLSearchParams(params); if (value) next.set(key, value); else next.delete(key); setParams(next) }
  return <main className="catalog section-wrap"><div className="page-intro"><p className="eyebrow">Nosso cardápio</p><h1>Feito para <em>adoçar o dia.</em></h1><p>Conheça as criações da nossa cozinha artesanal.</p></div><div className="catalog-toolbar"><div className="filter-tabs" aria-label="Filtrar por categoria"><button className={!category ? 'active' : ''} onClick={() => updateParam('categoria', '')}>Todos</button>{categories.map((item) => <button key={item.id} className={category === item.slug ? 'active' : ''} onClick={() => updateParam('categoria', item.slug)}>{item.name}</button>)}</div><label className="search-field"><Search size={17} /><input value={search} onChange={(event) => updateParam('q', event.target.value)} placeholder="Buscar no cardápio" aria-label="Buscar produtos pelo nome" /><kbd>↵</kbd></label></div>{error && <p className="notice error">{error}</p>}{loading ? <div className="loading-state">Carregando o cardápio...</div> : products.length ? <div className="product-grid catalog-grid">{products.map((product, index) => <ProductCard key={product.id} product={product} index={index} />)}</div> : <div className="empty-state"><ShoppingBag size={25} /><h2>Nenhum produto por aqui</h2><p>Tente outra busca ou escolha uma categoria diferente.</p><button className="text-link" onClick={() => setParams({})}>Limpar filtros <ArrowRight size={15} /></button></div>}</main>
}

function ProductPage({ addToCart }: { addToCart: (product: Product, quantity: number, variantId?: number) => void }) {
  const { slug = '' } = useParams()
  const [product, setProduct] = useState<Product | null>(null)
  const [activeImage, setActiveImage] = useState<string | null>(null)
  const [quantity, setQuantity] = useState(1)
  const [variantId, setVariantId] = useState<number | undefined>()
  const [error, setError] = useState('')
  const [added, setAdded] = useState(false)
  useEffect(() => { setActiveImage(null); api<Product>(`/api/products/${slug}`).then(setProduct).catch((reason: Error) => setError(reason.message)) }, [slug])
  if (error) return <main className="not-found"><p className="eyebrow">Produto</p><h1>{error}</h1><Link to="/produtos" className="button button-dark">Voltar ao cardápio</Link></main>
  if (!product) return <main className="loading-state">Carregando produto...</main>
  const selected = product.variants.find((variant) => variant.id === variantId)
  const unavailable = !product.is_available || (product.stock !== null && product.stock < 1) || (product.variants.length > 0 && !product.variants.some((variant) => variant.is_available && (variant.stock === null || variant.stock > 0)))
  const price = Number(product.price) + Number(selected?.price_delta ?? 0)
  const selectedImage = product.images.find((image) => image.url === activeImage)
  return <main className="product-detail section-wrap"><Link className="back-link" to="/produtos"><ArrowLeft size={16} /> Voltar ao cardápio</Link><div className="detail-layout"><div className="detail-photo"><img src={activeImage ?? photo(product)} alt={selectedImage?.alt_text || product.images[0]?.alt_text || product.name} />{product.images.length > 1 && <div className="detail-thumbs" aria-label="Galeria de imagens">{product.images.map((image) => <button className={activeImage === image.url || (!activeImage && image.url === product.images[0].url) ? 'active' : ''} key={image.id} onClick={() => setActiveImage(image.url)} aria-label={`Ver imagem de ${image.alt_text || product.name}`} aria-pressed={activeImage === image.url || (!activeImage && image.url === product.images[0].url)}><img src={image.url} alt="" /></button>)}</div>}</div><div className="detail-copy"><p className="eyebrow">{product.category.name}</p><h1>{product.name}</h1><p className="detail-description">{product.description}</p><p className="detail-price">{money(price)}</p>{product.variants.length > 0 && <label className="form-field"><span>Escolha uma opção</span><span className="select-wrap"><select value={variantId ?? ''} onChange={(event) => setVariantId(event.target.value ? Number(event.target.value) : undefined)}><option value="">Selecione</option>{product.variants.map((variant) => <option disabled={!variant.is_available || variant.stock === 0} key={variant.id} value={variant.id}>{variant.name}{Number(variant.price_delta) > 0 ? ` · +${money(variant.price_delta)}` : ''}{!variant.is_available || variant.stock === 0 ? ' · indisponível' : ''}</option>)}</select><ChevronDown size={16} /></span></label>}<div className="quantity-row"><span>Quantidade</span><div className="quantity-control"><button aria-label="Diminuir quantidade" onClick={() => setQuantity(Math.max(1, quantity - 1))}><Minus size={15} /></button><span>{quantity}</span><button aria-label="Aumentar quantidade" onClick={() => setQuantity(Math.min(50, quantity + 1))}><Plus size={15} /></button></div></div><button disabled={unavailable || (product.variants.length > 0 && (!selected?.is_available || selected.stock === 0))} className="button button-dark add-button" onClick={() => { addToCart(product, quantity, variantId); setAdded(true); window.setTimeout(() => setAdded(false), 2200) }}>{added ? <><Check size={17} /> Adicionado à sacola</> : <><ShoppingBag size={17} /> {unavailable ? 'Indisponível' : 'Adicionar à sacola'}</>}</button><div className="detail-note"><span className="note-line" /><p>Produzido sob encomenda. Consulte a disponibilidade e o prazo mínimo pelo canal de contato antes de concluir.</p></div></div></div></main>
}

function CartPage({ cart, updateQuantity, clearCart }: { cart: CartLine[]; updateQuantity: (id: number, variantId: number | undefined, quantity: number) => void; clearCart: () => void }) {
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [email, setEmail] = useState('')
  const [fulfillment, setFulfillment] = useState<'pickup' | 'delivery'>('pickup')
  const [requestedFor, setRequestedFor] = useState('')
  const [minimumNotice, setMinimumNotice] = useState(48)
  const [notes, setNotes] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<{ public_code: string; total: string; whatsapp_url: string | null } | null>(null)
  useEffect(() => { api<{ minimum_order_notice_hours: number }>('/api/storefront-config').then((config) => setMinimumNotice(config.minimum_order_notice_hours)).catch(() => undefined) }, [])
  const minRequestedFor = new Date(Date.now() + minimumNotice * 60 * 60 * 1000)
  const minRequestedValue = new Date(minRequestedFor.getTime() - minRequestedFor.getTimezoneOffset() * 60 * 1000).toISOString().slice(0, 16)
  const subtotal = cart.reduce((sum, line) => {
    const variant = line.product.variants.find((item) => item.id === line.variantId)
    return sum + (Number(line.product.price) + Number(variant?.price_delta ?? 0)) * line.quantity
  }, 0)
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    try {
      const order = await api<typeof result>('/api/orders', { method: 'POST', body: JSON.stringify({ customer_name: name, customer_email: email || null, customer_phone: phone, fulfillment, requested_for: new Date(requestedFor).toISOString(), delivery_notes: notes, items: cart.map((line) => ({ product_id: line.product.id, variant_id: line.variantId ?? null, quantity: line.quantity })) }) })
      setResult(order); clearCart()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Não foi possível registrar o pedido.') }
    finally { setBusy(false) }
  }
  if (result) return <main className="checkout-result section-wrap"><div className="result-check"><Check size={27} /></div><p className="eyebrow">Pedido registrado</p><h1>Obrigada por escolher<br /><em>a Ágape.</em></h1><p>Seu código de pedido é <strong>{result.public_code}</strong>. O pedido ainda precisa ser confirmado pela confeitaria; nenhum pagamento foi realizado.</p><p className="result-total">Total calculado: {money(result.total)}</p>{result.whatsapp_url && <a className="button button-dark" href={result.whatsapp_url} target="_blank" rel="noreferrer">Continuar no WhatsApp <ArrowRight size={16} /></a>}<Link className="text-link" to="/produtos">Voltar ao cardápio</Link></main>
  if (!cart.length) return <main className="empty-state cart-empty"><ShoppingBag size={28} /><p className="eyebrow">Sua sacola</p><h1>Ainda está vazia.</h1><p>Escolha algo especial no nosso cardápio.</p><Link to="/produtos" className="button button-dark">Explorar cardápio <ArrowRight size={16} /></Link></main>
  return <main className="cart-page section-wrap"><div className="page-intro compact"><p className="eyebrow">Quase lá</p><h1>Sua <em>sacola.</em></h1></div><div className="cart-layout"><section className="cart-lines" aria-label="Itens na sacola">{cart.map((line) => { const variant = line.product.variants.find((item) => item.id === line.variantId); const unitPrice = Number(line.product.price) + Number(variant?.price_delta ?? 0); return <article className="cart-line" key={`${line.product.id}-${line.variantId ?? 'base'}`}><img src={photo(line.product)} alt="" /><div className="cart-line-info"><Link to={`/produto/${line.product.slug}`}>{line.product.name}</Link>{variant && <span>{variant.name}</span>}<span>{money(unitPrice)} cada</span></div><div className="quantity-control"><button aria-label={`Diminuir ${line.product.name}`} onClick={() => updateQuantity(line.product.id, line.variantId, line.quantity - 1)}><Minus size={15} /></button><span>{line.quantity}</span><button aria-label={`Aumentar ${line.product.name}`} onClick={() => updateQuantity(line.product.id, line.variantId, line.quantity + 1)}><Plus size={15} /></button></div><strong>{money(unitPrice * line.quantity)}</strong><button className="icon-button remove-line" aria-label={`Remover ${line.product.name}`} onClick={() => updateQuantity(line.product.id, line.variantId, 0)}><Trash2 size={17} /></button></article> })}<Link className="text-link continue-link" to="/produtos"><ArrowLeft size={15} /> Continuar escolhendo</Link></section><form className="checkout-form" onSubmit={submit}><div className="checkout-title"><h2>Seus dados</h2><span>Solicitação de encomenda</span></div><label className="form-field"><span>Nome</span><input required minLength={2} maxLength={160} value={name} onChange={(event) => setName(event.target.value)} autoComplete="name" /></label><label className="form-field"><span>Celular / WhatsApp</span><input required minLength={8} maxLength={30} value={phone} onChange={(event) => setPhone(event.target.value)} autoComplete="tel" /></label><label className="form-field"><span>E-mail <small>opcional</small></span><input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" /></label><label className="form-field"><span>Data e horário desejados · mínimo de {minimumNotice}h</span><input type="datetime-local" required min={minRequestedValue} value={requestedFor} onChange={(event) => setRequestedFor(event.target.value)} /></label><fieldset className="fulfillment-choice"><legend>Recebimento</legend><label><input type="radio" checked={fulfillment === 'pickup'} onChange={() => setFulfillment('pickup')} /> Retirada</label><label><input type="radio" checked={fulfillment === 'delivery'} onChange={() => setFulfillment('delivery')} /> Entrega</label></fieldset>{fulfillment === 'delivery' && <label className="form-field"><span>Endereço e observações</span><textarea required maxLength={500} value={notes} onChange={(event) => setNotes(event.target.value)} rows={3} /></label>}{error && <p className="notice error">{error}</p>}<div className="checkout-total"><span>Subtotal</span><strong>{money(subtotal)}</strong></div><p className="checkout-disclaimer">O pedido fica pendente de confirmação. Valores e disponibilidade são conferidos pela confeitaria. Nenhum pagamento é processado aqui.</p><button className="button button-dark checkout-submit" disabled={busy}>{busy ? 'Enviando...' : 'Solicitar encomenda'} <ArrowRight size={16} /></button></form></div></main>
}

function AdminArea() {
  const [user, setUser] = useState<{ email: string } | null>(null)
  const [checked, setChecked] = useState(false)
  const navigate = useNavigate()
  useEffect(() => { api<{ email: string }>('/api/auth/me').then(setUser).catch(() => setUser(null)).finally(() => setChecked(true)) }, [])
  if (!checked) return <main className="admin-loading">Verificando acesso...</main>
  if (!user) return <AdminLogin onLogin={setUser} />
  return <AdminDashboard user={user} onLogout={async () => { await api('/api/auth/logout', { method: 'POST' }).catch(() => undefined); setUser(null); navigate('/admin') }} />
}

function AdminLogin({ onLogin }: { onLogin: (user: { email: string }) => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(''); setBusy(true)
    try { const user = await api<{ email: string }>('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }); onLogin(user) }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Não foi possível entrar.') }
    finally { setBusy(false) }
  }
  return <main className="admin-login"><Link className="brand" to="/"><span className="brand-mark">á</span><span className="brand-copy"><strong>Ágape</strong><small>PAINEL ADMINISTRATIVO</small></span></Link><form className="login-card" onSubmit={submit}><LockKeyhole size={22} /><p className="eyebrow">Acesso restrito</p><h1>Bem-vinda de volta.</h1><label className="form-field"><span>E-mail</span><input type="email" required autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} /></label><label className="form-field"><span>Senha</span><input type="password" required autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>{error && <p className="notice error">{error}</p>}<button className="button button-dark" disabled={busy}>{busy ? 'Entrando...' : 'Entrar no painel'} <ArrowRight size={16} /></button><Link className="login-back" to="/">Voltar à loja</Link></form><span className="admin-footnote">Confeitaria Ágape Artesanal</span></main>
}

type DashboardStats = { products: number; available_products: number; unavailable_products: number; orders: number; pending_orders: number; paid_sales: string }
type ProductPayload = { category_id: number; name: string; slug: string; description: string; price: string; is_available: boolean; is_published: boolean; is_featured: boolean; is_demo: boolean; stock: number | null; images: { url: string; alt_text: string }[]; variants: { name: string; price_delta: string; stock: number | null; is_available: boolean }[] }

function AdminDashboard({ user, onLogout }: { user: { email: string }; onLogout: () => void }) {
  const [section, setSection] = useState<'products' | 'orders'>('products')
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [products, setProducts] = useState<Product[]>([])
  const [orders, setOrders] = useState<Order[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [editor, setEditor] = useState<Product | 'new' | null>(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function refresh() {
    try {
      const [dashboard, productItems, orderItems, categoryItems] = await Promise.all([api<DashboardStats>('/api/admin/dashboard'), api<Product[]>('/api/admin/products'), api<Order[]>('/api/admin/orders'), api<Category[]>('/api/admin/categories')])
      setStats(dashboard); setProducts(productItems); setOrders(orderItems); setCategories(categoryItems); setError('')
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Falha ao carregar dados administrativos.') }
  }
  useEffect(() => { void refresh() }, [])
  async function saveProduct(payload: ProductPayload, product: Product | 'new') {
    setBusy(true); setError(''); setMessage('')
    try {
      await api(product === 'new' ? '/api/admin/products' : `/api/admin/products/${product.id}`, { method: product === 'new' ? 'POST' : 'PUT', body: JSON.stringify(payload) })
      setEditor(null); setMessage('Produto salvo com sucesso.'); await refresh()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Não foi possível salvar o produto.') }
    finally { setBusy(false) }
  }
  async function archive(product: Product) {
    if (!window.confirm(`Arquivar “${product.name}”? Ele deixará de aparecer na loja.`)) return
    try { await api(`/api/admin/products/${product.id}/archive`, { method: 'POST' }); setMessage('Produto arquivado.'); await refresh() }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Não foi possível arquivar o produto.') }
  }
  async function changeStatus(order: Order, status: string) {
    try { await api(`/api/admin/orders/${order.id}/status`, { method: 'PATCH', body: JSON.stringify({ status }) }); setMessage(`Pedido ${order.public_code} atualizado.`); await refresh() }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Não foi possível atualizar o pedido.') }
  }
  return <main className="admin-app"><header className="admin-header"><Link className="brand" to="/"><span className="brand-mark">á</span><span className="brand-copy"><strong>Ágape</strong><small>ADMINISTRAÇÃO</small></span></Link><div className="admin-user"><span>{user.email}</span><button onClick={onLogout}>Sair</button></div></header><div className="admin-body"><aside className="admin-sidebar"><p className="eyebrow">Loja</p><button className={section === 'products' ? 'selected' : ''} onClick={() => setSection('products')}><ShoppingBag size={17} /> Produtos</button><button className={section === 'orders' ? 'selected' : ''} onClick={() => setSection('orders')}><ArrowRight size={17} /> Pedidos</button><a href="/" target="_blank" rel="noreferrer">Abrir loja <ArrowDownRight size={16} /></a><div className="sidebar-foot">Dados da loja<br />Confeitaria Ágape</div></aside><section className="admin-content"><div className="admin-title"><div><p className="eyebrow">Visão geral</p><h1>{section === 'products' ? 'Produtos' : 'Pedidos'}</h1></div>{section === 'products' && <button className="button button-dark" onClick={() => setEditor('new')}><Plus size={17} /> Novo produto</button>}</div>{stats && <div className="stat-grid"><Stat label="Produtos" value={stats.products} /><Stat label="Disponíveis" value={stats.available_products} /><Stat label="Indisponíveis" value={stats.unavailable_products} /><Stat label="Pedidos pendentes" value={stats.pending_orders} /><Stat label="Vendas pagas" value={money(stats.paid_sales)} /></div>}{error && <p className="notice error">{error}</p>}{message && <p className="notice success">{message}</p>}{section === 'products' ? <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Produto</th><th>Categoria</th><th>Preço</th><th>Disponibilidade</th><th>Publicado</th><th aria-label="Ações" /></tr></thead><tbody>{products.map((product) => <tr key={product.id}><td><div className="table-product"><img src={photo(product)} alt="" /><span>{product.name}</span></div></td><td>{product.category.name}</td><td>{money(product.price)}</td><td><span className={`status-pill ${product.is_available ? 'status-green' : 'status-muted'}`}>{product.is_available ? 'Disponível' : 'Indisponível'}</span></td><td>{product.is_published ? 'Publicado' : 'Rascunho'}</td><td><button className="table-action" onClick={() => setEditor(product)}>Editar</button><button className="table-action danger-text" onClick={() => void archive(product)}>Arquivar</button></td></tr>)}{!products.length && <tr><td colSpan={6}>Nenhum produto cadastrado. Crie o primeiro para começar.</td></tr>}</tbody></table></div> : <div className="order-list">{orders.map((order) => <article className="order-card" key={order.id}><div className="order-card-head"><div><strong>#{order.public_code}</strong><span>{dateTime(order.created_at)}</span></div><select aria-label={`Status do pedido ${order.public_code}`} value={order.status} onChange={(event) => void changeStatus(order, event.target.value)}>{['pending', 'confirmed', 'preparing', 'ready', 'completed', 'cancelled', 'paid'].map((value) => <option key={value} value={value}>{orderStatusLabel(value)}</option>)}</select></div><div className="order-customer"><strong>{order.customer.name}</strong><span>{order.customer.phone}{order.customer.email ? ` · ${order.customer.email}` : ''}</span><span>Data desejada: {dateTime(order.requested_for)}</span><span>{order.fulfillment === 'delivery' ? 'Entrega' : 'Retirada'}{order.delivery_notes ? ` · ${order.delivery_notes}` : ''}</span></div><ul>{order.items.map((item, index) => <li key={`${order.id}-${index}`}>{item.quantity} × {item.product_name}{item.variant_name ? ` (${item.variant_name})` : ''} <span>{money(Number(item.unit_price) * item.quantity)}</span></li>)}</ul><div className="order-total"><span>Total</span><strong>{money(order.total)}</strong></div>{order.history.length > 0 && <details className="order-history"><summary>Histórico de status</summary>{order.history.map((item, index) => <p key={`${order.id}-h${index}`}>{orderStatusLabel(item.old_status)} → {orderStatusLabel(item.new_status)} · {dateTime(item.created_at)}</p>)}</details>}</article>)}{!orders.length && <div className="empty-state"><h2>Nenhum pedido recebido</h2><p>Os pedidos registrados pela loja aparecerão aqui.</p></div>}</div>}</section></div>{editor && <ProductEditor product={editor} categories={categories} busy={busy} onClose={() => setEditor(null)} onSave={(payload) => void saveProduct(payload, editor)} />}</main>
}

function Stat({ label, value }: { label: string; value: string | number }) { return <div className="stat-item"><span>{label}</span><strong>{value}</strong></div> }

function orderStatusLabel(status: string) { return ({ pending: 'Pendente', confirmed: 'Confirmado', preparing: 'Em preparo', ready: 'Pronto', completed: 'Concluído', cancelled: 'Cancelado', paid: 'Pago' } as Record<string, string>)[status] ?? status }

function ProductEditor({ product, categories, busy, onClose, onSave }: { product: Product | 'new'; categories: Category[]; busy: boolean; onClose: () => void; onSave: (payload: ProductPayload) => void }) {
  const [name, setName] = useState(product === 'new' ? '' : product.name)
  const [slug, setSlug] = useState(product === 'new' ? '' : product.slug)
  const [description, setDescription] = useState(product === 'new' ? '' : product.description)
  const [price, setPrice] = useState(product === 'new' ? '' : product.price)
  const [categoryId, setCategoryId] = useState(product === 'new' ? (categories[0]?.id ?? 0) : product.category_id)
  const [available, setAvailable] = useState(product === 'new' || product.is_available)
  const [published, setPublished] = useState(product !== 'new' && product.is_published)
  const [featured, setFeatured] = useState(product !== 'new' && product.is_featured)
  const [demo, setDemo] = useState(product !== 'new' && product.is_demo)
  const [stock, setStock] = useState(product === 'new' || product.stock === null ? '' : String(product.stock))
  const [imageUrls, setImageUrls] = useState(product === 'new' ? '' : product.images.map((image) => image.url).join('\n'))
  const [variants, setVariants] = useState(product === 'new' ? '' : product.variants.map((variant) => `${variant.name}|${variant.price_delta}|${variant.stock ?? ''}`).join('\n'))
  const [uploadError, setUploadError] = useState('')
  const [uploading, setUploading] = useState(false)
  const [previewing, setPreviewing] = useState(false)
  function setProductName(value: string) { setName(value); if (product === 'new') setSlug(value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')) }
  async function upload(file?: File) {
    if (!file) return
    setUploading(true); setUploadError('')
    try { const data = new FormData(); data.append('file', file); const result = await api<{ url: string }>('/api/admin/uploads', { method: 'POST', body: data }); setImageUrls((previous) => [previous, result.url].filter(Boolean).join('\n')) }
    catch (error) { setUploadError(error instanceof Error ? error.message : 'Upload falhou.') }
    finally { setUploading(false) }
  }
  function submit(event: FormEvent) {
    event.preventDefault()
    const imageItems = imageUrls.split('\n').map((url) => url.trim()).filter(Boolean).map((url) => ({ url, alt_text: name }))
    const variantItems = variants.split('\n').map((line) => line.split('|')).filter((parts) => parts[0]?.trim()).map(([variantName, delta = '0', quantity = '']) => ({ name: variantName.trim(), price_delta: delta.trim() || '0', stock: quantity.trim() ? Number(quantity) : null, is_available: true }))
    onSave({ category_id: Number(categoryId), name, slug, description, price, is_available: available, is_published: published, is_featured: featured, is_demo: demo, stock: stock === '' ? null : Number(stock), images: imageItems, variants: variantItems })
  }
  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}><section className="product-editor" role="dialog" aria-modal="true" aria-labelledby="editor-title"><header><div><p className="eyebrow">Catálogo</p><h2 id="editor-title">{product === 'new' ? 'Novo produto' : 'Editar produto'}</h2></div><button className="icon-button" onClick={onClose} aria-label="Fechar"><X size={19} /></button></header><form onSubmit={submit}><div className="editor-fields"><label className="form-field"><span>Nome</span><input required minLength={2} maxLength={180} value={name} onChange={(event) => setProductName(event.target.value)} /></label><label className="form-field"><span>Endereço do produto</span><input required pattern="[a-z0-9]+(-[a-z0-9]+)*" value={slug} onChange={(event) => setSlug(event.target.value)} /></label><label className="form-field"><span>Categoria</span><select required value={categoryId} onChange={(event) => setCategoryId(Number(event.target.value))}>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label><label className="form-field"><span>Preço (R$)</span><input required type="number" min="0" step="0.01" value={price} onChange={(event) => setPrice(event.target.value)} /></label><label className="form-field editor-wide"><span>Descrição</span><textarea required minLength={2} maxLength={5000} rows={4} value={description} onChange={(event) => setDescription(event.target.value)} /></label><label className="form-field"><span>Estoque <small>vazio = sem limite definido</small></span><input type="number" min="0" step="1" value={stock} onChange={(event) => setStock(event.target.value)} /></label><label className="form-field editor-wide"><span>Imagens</span><textarea rows={2} value={imageUrls} onChange={(event) => setImageUrls(event.target.value)} placeholder="Uma URL por linha" /><span className="upload-control"><label><Upload size={15} /> {uploading ? 'Enviando...' : 'Enviar imagem'}<input type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => void upload(event.target.files?.[0])} /></label><small>JPG, PNG ou WebP · até 8 MB</small></span>{uploadError && <small className="danger-text">{uploadError}</small>}</label><label className="form-field editor-wide"><span>Variações <small>uma por linha: nome | adicional em R$ | estoque</small></span><textarea rows={3} value={variants} onChange={(event) => setVariants(event.target.value)} placeholder={'Pequeno | 0 | 5\nGrande | 12.00 | 3'} /></label></div><div className="toggle-row"><label><input type="checkbox" checked={available} onChange={(event) => setAvailable(event.target.checked)} /> Disponível</label><label><input type="checkbox" checked={published} onChange={(event) => setPublished(event.target.checked)} /> Publicar</label><label><input type="checkbox" checked={featured} onChange={(event) => setFeatured(event.target.checked)} /> Destaque</label><label><input type="checkbox" checked={demo} onChange={(event) => setDemo(event.target.checked)} /> Dados de demonstração</label></div><footer><button type="button" className="button button-outline" onClick={onClose}>Cancelar</button><button type="button" className="button button-outline" onClick={() => setPreviewing(true)}>Pré-visualizar</button><button className="button button-dark" disabled={busy || uploading}>{busy ? 'Salvando...' : 'Salvar produto'} <Check size={16} /></button></footer></form></section>{previewing && <div className="preview-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setPreviewing(false) }}><section className="preview-panel" role="dialog" aria-modal="true" aria-label="Prévia do produto"><button className="icon-button preview-close" onClick={() => setPreviewing(false)} aria-label="Fechar prévia"><X size={18} /></button><img src={imageUrls.split('\n').map((url) => url.trim()).find(Boolean) || fallbackPhotos[0]} alt={name || 'Prévia do produto'} /><div><p className="product-category">{categories.find((category) => category.id === Number(categoryId))?.name || 'Categoria'}</p><h2>{name || 'Nome do produto'}</h2><p>{description || 'A descrição do produto aparecerá aqui.'}</p><strong>{price ? money(price) : 'Preço'}</strong></div></section></div>}</div>
}

export default App