# A.M Gems and Jewellery E-Commerce Website

A responsive Flask-based luxury storefront for gemstone bracelets, rings, and jewellery.

## Features

- Home, Shop, About Us, Contact, and Testimonials pages
- Product upload panel (name, category, description, price, image)
- Product management panel with edit and delete support
- Session-based admin login/logout for protected inventory actions
- Checkout form that captures customer details before payment
- Contact/enquiry form with database storage
- Direct GPay / PhonePe / UPI payment link for each product
- WhatsApp one-click enquiry and payment support links
- Optional Razorpay secure checkout payment links
- Optional email notifications to customer and admin on enquiry/order
- Mobile-first responsive design and SEO meta tags
- Sitemap and robots support

## Run

1. Open terminal in `am_gems_site`.
2. Install dependencies from workspace root if needed:

```powershell
pip install -r ..\requirements.txt
```

3. Start the website:

```powershell
python am_gems_bangalore.py
```

4. Open browser:

`http://127.0.0.1:5050`

## Deploying to Vercel

This project now includes a Vercel Python entrypoint in `api/index.py` and routing in `vercel.json`.

Before deploying, set these environment variables in Vercel if you want the site to behave correctly:

- `AM_GEMS_SITE_URL` for canonical URLs
- `AM_GEMS_DATABASE_URL` for a persistent database such as PostgreSQL
- `AM_GEMS_UPLOAD_CODE`, `AM_GEMS_UPI_ID`, `AM_GEMS_PAYMENT_NUMBER`, `AM_GEMS_WHATSAPP_NUMBER`
- Mail and Razorpay variables if you use those features

Important limitation: the default SQLite database and image uploads are still ephemeral on Vercel. For real production data, connect the app to external storage and a managed database.

## Configuration (Optional)

- `AM_GEMS_UPLOAD_CODE` for secure upload panel code
- `AM_GEMS_UPI_ID` for GPay / UPI recipient
- `AM_GEMS_PAYMENT_NUMBER` for the direct GPay / PhonePe contact number
- `AM_GEMS_SITE_URL` for canonical URL and SEO
- `AM_GEMS_WHATSAPP_NUMBER` for WhatsApp quick support button
- `AM_GEMS_MAIL_SERVER`, `AM_GEMS_MAIL_PORT`, `AM_GEMS_MAIL_USERNAME`, `AM_GEMS_MAIL_PASSWORD`, `AM_GEMS_MAIL_FROM`
- `AM_GEMS_ADMIN_EMAIL` for enquiry and order alerts
- `AM_GEMS_RAZORPAY_KEY_ID`, `AM_GEMS_RAZORPAY_KEY_SECRET` for Razorpay secure checkout
- `AM_GEMS_PHONEPE_CHECKOUT_URL` to show a PhonePe checkout button (merchant URL)

## New Admin and Checkout Routes

- `/admin/login` for admin session sign-in
- `/admin/logout` for admin session sign-out
- `/admin/upload` to upload products
- `/admin/products` to edit/delete products (admin session required)
- `/order/<product_id>` to capture customer details and choose payment method
- `/pay/<product_id>` for GPay / PhonePe / UPI and support links
- `/pay/razorpay/<product_id>?order_id=<id>` for Razorpay payment link redirect
