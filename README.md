# 🔧 آرشیو کتابخانه قطعات الکترونیکی برای Altium Designer

**Altium Component Libraries Archive** — آرشیو جامع و خودکار کتابخانه قطعات الکترونیکی مناسب نرم‌افزار Altium Designer

---

## ✨ ویژگی‌ها

- 🔄 **آپدیت خودکار هفتگی** از طریق GitHub Actions
- 📦 **جمع‌آوری از چند منبع** (JLCPCB/LCSC, Ultra Librarian, تولیدکنندگان)
- 🏗️ **تولید خودکار کتابخانه** (.SchLib + .PcbLib)
- 🌐 **پشتیبانی از چندین دسته‌بندی** (مقاومت، خازن، میکروکنترلر و...)
- 📊 **گزارش‌گیری و ردیابی نسخه**

---

## 📁 ساختار ریپو

```
altium-component-libraries/
├── config.yaml                    # تنظیمات منابع و دسته‌بندی‌ها
├── requirements.txt               # پیش‌نیازهای پایتون
├── scripts/
│   ├── fetch_jlcpcb.py           # جمع‌آوری از JLCPCB/LCSC
│   ├── fetch_ultra_librarian.py  # جمع‌آوری از Ultra Librarian
│   ├── generate_altium_libs.py   # تولید فایل‌های Altium
│   ├── create_summary.py         # ایجاد گزارش
│   └── update_all.py             # اجرای کلی
├── data/
│   ├── categories/               # داده‌های خام هر دسته
│   └── *.json                    # گزارش‌ها و آمار
├── libraries/
│   ├── SchLib/                   # کتابخانه شمایتک (.SchLib)
│   ├── PcbLib/                   # کتابخانه PCB (.PcbLib)
│   ├── IntLib/                   # کتابخانه یکپارچه (.IntLib)
│   └── DBLib/                    # کتابخانه پایگاه داده (.DBLib)
├── models/
│   └── STEP/                     # مدل‌های ۳بعدی
└── .github/
    └── workflows/
        └── update.yml            # GitHub Actions
```

---

## 🚀 شروع سریع

### ۱. کلون ریپو
```bash
git clone https://github.com/bahrambaba/altium-component-libraries.git
cd altium-component-libraries
```

### ۲. نصب پیش‌نیازها
```bash
pip install -r requirements.txt
pip install altium-monkey  # اختیاری - برای تولید فایل‌های Altium
```

### ۳. تنظیم فایل `config.yaml`
```yaml
jlpcb:
  enabled: true
  categories:
    - name: "resistors"
      keyword: "0402"
      max_pages: 5
```

### ۴. اجرای اولیه
```bash
python scripts/update_all.py
```

---

## 📡 منابع داده

### JLCPCB / LCSC (پیش‌فرض ✅)
- **هزینه:** رایگان
- **احراز هویت:** نیاز ندارد
- **تعداد قطعات:** 75,000+
- **دسته‌بندی‌ها:** مقاومت، خازن، سلف، LED، میکروکنترلر، کانکتور
- **آدرس API:** `https://wmsc.lcsc.com/ftps/wm/product/search`

### Ultra Librarian (اختیاری)
- **هزینه:** رایگان (نیاز به ثبت‌نام)
- **احراز هویت:** API Key
- **تعداد قطعات:** میلیون‌ها
- **دسته‌بندی‌ها:** تقویت‌کننده عملیاتی، مبدل DAC/ADC، حافظه
- **آدرس:** https://www.ultralibrarian.com

### تولیدکنندگان (آینده)
- Texas Instruments (TI)
- STMicroelectronics (ST)
- NXP
- Microchip
- Analog Devices

---

## 🤖 اتوماسیون

### GitHub Actions (خودکار)
- **برنامه:** هر یکشنبه ساعت ۰۰:۰۰ UTC
- **اجرا:** دستی از طریق `workflow_dispatch`
- **خروجی:** کامیت خودکار تغییرات

### اجرای دستی
```bash
# جمع‌آوری همه منابع
python scripts/update_all.py

# فقط JLCPCB
python scripts/fetch_jlcpcb.py

# فقط Ultra Librarian
python scripts/fetch_ultra_librarian.py

# فقط تولید کتابخانه
python scripts/generate_altium_libs.py
```

---

## ⚙️ تنظیمات پیشرفته

### فعال/غیرفعال کردن منابع
```yaml
jlpcb:
  enabled: true  # true/false

ultra_librarian:
  enabled: true
  api_key: "YOUR_API_KEY"
```

### تنظیم دسته‌بندی‌ها
```yaml
jlpcb:
  categories:
    - name: "resistors"
      keyword: "0402"           # کلمه کلیدی جستجو
      keyword_fa: "مقاومت 0402" # نام فارسی
      max_pages: 5              # حداکثر صفحات
      page_size: 100            # اندازه صفحه
```

---

## 📊 آمار و گزارش

فایل‌های گزارش در پوشه `data/` ذخیره می‌شوند:

| فایل | توضیح |
|---|---|
| `update_summary.json` | خلاصه هر اجرا |
| `jlpcb_stats.json` | آمار JLCPCB |
| `generation_stats.json` | آمار تولید کتابخانه |
| `last_update.json` | آخرین زمان آپدیت |

---

## 🔗 منابع مفید

| منبع | لینک |
|---|---|
| JLCPCB | https://www.jlcpcb.com |
| LCSC | https://www.lcsc.com |
| Ultra Librarian | https://www.ultralibrarian.com |
| altium-monkey | https://github.com/wavenumber-eng/altium_monkey |
| Altium Designer | https://www.altium.com |

---

## 📄 مجوز

MIT License

---

## 🤝 مشارکت

مشتاقانه منتظر مشارکت شما هستیم! لطفاً Issues و Pull Requests بفرستید.

---

**ساخته شده با ❤️ برای جامعه الکترونیک ایران**
