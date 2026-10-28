export type Category = { id: number; name: string; slug: string; description: string }
export type ProductImage = { id: number; url: string; alt_text: string; position: number }
export type Variant = { id: number; name: string; price_delta: string; stock: number | null; is_available: boolean }
export type Product = {
  id: number
  category_id: number
  category: Category
  name: string
  slug: string
  description: string
  price: string
  is_available: boolean
  is_published: boolean
  is_featured: boolean
  is_demo: boolean
  stock: number | null
  images: ProductImage[]
  variants: Variant[]
}
export type CartLine = { product: Product; quantity: number; variantId?: number }
export type Order = {
  id: number
  public_code: string
  status: string
  fulfillment: string
  delivery_notes: string
  requested_for: string
  total: string
  created_at: string
  customer: { name: string; email: string | null; phone: string }
  items: { product_name: string; variant_name: string; quantity: number; unit_price: string }[]
  history: { old_status: string; new_status: string; created_at: string }[]
}