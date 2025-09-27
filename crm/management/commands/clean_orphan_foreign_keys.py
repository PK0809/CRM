from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Clean orphan foreign keys from invoice, estimationitem, and paymentlog tables'

    def handle(self, *args, **kwargs):
        with connection.cursor() as cursor:
            cleanup_queries = [
                {
                    "description": "Deleting invoice rows with missing estimation",
                    "sql": """
                        DELETE FROM crm_invoice
                        WHERE estimation_id NOT IN (SELECT id FROM crm_estimation);
                    """
                },
                {
                    "description": "Deleting estimation items with missing estimation",
                    "sql": """
                        DELETE FROM crm_estimationitem
                        WHERE estimation_id NOT IN (SELECT id FROM crm_estimation);
                    """
                },
                {
                    "description": "Deleting payment logs with missing invoice",
                    "sql": """
                        DELETE FROM crm_paymentlog
                        WHERE invoice_id NOT IN (SELECT id FROM crm_invoice);
                    """
                }
            ]

            for item in cleanup_queries:
                self.stdout.write(f"[RUNNING] {item['description']}")
                cursor.execute(item["sql"])
                self.stdout.write(self.style.SUCCESS("[DONE]"))

        self.stdout.write(self.style.SUCCESS("✅ All orphan foreign key records cleaned successfully."))
