# al-shehapi (Honey System)

نسخة تأسيسية لنظام عربي RTL لإدارة محل العسل، مبني بـ Django.

## ماذا جهزنا؟
- هيكل مشروع Django جاهز.
- نماذج بيانات أساسية مطابقة لفكرة النظام (موظفين/مخزون/مبيعات/حسابات/موردين/رأس مال/عروض/مصارفة).
- دعم متغيرات البيئة للنشر (PythonAnywhere).
- قالب واجهات RTL أساسي.

## ملاحظة مهمة
طلبت إنشاءه في `C:/Users/.../Desktop/al-shehapi`.
داخل هذه البيئة لا أقدر الكتابة على جهازك المحلي مباشرة، لذلك جهزته داخل المستودع الحالي.
لتنزيله على جهازك بدون GitHub:
1. انسخ المجلد كاملًا إلى سطح المكتب وسمّه `al-shehapi`.
2. أو اضغطه zip من هنا ثم انقله إلى جهازك.

## التشغيل
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

## ملفات مهمة
- `honey_system/settings.py`
- `honey_system/urls.py`
- `core/models.py`
- `core/views.py`
- `core/templates/core/`
- `core/templatetags/filters.py`
