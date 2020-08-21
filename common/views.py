from django.shortcuts import render


def redirect(request, message, location):
    """Render a view that does pretty auto-redirection
    for  a given @request, showing @message and leading
    to the specified @location"""
    return render(request,
                  'common/redirect.html',
                  {"message": message,
                   "redirect": location})
