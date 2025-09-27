# =====================================
# Django Environment Configuration
# =====================================

# Security
SECRET_KEY=your-secret-key

# Debug mode (False in production)
DEBUG=False

# Allowed hosts (include both root and www subdomain)
ALLOWED_HOSTS=crm.isecuresolutions.in,www.crm.isecuresolutions.in,.onrender.com,.cfargotunnel.com

# Database (SQLite for now; replace with Postgres in production)
DATABASE_URL=sqlite:///db.sqlite3
