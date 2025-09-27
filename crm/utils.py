from .models import EstimationSettings
from datetime import datetime

def generate_estimation_number():
    settings = EstimationSettings.objects.first()
    if not settings:
        return "EST-001"

    prefix = settings.prefix
    current_year = datetime.now().year
    current_month = datetime.now().month

    number = settings.next_number

    # Build number format
    if settings.frequency == "yearly":
        est_no = f"{prefix}/{current_year}/{number:04d}"
    elif settings.frequency == "monthly":
        est_no = f"{prefix}/{current_year}/{current_month:02d}/{number:04d}"
    else:
        est_no = f"{prefix}/{number:04d}"

    # Update next number
    settings.next_number += 1
    settings.save()

    return est_no


def generate_invoice_no():
    prefix = "INV"
    last = Invoice.objects.order_by('-id').first()
    if last:
        last_number = int(last.invoice_no.split('-')[-1])
    else:
        last_number = 0
    return f"{prefix}-{last_number + 1:04d}"


from num2words import num2words

def inr_currency_words(amount):
    try:
        amount = float(amount)
        rupees = int(amount)
        paise = int(round((amount - rupees) * 100))

        if paise > 0:
            return f"Rupees {num2words(rupees, lang='en_IN').title()} and {num2words(paise, lang='en_IN').title()} Paise Only"
        else:
            return f"Rupees {num2words(rupees, lang='en_IN').title()} Only"
    except Exception:
        return "Amount Not Available"

import datetime
from django.utils.timezone import now
from crm.models import Invoice

def generate_invoice_number():
    today = now().strftime("%Y%m%d")
    count = Invoice.objects.filter(created_at__date=now().date()).count() + 1
    return f"INV-{today}-{count:03}"

from crm.models import Estimation
from django.db.models import Max

def generate_and_reserve_quote_no():
    # Get the highest existing quote number
    last_estimation = Estimation.objects.aggregate(Max('quote_no'))['quote_no__max']
    
    try:
        last_number = int(str(last_estimation).replace('Q', '')) if last_estimation else 0
    except ValueError:
        last_number = 0

    next_number = last_number + 1
    return f"Q{next_number:04d}"  # e.g., Q0001, Q0002

from decimal import Decimal, InvalidOperation

def safe_decimal(value):
    try:
        return Decimal(value)
    except (TypeError, InvalidOperation):
        return Decimal('0.00')


import os
from django.template.loader import render_to_string
from weasyprint import HTML
from django.conf import settings

def generate_estimation_pdf(estimation):
    items = estimation.estimationitem_set.all()
    
    html_string = render_to_string('quotation_pdf_template.html', {
        'estimation': estimation,
        'items': items
    })

    pdf_dir = os.path.join(settings.MEDIA_ROOT, 'quotations')
    os.makedirs(pdf_dir, exist_ok=True)
    
    pdf_file_path = os.path.join(pdf_dir, f'Quotation_{estimation.id}.pdf')

    HTML(string=html_string).write_pdf(pdf_file_path)
    
    # Optional: Save PDF path to model
    estimation.pdf_file = f'quotations/Quotation_{estimation.id}.pdf'
    estimation.save()
