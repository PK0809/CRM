from django.db.models import Q

def lead_list(request):
    query = request.GET.get('q', '')
    leads = Lead.objects.all()

    if query:
        leads = leads.filter(
            Q(company_name__icontains=query) |
            Q(contact_person__icontains=query) |
            Q(email__icontains=query) |
            Q(mobile__icontains=query)
        ).distinct()

    paginator = Paginator(leads, 10)  # adjust pagination as needed
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, 'lead.html', {
        'leads': page_obj,
        'query': query,
        'clients': Client.objects.all(),
    })
