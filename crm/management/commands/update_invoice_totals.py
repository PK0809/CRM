from django.core.management.base import BaseCommand
from crm.models import Invoice, EstimationItem

class Command(BaseCommand):
    help = 'Update total_value and balance_due for all invoices'

    def handle(self, *args, **kwargs):
        for invoice in Invoice.objects.all():
            est = invoice.estimation
            items = EstimationItem.objects.filter(estimation=est)

            if not items.exists():
                self.stdout.write(f"{invoice.invoice_no} ➤ No items found. Skipping.")
                continue

            total = 0
            for item in items:
                qty = item.quantity or 0
                rate = float(item.rate or 0)
                tax = float(item.tax or 0)

                base = qty * rate
                tax_amount = (base * tax) / 100
                total += base + tax_amount

            invoice.total_value = round(total, 2)
            invoice.balance_due = round(total, 2)
            invoice.save()

            self.stdout.write(self.style.SUCCESS(f"{invoice.invoice_no} ➤ ₹{invoice.total_value} updated"))
